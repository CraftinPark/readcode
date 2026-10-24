"""Payments and refunds through the provider, and the provider's webhook events.

Calls to the provider only start things; the result arrives as an event:
payment.succeeded / payment.failed / refund.succeeded.
"""
from .db import new_id, transaction

class PaymentError(Exception):
    pass


def start_payment(conn, provider, order_id: str, method: str, now_ms: int) -> None:
    order = conn.execute("SELECT total FROM orders WHERE id = ?", (order_id,)).fetchone()
    pay = provider.create_payment(order["total"], method, reference=order_id)
    conn.execute("UPDATE orders SET provider_payment_id = ?, updated_ms = ? WHERE id = ?", (pay["id"], now_ms, order_id))


def refund(conn, provider, order_id: str, amount: int, now_ms: int) -> str:
    """Ask the provider to refund part or all of an order. The refund is pending
    until the provider's refund.succeeded event arrives."""
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    refunded = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM refunds WHERE order_id = ? AND status != 'failed'",
                            (order_id,)).fetchone()[0]
    if amount <= 0 or refunded + amount > order["total"]:
        raise PaymentError("The refund is larger than what is left on the order.")
    r = provider.refund(order["provider_payment_id"], amount)
    refund_id = new_id("rf")
    conn.execute("INSERT INTO refunds (id, order_id, amount, status, provider_refund_id, created_ms) "
                 "VALUES (?, ?, ?, 'pending', ?, ?)", (refund_id, order_id, amount, r["id"], now_ms))
    return refund_id


def _set_payment_status(conn, order, new: str, now_ms: int) -> bool:
    current = order["payment_status"]
    if new == current:
        return False
    conn.execute("UPDATE orders SET payment_status = ?, updated_ms = ? WHERE id = ?", (new, now_ms, order["id"]))
    return True


def _notify(conn, recipient: str, kind: str, order_id: str, now_ms: int) -> None:
    conn.execute("INSERT INTO notifications (id, recipient, kind, order_id, created_ms) VALUES (?, ?, ?, ?, ?)",
                 (new_id("ntf"), recipient, kind, order_id, now_ms))


def handle_event(conn, event: dict, now_ms: int) -> str:
    """Apply one provider event. Returns what happened, for the logs."""
    with transaction(conn):
        if conn.execute("SELECT 1 FROM provider_events WHERE id = ?", (event["id"],)).fetchone():
            return "already processed"
        conn.execute("INSERT INTO provider_events (id, type, received_ms) VALUES (?, ?, ?)",
                     (event["id"], event["type"], now_ms))
        data = event["data"]

        if event["type"] in ("payment.succeeded", "payment.failed"):
            order = conn.execute("SELECT * FROM orders WHERE provider_payment_id = ?", (data["payment_id"],)).fetchone()
            if order is None:
                return "unknown payment"
            new = "paid" if event["type"] == "payment.succeeded" else "failed"
            if not _set_payment_status(conn, order, new, now_ms):
                return f"ignored: order is already {order['payment_status']}"
            if new == "paid":
                _notify(conn, f"restaurant:{order['restaurant_id']}", "new_order", order["id"], now_ms)
                _notify(conn, f"customer:{order['customer_id']}", "payment_confirmed", order["id"], now_ms)
            return f"order {order['id']} is now {new}"

        if event["type"] == "refund.succeeded":
            row = conn.execute("SELECT * FROM refunds WHERE provider_refund_id = ?", (data["refund_id"],)).fetchone()
            if row is None:
                return "unknown refund"
            conn.execute("UPDATE refunds SET status = 'succeeded', settled_ms = ? WHERE id = ?", (now_ms, row["id"]))
            order = conn.execute("SELECT * FROM orders WHERE id = ?", (row["order_id"],)).fetchone()
            done = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM refunds WHERE order_id = ? AND status = 'succeeded'",
                                (order["id"],)).fetchone()[0]
            if done >= order["total"]:
                _set_payment_status(conn, order, "refunded", now_ms)
            return f"refund {row['id']} settled"

        return f"ignored event type {event['type']}"
