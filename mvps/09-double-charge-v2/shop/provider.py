"""Client for the card provider. The provider keeps its own ledger (provider.db): the truth about what
customers' cards were actually charged.

Provider semantics (from their API docs):
- Every charge carries an idempotency_key. A request with a key the provider has seen before is NOT
  processed again: the provider replays the first result for that key, whether it was a capture or a decline.
- A charge can be captured and still time out on our side (the answer arrives after we stop waiting).
- lookup(key) returns the stored result for a key, or None if the provider never saw it.
"""
import os
import sqlite3
import time

LEDGER = os.environ.get("PROVIDER_DB", "provider.db")
LATENCY = float(os.environ.get("PROVIDER_LATENCY", "0"))
TIMEOUT = 2.0
DECLINING_CARDS = {"4000000000000002"}   # test cards that are always declined


class Timeout(Exception):
    pass


class Declined(Exception):
    pass


def _ledger():
    conn = sqlite3.connect(LEDGER, timeout=10, isolation_level=None)
    conn.execute("create table if not exists charges (idempotency_key text primary key, order_id integer, "
                 "amount_cents integer, card text, result text)")
    return conn


def charge(order_id, amount_cents, card, idempotency_key):
    conn = _ledger()
    row = conn.execute("select result from charges where idempotency_key = ?", (idempotency_key,)).fetchone()
    if row is None:
        result = "declined" if card in DECLINING_CARDS else "captured"
        conn.execute("insert into charges values (?, ?, ?, ?, ?)", (idempotency_key, order_id, amount_cents, card, result))
    else:
        result = row[0]
    if LATENCY >= TIMEOUT:
        raise Timeout(f"provider did not answer within {TIMEOUT}s")
    time.sleep(LATENCY)
    if result == "declined":
        raise Declined("card declined")
    return {"idempotency_key": idempotency_key, "status": "captured"}


def lookup(idempotency_key):
    row = _ledger().execute("select result from charges where idempotency_key = ?", (idempotency_key,)).fetchone()
    return row[0] if row else None
