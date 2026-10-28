"""POST /webhooks/bundlr: our reseller partner tells us about cancellations.

    {"sub_id": 4411, "type": "cancelled", "effective_at": 1792000000, "received_at": 1792003600}
"""
from . import status


def handle_reseller_event(conn, event):
    conn.execute("insert into reseller_events (sub_id, type, effective_at, received_at) values (?, ?, ?, ?)",
                 (event["sub_id"], event["type"], event["effective_at"], event["received_at"]))
    if event["type"] == "cancelled":
        conn.execute("update subscriptions set status = ? where id = ?", (status.CANCELLED, event["sub_id"]))
        # Bundlr webhooks can land after we already renewed: refund renewals made after the cancellation.
        for charge_id, cents in conn.execute("select id, amount_cents from charges where sub_id = ? and kind = 'charge' "
                                             "and at >= ?", (event["sub_id"], event["effective_at"])).fetchall():
            conn.execute("insert into charges (sub_id, kind, amount_cents, at) values (?, 'refund', ?, ?)",
                         (event["sub_id"], cents, event["received_at"]))
    conn.commit()
