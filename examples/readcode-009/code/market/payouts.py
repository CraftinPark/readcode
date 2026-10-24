"""Restaurant payouts.

A payout covers everything since the restaurant's previous payout: the net
food sales of delivered orders, minus refunds given on those orders, minus the
platform's commission. Each order and each refund belongs to exactly one payout
period, by the time it was created.
"""
from .db import new_id, transaction
from .money import percent


def _window(conn, restaurant_id: str, now_ms: int) -> tuple[int, int]:
    last = conn.execute("SELECT MAX(period_end_ms) FROM payouts WHERE restaurant_id = ?", (restaurant_id,)).fetchone()[0]
    return (last or 0), now_ms


def preview(conn, restaurant, now_ms: int) -> dict:
    start, end = _window(conn, restaurant["id"], now_ms)
    gross = conn.execute(
        "SELECT COALESCE(SUM(l.net), 0) FROM order_lines l JOIN orders o ON o.id = l.order_id "
        "WHERE o.restaurant_id = ? AND o.status = 'delivered' AND o.created_ms > ? AND o.created_ms <= ?",
        (restaurant["id"], start, end)).fetchone()[0]
    refunds = conn.execute(
        "SELECT COALESCE(SUM(r.amount), 0) FROM refunds r JOIN orders o ON o.id = r.order_id "
        "WHERE o.restaurant_id = ? AND o.status = 'delivered' AND r.status = 'succeeded' "
        "AND r.created_ms > ? AND r.created_ms <= ?",
        (restaurant["id"], start, end)).fetchone()[0]
    commission = percent(gross, restaurant["commission_bps"] / 100)
    return {"restaurant_id": restaurant["id"], "period_start_ms": start, "period_end_ms": end,
            "gross": gross, "refunds": refunds, "commission": commission, "amount": gross - refunds - commission}


def run(conn, now_ms: int) -> list[dict]:
    """Pay every restaurant for its current period. Run weekly by a scheduler."""
    out = []
    with transaction(conn):
        for r in conn.execute("SELECT * FROM restaurants ORDER BY id").fetchall():
            p = preview(conn, r, now_ms)
            if not p["gross"] and not p["refunds"]:
                continue
            p["id"] = new_id("po")
            conn.execute("INSERT INTO payouts (id, restaurant_id, period_start_ms, period_end_ms, gross, refunds, "
                         "commission, amount, created_ms) VALUES (:id, :restaurant_id, :period_start_ms, "
                         ":period_end_ms, :gross, :refunds, :commission, :amount, :period_end_ms)", p)
            out.append(p)
    return out
