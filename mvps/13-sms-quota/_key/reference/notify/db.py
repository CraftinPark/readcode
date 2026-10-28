SCHEMA = """
create table if not exists outbox (id integer primary key, campaign text, to_number text, body text,
                                   created_at integer, status text default 'pending', sent_at integer);
create table if not exists sends (id integer primary key, ts integer, kind text, to_number text, status text,
                                  headers text);
create table if not exists quota (id integer primary key check (id = 1), remaining integer, seen_at integer);
"""


def init(conn):
    conn.executescript(SCHEMA)
