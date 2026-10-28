"""POST /webhooks/bundlr: our reseller partner tells us about cancellations.

    {"sub_id": 4411, "type": "cancelled", "effective_at": 1792000000, "received_at": 1792003600}
"""
from . import status


def handle_reseller_event(conn, event):
    conn.execute("insert into reseller_events (sub_id, type, effective_at, received_at) values (?, ?, ?, ?)",
                 (event["sub_id"], event["type"], event["effective_at"], event["received_at"]))
    if event["type"] == "cancelled":
        conn.execute("update subscriptions set status = ? where id = ?", (status.CANCELLED, event["sub_id"]))
    conn.commit()
