"""Client interface for the card network: the processor that asks the card's
issuing bank to approve a payment, and later to give money back.

The network deduplicates on `reference`: authorizing again with a reference it
has already seen returns the original authorization instead of charging the
card a second time. Refunds deduplicate the same way.
"""
from dataclasses import dataclass
from typing import Protocol

from . import db


class CardNetworkTimeout(Exception):
    """No answer in time. The request may or may not have reached the bank."""


class CardDeclined(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Authorization:
    id: str
    reference: str
    amount: int
    currency: str


class CardNetwork(Protocol):
    def authorize(self, reference: str, payment_method: str, amount: int, currency: str) -> Authorization: ...
    def refund(self, reference: str, authorization_id: str, amount: int) -> str: ...


DECLINE_CODES = {
    "pm_card_declined": "card_declined",
    "pm_card_insufficient_funds": "insufficient_funds",
}


class FakeCardNetwork:
    """In-memory stand-in for local runs and tests. It behaves like the real
    network for the cases this service relies on, including deduplication."""

    def __init__(self):
        self.authorizations: dict[str, Authorization] = {}
        self.refunds: dict[str, tuple[str, int]] = {}

    def authorize(self, reference: str, payment_method: str, amount: int, currency: str) -> Authorization:
        if payment_method in DECLINE_CODES:
            raise CardDeclined(DECLINE_CODES[payment_method])
        if reference not in self.authorizations:
            self.authorizations[reference] = Authorization(db.new_id("auth"), reference, amount, currency)
        return self.authorizations[reference]

    def refund(self, reference: str, authorization_id: str, amount: int) -> str:
        if reference not in self.refunds:
            self.refunds[reference] = (authorization_id, amount)
        return reference

    def total_authorized(self) -> int:
        return sum(a.amount for a in self.authorizations.values())
