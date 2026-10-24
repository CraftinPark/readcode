"""Order lifecycle.

    placed -> accepted -> assigned -> picked_up -> delivered
       \\________\\__________\\___________-> cancelled

Payment has its own status (see payments.py). The kitchen only starts on an
order once its payment is confirmed.
"""
from . import dispatch, payments
from .db import new_id, transaction
from .pricing import quote

CANCELLABLE = ("placed", "accepted", "assigned", "picked_up")


class OrderError(Exception):
    pass


def get(conn, order_id: str, customer_id: str | None = None):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None or (customer_id is not None and row["customer_id"] != customer_id):
        raise OrderError(f"No such order: {order_id}")
    return row


def lines(conn, order_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM order_lines WHERE order_id = ? ORDER BY id", (order_id,))]


def place(conn, provider, customer_id: str, restaurant_id: str, items: list[dict], promo_code: str | None,
          payment_method: str, now_ms: int) -> str:
    q = quote(conn, restaurant_id, items, promo_code)
    order_id = new_id("ord")
    with transaction(conn):
        conn.execute("INSERT INTO orders (id, customer_id, restaurant_id, status, payment_status, subtotal, discount, "
                     "delivery_fee, tax, total, promo_code, created_ms, updated_ms) "
                     "VALUES (?, ?, ?, 'placed', 'pending', ?, ?, ?, ?, ?, ?, ?, ?)",
                     (order_id, customer_id, restaurant_id, q["subtotal"], q["discount"], q["delivery_fee"],
                      q["tax"], q["total"], q["promo_code"], now_ms, now_ms))
        for i, l in enumerate(q["lines"]):
            conn.execute("INSERT INTO order_lines (id, order_id, item_id, name, quantity, amount, discount, net) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (f"{order_id}_{i}", order_id, l["item_id"], l["name"], l["quantity"], l["amount"],
                          l["discount"], l["net"]))
    payments.start_payment(conn, provider, order_id, payment_method, now_ms)
    return order_id


def accept(conn, order_id: str, now_ms: int) -> None:
    with transaction(conn):
        order = get(conn, order_id)
        if order["status"] != "placed" or order["payment_status"] != "paid":
            raise OrderError("Only placed, paid orders can be accepted.")
        conn.execute("UPDATE orders SET status = 'accepted', updated_ms = ? WHERE id = ?", (now_ms, order_id))


def picked_up(conn, order_id: str, now_ms: int) -> None:
    with transaction(conn):
        if get(conn, order_id)["status"] != "assigned":
            raise OrderError("Only assigned orders can be picked up.")
        conn.execute("UPDATE orders SET status = 'picked_up', updated_ms = ? WHERE id = ?", (now_ms, order_id))


def delivered(conn, order_id: str, now_ms: int) -> None:
    with transaction(conn):
        order = get(conn, order_id)
        if order["status"] != "picked_up":
            raise OrderError("Only picked-up orders can be delivered.")
        conn.execute("UPDATE orders SET status = 'delivered', updated_ms = ? WHERE id = ?", (now_ms, order_id))
        dispatch.release(conn, order["courier_id"])


def cancel(conn, provider, order_id: str, now_ms: int, customer_id: str | None = None) -> None:
    """Cancel an order and give the money back."""
    order = get(conn, order_id, customer_id)
    if order["status"] not in CANCELLABLE:
        raise OrderError(f"A {order['status']} order cannot be cancelled.")
    with transaction(conn):
        if order["status"] in ("assigned", "picked_up"):
            dispatch.release(conn, order["courier_id"])
        conn.execute("UPDATE orders SET status = 'cancelled', updated_ms = ? WHERE id = ?", (now_ms, order_id))
        conn.execute("INSERT INTO notifications (id, recipient, kind, order_id, created_ms) VALUES (?, ?, 'order_cancelled', ?, ?)",
                     (new_id("ntf"), f"restaurant:{order['restaurant_id']}", order_id, now_ms))
    if order["payment_status"] in ("pending", "paid"):
        payments.refund(conn, provider, order_id, order["total"], now_ms)
