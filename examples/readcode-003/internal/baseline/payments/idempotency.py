"""Idempotency keys for POST /charges.

A client sends Idempotency-Key with a create request so it can retry safely
after a timeout or a dropped connection. The first request with a key claims
it (state in_progress); when it finishes, its response is saved (state done)
and every retry with the same key gets that response back. Keys are kept for
24 hours and are scoped to the account.
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from .db import transaction

KEY_TTL = timedelta(hours=24)
# How long an in_progress claim blocks retries before we assume the server
# handling it died and let a retry take the key over.
CLAIM_TIMEOUT = timedelta(seconds=60)


class KeyConflict(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class SavedResponse:
    status_code: int
    body: dict


def request_hash(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def network_reference(account_id: str, key: str) -> str:
    """The reference sent to the card network for a request made with this key."""
    return f"idem:{account_id}:{key}"


def claim(conn, account_id: str, key: str, req_hash: str, now_ms: int) -> Optional[SavedResponse]:
    """Claim the key for a new request, or return the saved response of an
    earlier request with the same key. Raises KeyConflict if it cannot do either."""
    cutoff = now_ms - int(KEY_TTL.total_seconds() * 1000)
    with transaction(conn):
        conn.execute("DELETE FROM idempotency_keys WHERE created_ms < ?", (cutoff,))
        row = conn.execute("SELECT request_hash, state, status_code, body, created_ms FROM idempotency_keys "
                           "WHERE account_id = ? AND key = ?", (account_id, key)).fetchone()
        if row is None:
            conn.execute("INSERT INTO idempotency_keys (account_id, key, request_hash, state, created_ms) "
                         "VALUES (?, ?, ?, 'in_progress', ?)", (account_id, key, req_hash, now_ms))
            return None
        if row["request_hash"] != req_hash:
            raise KeyConflict("idempotency_key_reused", "This key was already used with different parameters.")
        if row["state"] == "done":
            return SavedResponse(row["status_code"], json.loads(row["body"]))
        if now_ms - row["created_ms"] < CLAIM_TIMEOUT.total_seconds() * 1000:
            raise KeyConflict("request_in_progress", "A request with this key is still being processed. Retry later.")
        # The server that claimed the key died part-way through. Take it over.
        conn.execute("UPDATE idempotency_keys SET created_ms = ? WHERE account_id = ? AND key = ?",
                     (now_ms, account_id, key))
        return None


def save_response(conn, account_id: str, key: str, status_code: int, body: dict) -> None:
    """Record the final response. Call inside the transaction that stores the result."""
    conn.execute("UPDATE idempotency_keys SET state = 'done', status_code = ?, body = ? "
                 "WHERE account_id = ? AND key = ?", (status_code, json.dumps(body), account_id, key))


def release(conn, account_id: str, key: str) -> None:
    """Give the key back after a failure the client may retry."""
    with transaction(conn):
        conn.execute("DELETE FROM idempotency_keys WHERE account_id = ? AND key = ? AND state = 'in_progress'",
                     (account_id, key))
