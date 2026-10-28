"""Shared database. In production this is Postgres; locally a SQLite file that every pod opens."""
import os
import sqlite3

DB_PATH = os.environ.get("SHOP_DB", "shop.db")

SCHEMA = """
create table if not exists orders (
    id integer primary key,
    customer text not null,
    amount_cents integer not null,
    status text not null default 'open'
);
create table if not exists payments (
    request_id text primary key,
    order_id integer not null,
    status text not null
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.executescript(SCHEMA)
    return conn
