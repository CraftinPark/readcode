"""Replays October's five escalations: the renewal job runs every hour, Bundlr's webhooks arrive when they
actually arrived, and each customer must end up paying nothing for the renewal after they cancelled.

    python check.py
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from subs import billing, db, webhooks  # noqa: E402

cases = json.load(open(os.path.join(HERE, "escalations", "october.json")))
conn = sqlite3.connect(":memory:")
db.init(conn)
for c in cases:
    s = c["sub"]
    conn.execute("insert into subscriptions values (?,?,?,?,?,?,?,?,?)", tuple(s[k] for k in (
        "id", "customer", "channel", "plan", "plan_cents", "status", "period_end", "trial_end", "meta")))
events = sorted((c["event"] for c in cases), key=lambda e: e["received_at"])
start = min(c["sub"]["period_end"] for c in cases) - 86400
end = max(e["received_at"] for e in events) + 3 * 86400
t, k = start - start % 3600, 0
while t <= end:
    while k < len(events) and events[k]["received_at"] <= t:
        webhooks.handle_reseller_event(conn, events[k])
        k += 1
    billing.run_renewals(conn, t)
    t += 3600
bad = 0
for c in cases:
    sid = c["sub"]["id"]
    net = conn.execute("select coalesce(sum(case kind when 'refund' then -amount_cents else amount_cents end), 0) "
                       "from charges where sub_id = ?", (sid,)).fetchone()[0]
    print(f"  {c['sub']['customer']:<22} net charged after cancelling: {net / 100:.2f}")
    bad += net != 0
print("all five OK" if not bad else f"{bad} of 5 still charged")
sys.exit(1 if bad else 0)
