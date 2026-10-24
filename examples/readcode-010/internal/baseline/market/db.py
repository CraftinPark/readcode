"""SQLite storage for the marketplace: schema, connections and transactions."""
import secrets
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    api_key  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS restaurants (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    timezone            TEXT NOT NULL,       -- IANA name, e.g. America/Toronto
    utc_offset_minutes  INTEGER NOT NULL,    -- offset when the restaurant signed up; shown in the admin list
    opens_at            TEXT NOT NULL,       -- local time, HH:MM
    closes_at           TEXT NOT NULL,       -- local time, HH:MM; may be after midnight
    commission_bps      INTEGER NOT NULL     -- platform commission, basis points of net sales
);

CREATE TABLE IF NOT EXISTS menu_items (
    id             TEXT PRIMARY KEY,
    restaurant_id  TEXT NOT NULL REFERENCES restaurants(id),
    name           TEXT NOT NULL,
    price          INTEGER NOT NULL CHECK (price > 0)
);

CREATE TABLE IF NOT EXISTS promos (
    code         TEXT PRIMARY KEY,
    percent_off  INTEGER NOT NULL CHECK (percent_off BETWEEN 1 AND 100),
    active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS couriers (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    on_shift     INTEGER NOT NULL DEFAULT 1,
    active_jobs  INTEGER NOT NULL DEFAULT 0 CHECK (active_jobs >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id                   TEXT PRIMARY KEY,
    customer_id          TEXT NOT NULL REFERENCES customers(id),
    restaurant_id        TEXT NOT NULL REFERENCES restaurants(id),
    status               TEXT NOT NULL,     -- placed | accepted | assigned | picked_up | delivered | cancelled
    payment_status       TEXT NOT NULL,     -- pending | paid | failed | refunded
    courier_id           TEXT REFERENCES couriers(id),
    subtotal             INTEGER NOT NULL,
    discount             INTEGER NOT NULL,
    delivery_fee         INTEGER NOT NULL,
    tax                  INTEGER NOT NULL,
    total                INTEGER NOT NULL,
    promo_code           TEXT,
    provider_payment_id  TEXT,
    created_ms           INTEGER NOT NULL,
    updated_ms           INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS order_lines (
    id         TEXT PRIMARY KEY,
    order_id   TEXT NOT NULL REFERENCES orders(id),
    item_id    TEXT NOT NULL,
    name       TEXT NOT NULL,
    quantity   INTEGER NOT NULL,
    amount     INTEGER NOT NULL,    -- quantity * unit price
    discount   INTEGER NOT NULL,    -- this line's share of the order discount
    net        INTEGER NOT NULL     -- amount - discount; what the restaurant is paid on
);

CREATE TABLE IF NOT EXISTS refunds (
    id                  TEXT PRIMARY KEY,
    order_id            TEXT NOT NULL REFERENCES orders(id),
    amount              INTEGER NOT NULL CHECK (amount > 0),
    status              TEXT NOT NULL,      -- pending | succeeded | failed
    provider_refund_id  TEXT,
    created_ms          INTEGER NOT NULL,
    settled_ms          INTEGER
);

CREATE TABLE IF NOT EXISTS payouts (
    id               TEXT PRIMARY KEY,
    restaurant_id    TEXT NOT NULL REFERENCES restaurants(id),
    period_start_ms  INTEGER NOT NULL,
    period_end_ms    INTEGER NOT NULL,
    gross            INTEGER NOT NULL,
    refunds          INTEGER NOT NULL,
    commission       INTEGER NOT NULL,
    amount           INTEGER NOT NULL,
    created_ms       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_events (
    id           TEXT PRIMARY KEY,       -- the provider's event id; a redelivery has the same id
    type         TEXT NOT NULL,
    received_ms  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id          TEXT PRIMARY KEY,
    recipient   TEXT NOT NULL,           -- customer:<id> | restaurant:<id> | courier:<id>
    kind        TEXT NOT NULL,
    order_id    TEXT,
    created_ms  INTEGER NOT NULL
);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def now_ms(clock) -> int:
    return int(clock() * 1000)


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init(path: str, seed: dict) -> None:
    """Create the schema and insert seed rows: {table: [row dict, ...]}."""
    conn = connect(path)
    conn.executescript(SCHEMA)
    with transaction(conn):
        for table, rows in seed.items():
            for row in rows:
                cols = ", ".join(row)
                marks = ", ".join("?" for _ in row)
                conn.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))
    conn.close()
