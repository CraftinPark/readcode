"""The tempting fix: remember paid orders in the process. Passes unit_check.py, fails the replay."""
import logging

from . import db, provider

log = logging.getLogger("shop.checkout")
_paid_orders = set()


def pay(order_id, request_id):
    if order_id in _paid_orders:
        return "paid"
    conn = db.connect()
    order = conn.execute("select amount_cents, status from orders where id = ?", (order_id,)).fetchone()
    if order is None:
        return "no_such_order"
    amount, status = order
    try:
        provider.charge(order_id, amount, idempotency_key=request_id)
    except provider.Timeout:
        return "unknown"
    _paid_orders.add(order_id)
    conn.execute("update orders set status = 'paid' where id = ?", (order_id,))
    return "paid"
