"""The renewal job. Runs every hour: run_renewals(conn, now)."""
from . import status

MONTH = 30 * 86400


def run_renewals(conn, now):
    conn.execute("update subscriptions set status = ? where status = ? and period_end <= ?",
                 (status.CANCELLED, status.CANCEL_PENDING, now))
    due = conn.execute("select id, plan_cents, period_end, status from subscriptions where status in (%s) "
                       "and period_end <= ?" % ",".join("?" * len(status.BILLABLE)),
                       (*status.BILLABLE, now)).fetchall()
    for sub_id, cents, period_end, st in due:
        conn.execute("insert into charges (sub_id, kind, amount_cents, at) values (?, 'charge', ?, ?)",
                     (sub_id, cents, now))
        new_status = status.ACTIVE if st in (status.TRIALING, status.PAST_DUE) else st
        conn.execute("update subscriptions set period_end = ?, status = ? where id = ?",
                     (period_end + MONTH, new_status, sub_id))
    conn.commit()
