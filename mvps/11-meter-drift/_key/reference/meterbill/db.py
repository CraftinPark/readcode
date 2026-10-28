"""Schema for the meter store (SQLite)."""


def init(conn):
    conn.executescript("""
        create table if not exists readings (meter text not null, ts integer not null, wh integer not null,
                                             sent_ts integer not null, received_at real not null,
                                             primary key (meter, ts));
        create table if not exists rejected (meter text, seq integer, sent_ts integer, received_at real, reason text);
    """)
