"""Client for the card provider. The provider keeps its own ledger (provider.db), which is the truth
about what the customer's card was actually charged. It dedupes on idempotency_key, like real providers."""
import os
import sqlite3
import time

LEDGER = os.environ.get("PROVIDER_DB", "provider.db")
# Seconds the provider takes to answer. Our client gives up after TIMEOUT.
LATENCY = float(os.environ.get("PROVIDER_LATENCY", "0"))
TIMEOUT = 2.0


class Timeout(Exception):
    pass


def _ledger():
    conn = sqlite3.connect(LEDGER, timeout=10, isolation_level=None)
    conn.execute("create table if not exists charges (idempotency_key text primary key, order_id integer, amount_cents integer)")
    return conn


def charge(order_id, amount_cents, idempotency_key):
    conn = _ledger()
    conn.execute("insert or ignore into charges values (?, ?, ?)", (idempotency_key, order_id, amount_cents))
    if LATENCY >= TIMEOUT:
        # The charge went through, but the answer arrives after we stopped waiting.
        raise Timeout(f"provider did not answer within {TIMEOUT}s")
    time.sleep(LATENCY)
    return {"idempotency_key": idempotency_key, "status": "captured"}
