"""Courier dispatch.

A courier can carry up to MAX_ACTIVE_JOBS orders at once. active_jobs is kept
on the courier row so dispatch does not have to scan every open order.
"""
from .db import transaction

MAX_ACTIVE_JOBS = 2


class NoCourier(Exception):
    pass


def available_couriers(conn) -> list[dict]:
    rows = conn.execute("SELECT id, name, active_jobs FROM couriers WHERE on_shift = 1 AND active_jobs < ? "
                        "ORDER BY active_jobs, id", (MAX_ACTIVE_JOBS,)).fetchall()
    return [dict(r) for r in rows]


def assign(conn, order_id: str, now_ms: int) -> str:
    """Give the order to the least busy courier on shift."""
    with transaction(conn):
        order = conn.execute("SELECT status, courier_id FROM orders WHERE id = ?", (order_id,)).fetchone()
        if order is None or order["status"] not in ("placed", "accepted"):
            raise NoCourier("Only placed or accepted orders can be dispatched.")
        courier = conn.execute("SELECT id FROM couriers WHERE on_shift = 1 AND active_jobs < ? "
                               "ORDER BY active_jobs, id LIMIT 1", (MAX_ACTIVE_JOBS,)).fetchone()
        if courier is None:
            raise NoCourier("No courier is available right now.")
        conn.execute("UPDATE couriers SET active_jobs = active_jobs + 1 WHERE id = ?", (courier["id"],))
        conn.execute("UPDATE orders SET courier_id = ?, status = 'assigned', updated_ms = ? WHERE id = ?",
                     (courier["id"], now_ms, order_id))
        conn.execute("INSERT INTO notifications (id, recipient, kind, order_id, created_ms) VALUES (?, ?, 'pickup_request', ?, ?)",
                     (f"ntf_{order_id}_{courier['id']}", f"courier:{courier['id']}", order_id, now_ms))
    return courier["id"]


def release(conn, courier_id: str) -> None:
    """The courier has one job fewer. Call inside the caller's transaction."""
    conn.execute("UPDATE couriers SET active_jobs = MAX(active_jobs - 1, 0) WHERE id = ?", (courier_id,))
