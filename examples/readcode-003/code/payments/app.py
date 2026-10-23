"""HTTP API: charges and refunds for merchant accounts.

Requests authenticate with the account's secret key (Authorization: Bearer
sk_...). Amounts are integers in the currency's minor unit. Several servers run
this app against one database; the card network and the clock are passed in so
they can be replaced in tests.
"""
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db, idempotency, webhooks
from .card_network import CardDeclined, CardNetwork, CardNetworkTimeout

SUPPORTED_CURRENCIES = {"usd", "eur", "gbp", "cad", "jpy"}
MAX_AMOUNT = 99_999_999


class ChargeIn(BaseModel):
    amount: int = Field(gt=0, le=MAX_AMOUNT)
    currency: str
    payment_method: str
    description: Optional[str] = Field(default=None, max_length=500)


class RefundIn(BaseModel):
    amount: Optional[int] = Field(default=None, gt=0)


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def charge_json(row) -> dict:
    return {"id": row["id"], "object": "charge", "amount": row["amount"], "currency": row["currency"],
            "status": row["status"], "failure_code": row["failure_code"],
            "amount_refunded": row["amount_refunded"], "created": row["created_ms"] // 1000}


def create_app(db_path: str, network: CardNetwork, clock=time.time) -> FastAPI:
    app = FastAPI(title="Payments API")
    conn = db.connect(db_path)

    def account_id(authorization: str = Header(default="")) -> str:
        scheme, _, token = authorization.partition(" ")
        row = conn.execute("SELECT id FROM accounts WHERE secret_key = ?", (token,)).fetchone() if scheme == "Bearer" else None
        if row is None:
            raise api_error(401, "unauthorized", "Invalid or missing API key.")
        return row["id"]

    def load_charge(acct: str, charge_id: str):
        row = conn.execute("SELECT * FROM charges WHERE id = ? AND account_id = ?", (charge_id, acct)).fetchone()
        if row is None:
            raise api_error(404, "resource_missing", f"No such charge: {charge_id}")
        return row

    def store_charge(acct: str, key: Optional[str], status_code: int, **fields) -> JSONResponse:
        """Insert the charge, its event and the saved response in one transaction."""
        now = db.now_ms(clock)
        row = {"id": db.new_id("ch"), "account_id": acct, "amount_refunded": 0, "created_ms": now,
               "authorization_id": None, "failure_code": None, **fields}
        with db.transaction(conn):
            conn.execute("INSERT INTO charges (id, account_id, amount, currency, status, authorization_id, "
                         "failure_code, amount_refunded, created_ms) VALUES (:id, :account_id, :amount, "
                         ":currency, :status, :authorization_id, :failure_code, :amount_refunded, :created_ms)", row)
            body = charge_json(row)
            webhooks.record(conn, acct, f"charge.{row['status']}", body, now)
            if key is not None:
                idempotency.save_response(conn, acct, key, status_code, body)
        return JSONResponse(status_code=status_code, content=body)

    @app.post("/charges")
    def create_charge(body: ChargeIn, acct: str = Depends(account_id),
                      idempotency_key: Optional[str] = Header(default=None)):
        currency = body.currency.lower()
        if currency not in SUPPORTED_CURRENCIES:
            raise api_error(400, "invalid_currency", f"Unsupported currency: {body.currency}")

        if idempotency_key is not None:
            try:
                saved = idempotency.claim(conn, acct, idempotency_key, idempotency.request_hash(body.model_dump()),
                                          db.now_ms(clock))
            except idempotency.KeyConflict as e:
                raise api_error(409, e.code, e.message)
            if saved is not None:
                return JSONResponse(status_code=saved.status_code, content=saved.body)

        reference = db.new_id("ref")
        try:
            auth = network.authorize(reference, body.payment_method, body.amount, currency)
        except CardDeclined as e:
            return store_charge(acct, idempotency_key, 402, amount=body.amount, currency=currency,
                                status="failed", failure_code=e.code)
        except CardNetworkTimeout:
            if idempotency_key is not None:
                idempotency.release(conn, acct, idempotency_key)
            raise api_error(503, "card_network_timeout",
                            "The card network did not answer. Retry with the same Idempotency-Key.")
        return store_charge(acct, idempotency_key, 200, amount=body.amount, currency=currency,
                            status="succeeded", authorization_id=auth.id)

    @app.get("/charges/{charge_id}")
    def retrieve_charge(charge_id: str, acct: str = Depends(account_id)):
        return charge_json(load_charge(acct, charge_id))

    @app.get("/charges")
    def list_charges(acct: str = Depends(account_id), limit: int = Query(default=10, ge=1, le=100),
                     starting_after: Optional[str] = None):
        if starting_after is None:
            rows = conn.execute("SELECT * FROM charges WHERE account_id = ? ORDER BY created_ms DESC, id DESC "
                                "LIMIT ?", (acct, limit + 1)).fetchall()
        else:
            cursor = load_charge(acct, starting_after)
            rows = conn.execute("SELECT * FROM charges WHERE account_id = ? AND (created_ms, id) < (?, ?) "
                                "ORDER BY created_ms DESC, id DESC LIMIT ?",
                                (acct, cursor["created_ms"], cursor["id"], limit + 1)).fetchall()
        return {"object": "list", "data": [charge_json(r) for r in rows[:limit]], "has_more": len(rows) > limit}

    @app.post("/charges/{charge_id}/refunds")
    def create_refund(charge_id: str, body: RefundIn, acct: str = Depends(account_id)):
        charge = load_charge(acct, charge_id)
        if charge["status"] != "succeeded":
            raise api_error(400, "charge_not_refundable", "Only succeeded charges can be refunded.")
        amount = body.amount if body.amount is not None else charge["amount"] - charge["amount_refunded"]
        if amount <= 0:
            raise api_error(400, "charge_already_refunded", "This charge has already been fully refunded.")

        # Reserve the amount first, so two refunds racing on different servers
        # cannot both pass the check.
        with db.transaction(conn):
            reserved = conn.execute("UPDATE charges SET amount_refunded = amount_refunded + ? "
                                    "WHERE id = ? AND amount - amount_refunded >= ?",
                                    (amount, charge_id, amount)).rowcount
        if not reserved:
            raise api_error(400, "amount_too_large", "The refund is larger than what is left on the charge.")

        refund_id = db.new_id("re")
        try:
            network_id = network.refund(f"refund:{refund_id}", charge["authorization_id"], amount)
        except CardNetworkTimeout:
            with db.transaction(conn):
                conn.execute("UPDATE charges SET amount_refunded = amount_refunded - ? WHERE id = ?", (amount, charge_id))
            raise api_error(503, "card_network_timeout", "The card network did not answer. The refund was not made.")

        now = db.now_ms(clock)
        with db.transaction(conn):
            conn.execute("INSERT INTO refunds (id, charge_id, amount, network_id, created_ms) VALUES (?, ?, ?, ?, ?)",
                         (refund_id, charge_id, amount, network_id, now))
            refund = {"id": refund_id, "object": "refund", "charge": charge_id, "amount": amount, "created": now // 1000}
            webhooks.record(conn, acct, "charge.refunded", refund, now)
        return refund

    return app
