"""Schema (same as production).

subscriptions.status: see status.py. charges.kind is 'charge' or 'refund' (amount_cents always positive).
reseller_events: cancellations reported by our reseller partner (Bundlr), with when they took effect and when
their webhook reached us.
"""
SCHEMA = """
create table if not exists subscriptions (id integer primary key, customer text, channel text, plan text,
                                          plan_cents integer, status text, period_end integer, trial_end integer,
                                          meta text);
create table if not exists charges (id integer primary key, sub_id integer, kind text, amount_cents integer,
                                    at integer);
create table if not exists reseller_events (id integer primary key, sub_id integer, type text,
                                            effective_at integer, received_at integer);
"""


def init(conn):
    conn.executescript(SCHEMA)
