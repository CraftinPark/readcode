"""Runs every minute: tick(client, conn, now). Drains the campaign outbox, 600 messages a minute at most."""
from . import log

BATCH = 600


def tick(client, conn, now):
    rows = conn.execute("select id, campaign, to_number, body from outbox where status = 'pending' "
                        "order by id limit ?", (BATCH,)).fetchall()
    for oid, campaign, to, body in rows:
        try:
            resp = client.send(to, body, client_ref=f"outbox:{oid}")
        except client.Timeout:
            log.record(conn, now, "campaign", to, "timeout", None)
            continue  # still pending: retried next tick
        except client.RateLimited as e:
            log.record(conn, now, "campaign", to, "rate_limited", e.headers)
            break
        log.record(conn, now, "campaign", to, "sent", resp["headers"])
        conn.execute("update outbox set status = 'sent', sent_at = ? where id = ?", (now, oid))
    conn.commit()
