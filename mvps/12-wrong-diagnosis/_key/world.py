"""The production world behind MVP 12 (key only).

Hidden truth: production has two subscription statuses no code in the repo knows about.
- cancel_pending: written by the support console (another team's tool) when support cancels "at period end".
  Must NOT be charged at renewal. The shipped billing charges everything that isn't 'cancelled', so it is.
- active_migrated: written by the July 2026 legacy-plan migration. These are paying customers and MUST be
  charged. An allow-list fix ('active', 'past_due', 'trialing') silently stops charging them.
And the senior engineer's diagnosis (reseller cancellation webhooks arrive late; wait 24 h) is real but
incomplete: some reseller webhooks arrive up to 31 h late, so the charge has to be refunded when they land.
"""
import datetime as dt
import json
import random
import sqlite3

DAY = 86400
NOW = int(dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc).timestamp())     # snapshot time
NOV1 = int(dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc).timestamp())
DEC1 = NOV1 + 30 * DAY
LAST_RENEWAL = NOW + 30 * DAY  # everyone renews within a month of their last charge (before NOW)
SCHEMA = """
create table subscriptions (id integer primary key, customer text, channel text, plan text, plan_cents integer,
                            status text, period_end integer, trial_end integer, meta text);
create table charges (id integer primary key, sub_id integer, kind text, amount_cents integer, at integer);
create table reseller_events (id integer primary key, sub_id integer, type text, effective_at integer,
                              received_at integer);
"""
PLANS = [("basic", 900), ("plus", 1900), ("pro", 4900)]
FIRST = ["ana", "ben", "chen", "dee", "eli", "fay", "gus", "hana", "ivo", "jun", "kai", "lea", "mo", "nia", "oli",
         "pia", "raj", "sol", "tia", "uma", "vik", "wen", "yas", "zoe"]


def build(seed=12):
    """Returns (conn with the production snapshot at NOW, future reseller events for Nov)."""
    r = random.Random(seed)
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    future = []
    n = 0

    def add(status, channel, meta=None, period_end=None, trial_end=None):
        nonlocal n
        n += 1
        plan, cents = r.choice(PLANS)
        if status == "active_migrated":
            plan, cents = "gold-legacy", r.choice([1500, 2500])
        pe = period_end or (NOV1 + r.randint(0, LAST_RENEWAL - NOV1 - 1))
        conn.execute("insert into subscriptions values (?,?,?,?,?,?,?,?,?)",
                     (n, f"{r.choice(FIRST)}.{r.randint(10, 999)}@example.com", channel, plan, cents, status, pe,
                      trial_end, json.dumps(meta) if meta else None))
        # history: past monthly charges
        if status not in ("trialing",):
            for k in range(1, r.randint(2, 9)):
                conn.execute("insert into charges (sub_id, kind, amount_cents, at) values (?,?,?,?)",
                             (n, "charge", cents, pe - 30 * DAY * k + r.randint(0, 300)))
        return n, pe

    for _ in range(3900):
        add("active", "reseller" if r.random() < 0.13 else "web")
    for _ in range(150):
        add("past_due", "web")
    for _ in range(300):
        t = NOV1 + r.randint(0, LAST_RENEWAL - NOV1 - 1)
        add("trialing", "web", period_end=t, trial_end=t)
    for _ in range(500):
        sid, _ = add("cancelled", r.choice(["web", "web", "reseller"]), period_end=NOW - r.randint(1, 200) * DAY)
    for _ in range(90):
        add("cancel_pending", "web", meta={"source": "support-console", "by": r.choice(["agent.kim", "agent.ola",
                                                                                         "agent.ravi"]),
                                           "note": r.choice(["cust asked to stop at end of month", "moving abroad",
                                                             "too expensive", "cancel eop pls"])})
    for _ in range(60):
        add("active_migrated", "web", meta={"source": "plan-migration-2026-07", "from_plan": "gold"})

    # Reseller cancellation history (last 6 months) and next month's cancellations.
    resellers = [row[0] for row in conn.execute("select id from subscriptions where channel='reseller' and status='active'")]

    def delay():
        return r.randint(20 * 60, 3 * 3600) if r.random() < 0.86 else r.randint(20 * 3600, 31 * 3600)

    for _ in range(260):
        eff = NOW - r.randint(1, 180) * DAY + r.randint(0, DAY)
        conn.execute("insert into reseller_events (sub_id, type, effective_at, received_at) values (?,?,?,?)",
                     (r.choice(resellers), "cancelled", eff, eff + delay()))
    picked = r.sample(resellers, 45)
    for sid in picked:
        pe = conn.execute("select period_end from subscriptions where id=?", (sid,)).fetchone()[0]
        eff = pe - r.randint(60, 2 * DAY) if r.random() < 0.8 else pe + r.randint(3600, 5 * DAY)
        future.append({"sub_id": sid, "type": "cancelled", "effective_at": eff, "received_at": eff + delay()})
    # Make sure the long tail is present among cancellations that land just before renewal.
    late = [e for e in future if e["effective_at"] < conn.execute("select period_end from subscriptions where id=?",
                                                                  (e["sub_id"],)).fetchone()[0]]
    for e in late[:5]:
        e["received_at"] = e["effective_at"] + r.randint(25 * 3600, 31 * 3600)
    conn.commit()
    return conn, sorted(future, key=lambda e: e["received_at"])


def truth(conn, future):
    """Net cents each subscription should pay for renewals in [NOV1, DEC1)."""
    cancel_eff = {e["sub_id"]: e["effective_at"] for e in future}
    out = {}
    for sid, status, cents, pe, trial_end in conn.execute(
            "select id, status, plan_cents, period_end, trial_end from subscriptions"):
        owe = 0
        if NOV1 <= pe < DEC1 and status in ("active", "past_due", "active_migrated", "trialing"):
            owe = cents
            if sid in cancel_eff and cancel_eff[sid] < pe:
                owe = 0
        out[sid] = owe
    return out
