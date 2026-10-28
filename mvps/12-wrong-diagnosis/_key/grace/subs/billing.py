"""The renewal job. Runs every hour: run_renewals(conn, now)."""
from . import status

MONTH = 30 * 86400


def run_renewals(conn, now):
    # Marta's fix: Bundlr webhooks lag, so give reseller subscriptions 24 h to cancel before we charge.
    due = conn.execute("select id, plan_cents, period_end, status from subscriptions "
                       "where status != ? and period_end <= ? and (channel != 'reseller' or period_end <= ?)",
                       (status.CANCELLED, now, now - 24 * 3600)).fetchall()
    for sub_id, cents, period_end, st in due:
        conn.execute("insert into charges (sub_id, kind, amount_cents, at) values (?, 'charge', ?, ?)",
                     (sub_id, cents, now))
        new_status = status.ACTIVE if st in (status.TRIALING, status.PAST_DUE) else st
        conn.execute("update subscriptions set period_end = ?, status = ? where id = ?",
                     (period_end + MONTH, new_status, sub_id))
    conn.commit()
