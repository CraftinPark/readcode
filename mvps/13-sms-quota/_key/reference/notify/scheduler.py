"""Runs every minute: tick(client, conn, now). Drains the campaign outbox, 600 messages a minute at most."""
from . import log

BATCH = 600
DAILY_QUOTA = 10000   # Textly account limit per UTC day (X-RateLimit-Remaining starts there each day)
OTP_RESERVE = 4000    # login codes run ~3,000/day; campaigns never eat into this


def _remaining(conn, now):
    row = conn.execute("select remaining, seen_at from quota where id = 1").fetchone()
    if row is None or row[1] // 86400 != now // 86400:
        return DAILY_QUOTA
    return row[0]


def tick(client, conn, now):
    rows = conn.execute("select id, campaign, to_number, body from outbox where status = 'pending' "
                        "order by id limit ?", (BATCH,)).fetchall()
    for oid, campaign, to, body in rows:
        if _remaining(conn, now) <= OTP_RESERVE:
            break  # leave the rest for tomorrow: the quota is shared with login codes
        try:
            resp = client.send(to, body, client_ref=f"outbox:{oid}")
        except client.Timeout:
            log.record(conn, now, "campaign", to, "timeout", None)
            continue  # still pending: retried next tick
        except client.RateLimited as e:
            log.record(conn, now, "campaign", to, "rate_limited", e.headers)
            break
        log.record(conn, now, "campaign", to, "sent", resp["headers"])
        log.note_quota(conn, now, resp["headers"])
        conn.execute("update outbox set status = 'sent', sent_at = ? where id = ?", (now, oid))
    conn.commit()
