"""Promo codes at checkout. Amounts are integer cents."""
from datetime import date

CODES = {
    # code: (kind, value, min_subtotal_cents, expires_on (last valid day), max_uses, first_order_only)
    "WELCOME10": ("percent", 10, 2000, date(2026, 12, 31), 10000, True),
    "FLAT5": ("flat", 500, 0, date(2026, 11, 30), 500, False),
    "VIP25": ("percent", 25, 5000, date(2027, 6, 30), 50, False),
}


def discount(subtotal_cents, code, today, times_used, customer_order_count):
    """Discount in cents for this order, or 0 if the code does not apply. Never more than the subtotal."""
    rule = CODES.get(code.strip().upper())
    if rule is None:
        return 0
    kind, value, min_subtotal, expires_on, max_uses, first_order_only = rule
    if subtotal_cents < min_subtotal:
        return 0
    if today > expires_on:
        return 0
    if times_used >= max_uses:
        return 0
    if first_order_only and customer_order_count > 0:
        return 0
    if kind == "percent":
        amount = (subtotal_cents * value + 50) // 100     # round half up to the cent
    else:
        amount = value
    return min(amount, subtotal_cents)
