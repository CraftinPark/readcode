"""SQLite storage: schema, connections and transactions.

Every server process opens its own connection to the same database file, so
anything that must be shared between servers (idempotency keys, events) lives
here rather than in memory.
"""
import secrets
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    secret_key  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS charges (
    id                TEXT PRIMARY KEY,
    account_id        TEXT NOT NULL REFERENCES accounts(id),
    amount            INTEGER NOT NULL CHECK (amount > 0),
    currency          TEXT NOT NULL,
    status            TEXT NOT NULL,          -- succeeded | failed
    authorization_id  TEXT,
    failure_code      TEXT,
    amount_refunded   INTEGER NOT NULL DEFAULT 0 CHECK (amount_refunded >= 0),
    created_ms        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS charges_by_account ON charges (account_id, created_ms DESC, id DESC);

CREATE TABLE IF NOT EXISTS refunds (
    id          TEXT PRIMARY KEY,
    charge_id   TEXT NOT NULL REFERENCES charges(id),
    amount      INTEGER NOT NULL CHECK (amount > 0),
    network_id  TEXT NOT NULL,
    created_ms  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    account_id    TEXT NOT NULL,
    key           TEXT NOT NULL,
    request_hash  TEXT NOT NULL,
    state         TEXT NOT NULL,              -- in_progress | done
    status_code   INTEGER,
    body          TEXT,
    created_ms    INTEGER NOT NULL,
    PRIMARY KEY (account_id, key)
);

CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL REFERENCES accounts(id),
    url         TEXT NOT NULL,
    secret      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id               TEXT PRIMARY KEY,
    account_id       TEXT NOT NULL,
    type             TEXT NOT NULL,
    payload          TEXT NOT NULL,
    created_ms       INTEGER NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    next_attempt_ms  INTEGER NOT NULL,
    delivered_ms     INTEGER,
    failed           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS events_due ON events (delivered_ms, failed, next_attempt_ms);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def now_ms(clock) -> int:
    """Milliseconds since the epoch. Every *_ms column uses this unit."""
    return int(clock() * 1000)


def connect(path: str) -> sqlite3.Connection:
    # isolation_level=None: we issue BEGIN/COMMIT ourselves in transaction().
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """BEGIN IMMEDIATE takes the write lock up front, so two servers cannot
    interleave writes to the same rows."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init(path: str, accounts: list[dict], endpoints: list[dict] = ()) -> None:
    conn = connect(path)
    conn.executescript(SCHEMA)
    with transaction(conn):
        for a in accounts:
            conn.execute("INSERT OR IGNORE INTO accounts (id, name, secret_key) VALUES (?, ?, ?)",
                         (a["id"], a["name"], a["secret_key"]))
        for e in endpoints:
            conn.execute("INSERT OR IGNORE INTO webhook_endpoints (id, account_id, url, secret) VALUES (?, ?, ?, ?)",
                         (e["id"], e["account_id"], e["url"], e["secret"]))
    conn.close()
