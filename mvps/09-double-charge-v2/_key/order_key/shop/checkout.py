"""What all three gate runs on MVP 05 shipped: one provider key per order.
The Pay button. The app sends a fresh request_id with every tap, and the card the customer chose."""
import logging

from . import db, provider

log = logging.getLogger("shop.checkout")


def pay(order_id, request_id, card="4242424242424242"):
    conn = db.connect()
    order = conn.execute("select amount_cents, status from orders where id = ?", (order_id,)).fetchone()
    if order is None:
        return "no_such_order"
    amount, status = order

    if status == "paid":
        return "paid"

    conn.execute("insert into payments (request_id, order_id, status) values (?, ?, 'pending')", (request_id, order_id))
    try:
        provider.charge(order_id, amount, card, idempotency_key=f"order-{order_id}")
    except provider.Declined:
        conn.execute("update payments set status = 'declined' where request_id = ?", (request_id,))
        return "declined"
    except provider.Timeout:
        log.warning("provider timeout order=%s request=%s", order_id, request_id)
        conn.execute("update payments set status = 'unknown' where request_id = ?", (request_id,))
        return "unknown"

    conn.execute("update payments set status = 'paid' where request_id = ?", (request_id,))
    conn.execute("update orders set status = 'paid' where id = ?", (order_id,))
    return "paid"
