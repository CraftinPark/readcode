"""Backend playground: run an example's shipped code and let the candidate poke it.

For backend tickets there is no screen to look at, so the playground shows what
a backend engineer looks at on call: requests and responses, logs, database
rows, and what external systems saw. It also exposes the levers the gate tests
use (inject a fault, move the clock, deliver a webhook out of order), so the
candidate can reproduce the symptom themselves.

Only the example's own shipped code runs here, never candidate code.

Protocol: the server describes its controls and panels; the console renders them.
    state   = {clock, controls: [{group, items: [{id, label, kind, on?}]}], panels: [{id, title, rows}], logs, response?}
    POST /api/playground/<example>/sessions          -> state + session id
    POST /api/playground/sessions/<sid>/request      {method, path, headers, body}
    POST /api/playground/sessions/<sid>/act          {action, value?}

    cd backend && python -m playground          # serves /api/playground on :8000
"""
import importlib
import importlib.util
import json
import secrets
import shutil
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
MAX_SESSIONS = 50


def load_package(example: str, package: str):
    """Import code/<package> of an example under a unique name, so several
    examples with a package of the same name can run side by side."""
    alias = f"rc_{example.replace('-', '_')}_{package}"
    if alias not in sys.modules:
        path = EXAMPLES / example / "code" / package
        spec = importlib.util.spec_from_file_location(alias, path / "__init__.py", submodule_search_locations=[str(path)])
        mod = importlib.util.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)
    return lambda name: importlib.import_module(f"{alias}.{name}")


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def _rows(conn, sql, args=()):
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


class Session:
    """Common parts: a temp folder, a clock, a log, and the HTTP client for the app."""

    def __init__(self, start_time: float):
        self.dir = tempfile.mkdtemp(prefix="rc-playground-")
        self.clock = Clock(start_time)
        self.logs: list[str] = []
        self.lock = threading.Lock()

    def log(self, line):
        stamp = datetime.fromtimestamp(self.clock(), timezone.utc).strftime("%a %d %b %H:%M UTC")
        self.logs.append(f"{stamp}  {line}")

    def request(self, method, path, headers, body):
        key = headers.get("Idempotency-Key")
        self.log(f"-> {method} {path}" + (f"  Idempotency-Key: {key}" if key else ""))
        r = self.client.request(method, path, headers=headers, json=body if method != "GET" else None)
        try:
            payload = r.json()
        except ValueError:
            payload = r.text
        detail = payload.get("detail") if isinstance(payload, dict) else None
        note = (detail.get("code") or detail.get("message")) if isinstance(detail, dict) else None
        self.log(f"<- {r.status_code}" + (f" {note}" if note else "") + (" (unhandled server error)" if r.status_code == 500 else ""))
        return {"status": r.status_code, "body": payload}

    def clock_controls(self):
        return {"group": "Clock", "items": [
            {"id": "clock:3600", "label": "+1 hour", "kind": "button"},
            {"id": "clock:86400", "label": "+1 day", "kind": "button"},
            {"id": "clock:604800", "label": "+7 days", "kind": "button"},
            {"id": "set_clock", "label": "Set date and time (UTC)", "kind": "datetime"}]}

    def act(self, action: str, value=None):
        if action.startswith("clock:"):
            seconds = int(action.split(":", 1)[1])
            self.clock.t += seconds
            self.log(f"clock moved forward {seconds // 3600} h")
        elif action == "set_clock":
            t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            self.clock.t = (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).timestamp()
            self.log("clock set")
        else:
            self.engine_act(action, value)

    def state(self):
        return {"clock": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat().replace("+00:00", "Z"),
                "controls": self.controls(), "panels": self.panels(), "logs": self.logs[-300:]}

    def close(self):
        self.client.close()
        shutil.rmtree(self.dir, ignore_errors=True)


class PaymentsSession(Session):
    """readcode-003: charges API with a card network and a webhook worker."""
    ACCOUNTS = [{"id": "acct_acme", "name": "Acme", "secret_key": "sk_test_acme"},
                {"id": "acct_globex", "name": "Globex", "secret_key": "sk_test_globex"}]
    ENDPOINTS = [{"id": "we_a", "account_id": "acct_acme", "url": "https://acme.example/hooks", "secret": "whsec_a"},
                 {"id": "we_g", "account_id": "acct_globex", "url": "https://globex.example/hooks", "secret": "whsec_g"}]

    def __init__(self, example):
        super().__init__(1_760_000_000.0)
        mod = load_package(example, "payments")
        db, app_mod, card, self.hooks = mod("db"), mod("app"), mod("card_network"), mod("webhooks")
        self.db = db
        path = str(Path(self.dir) / "payments.db")
        db.init(path, accounts=self.ACCOUNTS, endpoints=self.ENDPOINTS)
        self.faults = {"timeout_after_charge": False, "crash_after_charge": False}
        self.webhooks = []
        self.network = self._network(card)
        self.client = TestClient(app_mod.create_app(path, self.network, self.clock), raise_server_exceptions=False)
        self.conn = db.connect(path)
        self.log("session started: Acme (sk_test_acme) and Globex (sk_test_globex), each with a webhook endpoint")

    def _network(self, card):
        s = self

        class ObservedNetwork(card.FakeCardNetwork):
            def authorize(self, reference, payment_method, amount, currency):
                new = reference not in self.authorizations
                auth = super().authorize(reference, payment_method, amount, currency)
                s.log(f"card network: authorize {amount} {currency} ref={reference} -> {auth.id} "
                      f"({'new authorization' if new else 'same reference, existing authorization'})")
                if s.faults["timeout_after_charge"]:
                    s.faults["timeout_after_charge"] = False
                    s.log("fault: the card network charged the card, then timed out before answering")
                    raise card.CardNetworkTimeout()
                if s.faults["crash_after_charge"]:
                    s.faults["crash_after_charge"] = False
                    s.log("fault: the server died after the card was charged")
                    raise RuntimeError("server killed")
                return auth

            def refund(self, reference, authorization_id, amount):
                s.log(f"card network: refund {amount} of {authorization_id} ref={reference}")
                return super().refund(reference, authorization_id, amount)

        return ObservedNetwork()

    def controls(self):
        return [
            {"group": "Faults (next card network call)", "items": [
                {"id": "fault:timeout_after_charge", "label": "Charge the card, then time out", "kind": "toggle",
                 "on": self.faults["timeout_after_charge"]},
                {"id": "fault:crash_after_charge", "label": "Charge the card, then the server dies", "kind": "toggle",
                 "on": self.faults["crash_after_charge"]}]},
            {"group": "Clock", "items": [{"id": "clock:60", "label": "+1 min", "kind": "button"},
                                         {"id": "clock:600", "label": "+10 min", "kind": "button"},
                                         {"id": "clock:3600", "label": "+1 hour", "kind": "button"},
                                         {"id": "clock:86400", "label": "+1 day", "kind": "button"}]},
            {"group": "Webhook worker", "items": [{"id": f"deliver:{c}", "label": f"Run, endpoint answers {c}", "kind": "button"}
                                                  for c in (200, 404, 500)]},
        ]

    def engine_act(self, action, value):
        kind, _, arg = action.partition(":")
        if kind == "fault" and arg in self.faults:
            self.faults[arg] = bool(value)
            self.log(f"fault {'armed' if value else 'cleared'}: {arg.replace('_', ' ')}")
        elif kind == "deliver":
            code = int(arg)
            before = len(self.webhooks)

            def post(url, body, headers):
                event = json.loads(body)
                self.webhooks.append({"type": event["type"], "to": url, "reply": code})
                return code
            n = self.hooks.deliver_due(self.conn, post, self.db.now_ms(self.clock))
            self.log(f"webhook worker: sent {len(self.webhooks) - before}, marked delivered {n} (endpoint answered {code})")
        else:
            raise HTTPException(400, f"Unknown action {action}")

    def panels(self):
        net = self.network
        auths = [{"id": a.id, "amount": a.amount, "reference": a.reference} for a in net.authorizations.values()]
        return [
            {"id": "card", "title": f"Card network (what the bank saw), total authorized ${net.total_authorized() / 100:.2f}", "rows": auths},
            {"id": "charges", "title": "DB: charges", "rows": _rows(self.conn, "SELECT * FROM charges ORDER BY rowid")},
            {"id": "keys", "title": "DB: idempotency_keys", "rows": _rows(self.conn, "SELECT * FROM idempotency_keys ORDER BY rowid")},
            {"id": "refunds", "title": "DB: refunds", "rows": _rows(self.conn, "SELECT * FROM refunds ORDER BY rowid")},
            {"id": "events", "title": "DB: events (webhook outbox)", "rows": _rows(self.conn, "SELECT id, account_id, type, attempts, delivered_ms, failed FROM events ORDER BY rowid")},
            {"id": "webhooks", "title": "Webhooks sent", "rows": self.webhooks},
        ]


class MarketSession(Session):
    """readcode-007..011: the delivery marketplace with its payment provider."""
    START = datetime(2026, 10, 27, 16, 0, tzinfo=timezone.utc).timestamp()     # a Tuesday, noon in Toronto

    def __init__(self, example):
        super().__init__(self.START)
        mod = load_package(example, "market")
        db, app_mod, providers, seed = mod("db"), mod("app"), mod("providers"), mod("seed")
        path = str(Path(self.dir) / "market.db")
        db.init(path, seed.SEED)
        self.provider = providers.FakeProvider(clock=self.clock)
        self.client = TestClient(app_mod.create_app(path, self.provider, self.clock), raise_server_exceptions=False)
        self.conn = db.connect(path)
        self.log("session started. Customer keys: sk_alice, sk_bob. Staff key: sk_admin_ops.")

    def controls(self):
        events = [{"id": f"deliver:{e['id']}", "kind": "button",
                   "label": f"Deliver {e['type']} ({e['data'].get('payment_id') or e['data'].get('refund_id')})"}
                  for e in self.provider.outbox]
        return [
            self.clock_controls(),
            {"group": "Payment provider: events waiting to be delivered (any order)",
             "items": events or [{"id": "none", "label": "No events waiting", "kind": "note"}]},
            {"group": "Payment provider", "items": [{"id": "deliver_all", "label": "Deliver all, oldest first", "kind": "button"}]},
        ]

    def _deliver(self, event):
        r = self.client.post("/webhooks/provider", json=event)
        result = r.json().get("result") if r.status_code == 200 else f"HTTP {r.status_code}"
        self.log(f"provider -> POST /webhooks/provider {event['type']} {event['id']}: {result}")
        if r.status_code == 200:
            self.provider.acknowledge(event["id"])

    def engine_act(self, action, value):
        if action == "deliver_all":
            for e in list(self.provider.outbox):
                self._deliver(e)
        elif action.startswith("deliver:"):
            eid = action.split(":", 1)[1]
            event = next((e for e in self.provider.outbox if e["id"] == eid), None)
            if event is None:
                raise HTTPException(404, "That event was already delivered.")
            self._deliver(event)
        else:
            raise HTTPException(400, f"Unknown action {action}")

    def panels(self):
        c = self.conn
        return [
            {"id": "orders", "title": "DB: orders", "rows": _rows(c, "SELECT id, status, payment_status, courier_id, subtotal, discount, total, promo_code FROM orders ORDER BY created_ms")},
            {"id": "lines", "title": "DB: order_lines", "rows": _rows(c, "SELECT order_id, name, quantity, amount, discount, net FROM order_lines ORDER BY order_id, id")},
            {"id": "couriers", "title": "DB: couriers", "rows": _rows(c, "SELECT * FROM couriers ORDER BY id")},
            {"id": "refunds", "title": "DB: refunds", "rows": _rows(c, "SELECT id, order_id, amount, status, created_ms, settled_ms FROM refunds ORDER BY created_ms")},
            {"id": "payouts", "title": "DB: payouts", "rows": _rows(c, "SELECT restaurant_id, period_start_ms, period_end_ms, gross, refunds, commission, amount FROM payouts ORDER BY created_ms")},
            {"id": "notifications", "title": "DB: notifications", "rows": _rows(c, "SELECT recipient, kind, order_id, created_ms FROM notifications ORDER BY created_ms")},
            {"id": "provider", "title": "Provider: payments and refunds",
             "rows": [{"id": p["id"], "order": p["reference"], "amount": p["amount"], "status": p["status"], "refunded": p["refunded"]}
                      for p in self.provider.payments.values()]},
        ]


ENGINES = {"payments": PaymentsSession, "market": MarketSession}


def engine_for(example: str):
    p = EXAMPLES / example / "public.json"
    if not p.is_file():
        return None
    pg = json.loads(p.read_text(encoding="utf-8")).get("playground")
    return ENGINES.get(pg.get("engine", "payments")) if pg else None


class RequestIn(BaseModel):
    method: str = "POST"
    path: str
    headers: dict[str, str] = {}
    body: dict | None = None


class ActIn(BaseModel):
    action: str
    value: object = None


def create_playground_app(study_store=None):
    """The local API: playground sessions, plus study submissions (backend/study)."""
    from study import create_router

    app = FastAPI(title="ReadCode playground")
    app.include_router(create_router(study_store))
    sessions: dict[str, Session] = {}

    def get(sid) -> Session:
        if sid not in sessions:
            raise HTTPException(404, "No such playground session; start a new one.")
        return sessions[sid]

    @app.post("/api/playground/{example}/sessions")
    def new_session(example: str):
        engine = engine_for(example)
        if engine is None:
            raise HTTPException(404, f"No playground for {example}.")
        while len(sessions) >= MAX_SESSIONS:
            sessions.pop(next(iter(sessions))).close()
        sid = secrets.token_hex(8)
        sessions[sid] = engine(example)
        return {"session": sid, **sessions[sid].state()}

    @app.post("/api/playground/sessions/{sid}/request")
    def send(sid: str, r: RequestIn):
        s = get(sid)
        if not r.path.startswith("/"):
            raise HTTPException(400, "path must start with /")
        with s.lock:
            return {"response": s.request(r.method.upper(), r.path, r.headers, r.body), **s.state()}

    @app.post("/api/playground/sessions/{sid}/act")
    def act(sid: str, a: ActIn):
        s = get(sid)
        with s.lock:
            s.act(a.action, a.value)
            return s.state()

    @app.get("/api/playground/sessions/{sid}")
    def state(sid: str):
        return get(sid).state()

    return app


app = create_playground_app()
