"""Backend playground: run an example's shipped code and let the candidate poke it.

For backend tickets there is no screen to look at, so the playground shows what
a backend engineer looks at on call: requests and responses, logs, database
rows, outgoing webhooks, and what the external system (the card network) saw.
It also exposes the same levers the gate tests use: inject a fault, move the
clock. The candidate reproduces the symptom themselves.

Only the example's own shipped code runs here, never candidate code.

    cd backend && python -m playground          # serves /api/playground on :8000
"""
import importlib
import json
import os
import secrets
import shutil
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
SUPPORTED = {"readcode-003"}          # examples whose code the playground knows how to drive
MAX_SESSIONS = 50
TABLES = ("charges", "refunds", "idempotency_keys", "events")

ACCOUNTS = [{"id": "acct_acme", "name": "Acme", "secret_key": "sk_test_acme"},
            {"id": "acct_globex", "name": "Globex", "secret_key": "sk_test_globex"}]
ENDPOINTS = [{"id": "we_a", "account_id": "acct_acme", "url": "https://acme.example/hooks", "secret": "whsec_a"},
             {"id": "we_g", "account_id": "acct_globex", "url": "https://globex.example/hooks", "secret": "whsec_g"}]


def _load_payments(example):
    """Import the example's shipped `payments` package (code/ is what the candidate reads)."""
    code = str(EXAMPLES / example / "code")
    if code not in sys.path:
        sys.path.insert(0, code)
    return (importlib.import_module("payments.db"), importlib.import_module("payments.app"),
            importlib.import_module("payments.card_network"), importlib.import_module("payments.webhooks"))


class Clock:
    def __init__(self):
        self.t = 1_760_000_000.0

    def __call__(self):
        return self.t


class Session:
    def __init__(self, example):
        db, app_mod, card, hooks = _load_payments(example)
        self.db, self.hooks = db, hooks
        self.dir = tempfile.mkdtemp(prefix="rc-playground-")
        path = os.path.join(self.dir, "payments.db")
        db.init(path, accounts=ACCOUNTS, endpoints=ENDPOINTS)
        self.clock = Clock()
        self.logs: list[str] = []
        self.webhooks: list[dict] = []
        self.faults = {"timeout_after_charge": False, "crash_after_charge": False}
        self.network = self._network(card)
        self.client = TestClient(app_mod.create_app(path, self.network, self.clock), raise_server_exceptions=False)
        self.conn = db.connect(path)
        self.lock = threading.Lock()
        self.log("session started: Acme (sk_test_acme) and Globex (sk_test_globex), each with a webhook endpoint")

    def _network(self, card):
        session = self

        class ObservedNetwork(card.FakeCardNetwork):
            """The fake card network, plus a log line per call and the injectable faults."""

            def authorize(self, reference, payment_method, amount, currency):
                new = reference not in self.authorizations
                auth = super().authorize(reference, payment_method, amount, currency)
                session.log(f"card network: authorize {amount} {currency} ref={reference} -> {auth.id} "
                            f"({'new authorization' if new else 'same reference, existing authorization'})")
                if session.faults["timeout_after_charge"]:
                    session.faults["timeout_after_charge"] = False
                    session.log("fault: the card network charged the card, then timed out before answering")
                    raise card.CardNetworkTimeout()
                if session.faults["crash_after_charge"]:
                    session.faults["crash_after_charge"] = False
                    session.log("fault: the server died after the card was charged")
                    raise RuntimeError("server killed")
                return auth

            def refund(self, reference, authorization_id, amount):
                session.log(f"card network: refund {amount} of {authorization_id} ref={reference}")
                return super().refund(reference, authorization_id, amount)

        return ObservedNetwork()

    def log(self, line):
        stamp = datetime.fromtimestamp(self.clock(), timezone.utc).strftime("%H:%M:%S")
        self.logs.append(f"{stamp}  {line}")

    def request(self, method, path, headers, body):
        key = headers.get("Idempotency-Key")
        self.log(f"-> {method} {path}" + (f"  Idempotency-Key: {key}" if key else ""))
        r = self.client.request(method, path, headers=headers, json=body if method != "GET" else None)
        try:
            payload = r.json()
        except ValueError:
            payload = r.text
        code = (payload.get("detail") or {}).get("code") if isinstance(payload, dict) and isinstance(payload.get("detail"), dict) else None
        self.log(f"<- {r.status_code}" + (f" {code}" if code else "") + (" (unhandled server error)" if r.status_code == 500 else ""))
        return {"status": r.status_code, "body": payload}

    def deliver_webhooks(self, reply_status):
        def post(url, body, headers):
            event = json.loads(body)
            self.webhooks.append({"url": url, "type": event["type"], "event": event["id"], "reply": reply_status})
            return reply_status
        before = len(self.webhooks)
        delivered = self.hooks.deliver_due(self.conn, post, self.db.now_ms(self.clock))
        self.log(f"webhook worker: sent {len(self.webhooks) - before}, marked delivered {delivered} (endpoint answered {reply_status})")
        return delivered

    def state(self):
        tables = {}
        for t in TABLES:
            rows = self.conn.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall()
            tables[t] = [dict(r) for r in rows]
        net = self.network
        return {
            "clock": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat().replace("+00:00", "Z"),
            "faults": self.faults,
            "card_network": {
                "authorizations": [{"id": a.id, "reference": a.reference, "amount": a.amount, "currency": a.currency}
                                   for a in net.authorizations.values()],
                "refunds": [{"reference": k, "authorization": v[0], "amount": v[1]} for k, v in net.refunds.items()],
                "total_authorized": net.total_authorized(),
            },
            "tables": tables,
            "webhooks": self.webhooks,
            "logs": self.logs[-200:],
        }

    def close(self):
        self.conn.close()
        self.client.close()
        shutil.rmtree(self.dir, ignore_errors=True)


class RequestIn(BaseModel):
    method: str = "POST"
    path: str
    headers: dict[str, str] = {}
    body: dict | None = None


class FaultsIn(BaseModel):
    timeout_after_charge: bool | None = None
    crash_after_charge: bool | None = None


class ClockIn(BaseModel):
    seconds: float


class DeliverIn(BaseModel):
    reply_status: int = 200


def create_playground_app():
    app = FastAPI(title="ReadCode playground")
    sessions: dict[str, Session] = {}

    def get(sid) -> Session:
        if sid not in sessions:
            raise HTTPException(404, "No such playground session; start a new one.")
        return sessions[sid]

    @app.post("/api/playground/{example}/sessions")
    def new_session(example: str):
        if example not in SUPPORTED:
            raise HTTPException(404, f"No playground for {example}.")
        while len(sessions) >= MAX_SESSIONS:
            sessions.pop(next(iter(sessions))).close()
        sid = secrets.token_hex(8)
        sessions[sid] = Session(example)
        return {"session": sid, **sessions[sid].state()}

    @app.post("/api/playground/sessions/{sid}/request")
    def send(sid: str, r: RequestIn):
        s = get(sid)
        with s.lock:
            if not r.path.startswith("/"):
                raise HTTPException(400, "path must start with /")
            return {"response": s.request(r.method.upper(), r.path, r.headers, r.body), **s.state()}

    @app.post("/api/playground/sessions/{sid}/faults")
    def faults(sid: str, f: FaultsIn):
        s = get(sid)
        with s.lock:
            for k, v in f.model_dump(exclude_none=True).items():
                s.faults[k] = v
                s.log(f"fault {'armed' if v else 'cleared'}: {k.replace('_', ' ')}")
            return s.state()

    @app.post("/api/playground/sessions/{sid}/clock")
    def clock(sid: str, c: ClockIn):
        s = get(sid)
        with s.lock:
            s.clock.t += c.seconds
            s.log(f"clock moved forward {int(c.seconds)} s")
            return s.state()

    @app.post("/api/playground/sessions/{sid}/webhooks/deliver")
    def deliver(sid: str, d: DeliverIn):
        s = get(sid)
        with s.lock:
            s.deliver_webhooks(d.reply_status)
            return s.state()

    @app.get("/api/playground/sessions/{sid}")
    def state(sid: str):
        return get(sid).state()

    return app


app = create_playground_app()
