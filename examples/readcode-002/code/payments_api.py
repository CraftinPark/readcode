"""Charges API: create, fetch, list and refund card charges for merchant accounts.

Every request is authenticated with the account's secret key:

    Authorization: Bearer sk_test_...

Amounts are integers in the currency's minor unit (cents for USD), so 1050
means $10.50. POST /charges accepts an Idempotency-Key header; a retried
request with the same key returns the first response instead of charging the
card again.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

SUPPORTED_CURRENCIES = {"usd", "eur", "gbp", "cad"}
MAX_AMOUNT = 99_999_999
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60

# Test card tokens understood by the fake card network below.
DECLINING_CARDS = {"pm_card_declined", "pm_card_insufficient_funds"}


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------

@dataclass
class Account:
    id: str
    name: str
    secret_key: str


@dataclass
class Refund:
    id: str
    charge_id: str
    amount: int
    reason: Optional[str]
    created: float


@dataclass
class Charge:
    id: str
    seq: int
    account_id: str
    amount: int
    currency: str
    status: str                      # "succeeded" or "failed"
    payment_method: str
    description: Optional[str]
    metadata: dict
    created: float
    failure_code: Optional[str] = None
    amount_refunded: int = 0
    refunds: list = field(default_factory=list)

    @property
    def refunded(self) -> bool:
        return self.amount_refunded == self.amount


@dataclass
class SavedResponse:
    request_hash: str
    status_code: int
    body: dict
    created: float


class Store:
    def __init__(self, accounts: list[Account]):
        self.accounts_by_key = {a.secret_key: a for a in accounts}
        self.charges: dict[str, Charge] = {}
        self.saved_responses: dict = {}
        self.lock = threading.Lock()
        self._seq = itertools.count(1)

    def next_seq(self) -> int:
        return next(self._seq)


# --------------------------------------------------------------------------
# Request and response shapes
# --------------------------------------------------------------------------

class ChargeIn(BaseModel):
    amount: int = Field(gt=0, le=MAX_AMOUNT)
    currency: str
    payment_method: str
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: dict[str, str] = Field(default_factory=dict)


class RefundIn(BaseModel):
    amount: Optional[int] = Field(default=None, gt=0)
    reason: Optional[str] = None


def charge_json(c: Charge) -> dict:
    return {
        "id": c.id,
        "object": "charge",
        "amount": c.amount,
        "amount_refunded": c.amount_refunded,
        "currency": c.currency,
        "status": c.status,
        "refunded": c.refunded,
        "failure_code": c.failure_code,
        "description": c.description,
        "metadata": c.metadata,
        "created": c.created,
        "refunds": [refund_json(r) for r in c.refunds],
    }


def refund_json(r: Refund) -> dict:
    return {"id": r.id, "object": "refund", "charge": r.charge_id, "amount": r.amount,
            "reason": r.reason, "created": r.created}


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------

def create_app(store: Store) -> FastAPI:
    app = FastAPI(title="Charges API")

    def current_account(authorization: str = Header(default="")) -> Account:
        scheme, _, token = authorization.partition(" ")
        account = store.accounts_by_key.get(token) if scheme == "Bearer" else None
        if account is None:
            raise api_error(401, "unauthorized", "Invalid or missing API key.")
        return account

    def load_charge(account: Account, charge_id: str) -> Charge:
        charge = store.charges.get(charge_id)
        if charge is None:
            raise api_error(404, "resource_missing", f"No such charge: {charge_id}")
        return charge

    def authorize_card(payment_method: str, amount: int) -> Optional[str]:
        """Ask the card network to approve the payment. Returns a failure code or None."""
        if payment_method in DECLINING_CARDS:
            return payment_method.removeprefix("pm_card_")
        return None

    def forget_old_responses(now: float) -> None:
        expired = [k for k, saved in store.saved_responses.items()
                   if now - saved.created > IDEMPOTENCY_TTL_SECONDS]
        for k in expired:
            del store.saved_responses[k]

    @app.post("/charges")
    def create_charge(body: ChargeIn, account: Account = Depends(current_account),
                      idempotency_key: Optional[str] = Header(default=None)):
        currency = body.currency.lower()
        if currency not in SUPPORTED_CURRENCIES:
            raise api_error(400, "invalid_currency", f"Unsupported currency: {body.currency}")

        request_hash = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()
        now = time.time()
        with store.lock:
            forget_old_responses(now)
            if idempotency_key is not None:
                scope = idempotency_key
                saved = store.saved_responses.get(scope)
                if saved is not None:
                    if saved.request_hash != request_hash:
                        raise api_error(409, "idempotency_key_reused",
                                        "This key was already used with different parameters.")
                    return JSONResponse(status_code=saved.status_code, content=saved.body)

            seq = store.next_seq()
            failure = authorize_card(body.payment_method, body.amount)
            charge = Charge(id=f"ch_{seq:06d}", seq=seq, account_id=account.id, amount=body.amount,
                            currency=currency, status="failed" if failure else "succeeded",
                            payment_method=body.payment_method, description=body.description,
                            metadata=body.metadata, created=now, failure_code=failure)
            store.charges[charge.id] = charge
            status_code = 402 if failure else 200
            response = charge_json(charge)
            if idempotency_key is not None:
                store.saved_responses[scope] = SavedResponse(request_hash, status_code, response, now)
        return JSONResponse(status_code=status_code, content=response)

    @app.get("/charges/{charge_id}")
    def retrieve_charge(charge_id: str, account: Account = Depends(current_account)):
        return charge_json(load_charge(account, charge_id))

    @app.get("/charges")
    def list_charges(account: Account = Depends(current_account),
                     limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
                     starting_after: Optional[str] = None):
        mine = sorted((c for c in store.charges.values() if c.account_id == account.id),
                      key=lambda c: c.seq, reverse=True)
        if starting_after is not None:
            cursor = load_charge(account, starting_after)
            mine = [c for c in mine if c.seq <= cursor.seq]
        page = mine[:limit]
        return {"object": "list", "data": [charge_json(c) for c in page], "has_more": len(mine) > limit}

    @app.post("/charges/{charge_id}/refunds")
    def create_refund(charge_id: str, body: RefundIn, account: Account = Depends(current_account)):
        with store.lock:
            charge = load_charge(account, charge_id)
            if charge.status != "succeeded":
                raise api_error(400, "charge_not_refundable", "Only succeeded charges can be refunded.")
            amount = body.amount if body.amount is not None else charge.amount - charge.amount_refunded
            if amount > charge.amount:
                raise api_error(400, "amount_too_large",
                                f"Refund of {amount} exceeds the {charge.amount - charge.amount_refunded} left on the charge.")
            if amount == 0:
                raise api_error(400, "charge_already_refunded", "This charge has already been fully refunded.")
            refund = Refund(id=f"re_{store.next_seq():06d}", charge_id=charge.id, amount=amount,
                            reason=body.reason, created=time.time())
            charge.refunds.append(refund)
            charge.amount_refunded += amount
        return refund_json(refund)

    return app
