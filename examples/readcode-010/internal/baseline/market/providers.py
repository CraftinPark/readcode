"""The payment provider (an external service) and an in-memory stand-in for it.

Like real providers, it answers API calls at once but reports outcomes later as
webhook events. Events are redelivered until we acknowledge them with a 2xx,
and delivery order is not guaranteed.
"""
from dataclasses import dataclass, field

from .db import new_id

DECLINED = {"pm_card_declined"}


@dataclass
class FakeProvider:
    payments: dict = field(default_factory=dict)
    refunds: dict = field(default_factory=dict)
    outbox: list = field(default_factory=list)       # events not yet acknowledged, oldest first
    clock: object = None

    def _event(self, kind: str, data: dict) -> None:
        self.outbox.append({"id": new_id("evt"), "type": kind, "data": data,
                            "created": int(self.clock()) if self.clock else 0})

    def create_payment(self, amount: int, method: str, reference: str) -> dict:
        pay = {"id": new_id("pay"), "amount": amount, "method": method, "reference": reference,
               "status": "processing", "refunded": 0}
        self.payments[pay["id"]] = pay
        if method in DECLINED:
            pay["status"] = "failed"
            self._event("payment.failed", {"payment_id": pay["id"], "reference": reference})
        else:
            pay["status"] = "succeeded"
            self._event("payment.succeeded", {"payment_id": pay["id"], "reference": reference, "amount": amount})
        return {"id": pay["id"], "status": "processing"}

    def refund(self, payment_id: str, amount: int) -> dict:
        pay = self.payments[payment_id]
        if pay["refunded"] + amount > pay["amount"]:
            raise ValueError("Refund exceeds the payment.")
        pay["refunded"] += amount
        ref = {"id": new_id("re"), "payment_id": payment_id, "amount": amount, "status": "pending"}
        self.refunds[ref["id"]] = ref
        ref["status"] = "succeeded"
        self._event("refund.succeeded", {"refund_id": ref["id"], "payment_id": payment_id, "amount": amount})
        return {"id": ref["id"], "status": "pending"}

    def acknowledge(self, event_id: str) -> None:
        self.outbox = [e for e in self.outbox if e["id"] != event_id]
