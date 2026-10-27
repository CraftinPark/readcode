"""The Pay button. The app sends a fresh request_id with every tap."""
import logging

from . import db, provider

log = logging.getLogger("shop.checkout")


def pay(order_id, request_id):
    conn = db.connect()
    order = conn.execute("select amount_cents, status from orders where id = ?", (order_id,)).fetchone()
    if order is None:
        return "no_such_order"
    amount, status = order

    seen = conn.execute("select status from payments where request_id = ?", (request_id,)).fetchone()
    if seen:
        return seen[0]

    conn.execute("insert into payments (request_id, order_id, status) values (?, ?, 'pending')", (request_id, order_id))
    try:
        provider.charge(order_id, amount, idempotency_key=request_id)
    except provider.Timeout:
        log.warning("provider timeout order=%s request=%s", order_id, request_id)
        conn.execute("update payments set status = 'unknown' where request_id = ?", (request_id,))
        return "unknown"

    conn.execute("update payments set status = 'paid' where request_id = ?", (request_id,))
    conn.execute("update orders set status = 'paid' where id = ?", (order_id,))
    return "paid"
