"""Turning a cart into a priced order: lines, promo discount, delivery fee and tax.

The order discount is computed once on the subtotal and then shared out across
the lines, because restaurants are paid on each line's net amount.
"""
from .money import percent

DELIVERY_FEE = 399
TAX_PERCENT = 13          # on food after discount, plus the delivery fee
MAX_QUANTITY = 20


class PricingError(Exception):
    pass


def quote(conn, restaurant_id: str, items: list[dict], promo_code: str | None = None) -> dict:
    if not items:
        raise PricingError("The cart is empty.")
    lines = []
    for it in items:
        qty = int(it.get("quantity", 1))
        if not 1 <= qty <= MAX_QUANTITY:
            raise PricingError(f"Quantity must be between 1 and {MAX_QUANTITY}.")
        row = conn.execute("SELECT id, name, price FROM menu_items WHERE id = ? AND restaurant_id = ?",
                           (it["item_id"], restaurant_id)).fetchone()
        if row is None:
            raise PricingError(f"Item {it['item_id']} is not on this restaurant's menu.")
        lines.append({"item_id": row["id"], "name": row["name"], "quantity": qty, "amount": row["price"] * qty})

    subtotal = sum(l["amount"] for l in lines)
    discount = 0
    if promo_code:
        promo = conn.execute("SELECT * FROM promos WHERE code = ? AND active = 1", (promo_code.upper(),)).fetchone()
        if promo is None:
            raise PricingError("That promo code is not valid.")
        discount = percent(subtotal, promo["percent_off"])

    shares = [percent(l["amount"], discount * 100 / subtotal) for l in lines]
    for line, share in zip(lines, shares):
        line["discount"] = share
        line["net"] = line["amount"] - share

    food = subtotal - discount
    tax = percent(food + DELIVERY_FEE, TAX_PERCENT)
    return {"lines": lines, "subtotal": subtotal, "discount": discount, "delivery_fee": DELIVERY_FEE,
            "tax": tax, "total": food + DELIVERY_FEE + tax, "promo_code": promo_code.upper() if promo_code else None}
