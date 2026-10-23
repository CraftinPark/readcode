"""Webhook events.

record() writes an event in the same transaction as the change it describes,
so an event exists if and only if the change was committed (the outbox
pattern). deliver_due() runs in a background worker: it sends due events to
the account's endpoint and retries failures with backoff for up to 3 days.
"""
import hashlib
import hmac
import json
import sqlite3
from datetime import timedelta
from typing import Callable, Optional

from .db import new_id

MAX_AGE = timedelta(days=3)
MAX_BACKOFF = timedelta(hours=1)

# http_post(url, body, headers) -> HTTP status code, or None if the request
# failed before a response arrived (DNS, connection refused, timeout).
HttpPost = Callable[[str, bytes, dict], Optional[int]]


def record(conn: sqlite3.Connection, account_id: str, event_type: str, data: dict, now_ms: int) -> str:
    event_id = new_id("evt")
    payload = json.dumps({"id": event_id, "type": event_type, "created": now_ms // 1000, "data": data})
    conn.execute("INSERT INTO events (id, account_id, type, payload, created_ms, next_attempt_ms) "
                 "VALUES (?, ?, ?, ?, ?, ?)", (event_id, account_id, event_type, payload, now_ms, now_ms))
    return event_id


def sign(secret: str, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={mac.hexdigest()}"


def backoff_ms(attempts: int) -> int:
    return int(min(timedelta(seconds=30 * 2 ** attempts), MAX_BACKOFF).total_seconds() * 1000)


def deliver_due(conn: sqlite3.Connection, http_post: HttpPost, now_ms: int, batch: int = 100) -> int:
    """Send events whose next attempt is due. Returns how many were delivered."""
    due = conn.execute("SELECT id, account_id, type, payload, created_ms, attempts FROM events "
                       "WHERE delivered_ms IS NULL AND failed = 0 AND next_attempt_ms <= ? "
                       "ORDER BY created_ms LIMIT ?", (now_ms, batch)).fetchall()
    endpoints: dict[str, Optional[sqlite3.Row]] = {}
    delivered = 0
    for ev in due:
        cache_key = ev["type"]
        if cache_key not in endpoints:
            endpoints[cache_key] = conn.execute(
                "SELECT url, secret FROM webhook_endpoints WHERE account_id = ?", (ev["account_id"],)).fetchone()
        endpoint = endpoints[cache_key]
        if endpoint is None:
            # No endpoint configured: nothing to send, but keep the event for the dashboard.
            conn.execute("UPDATE events SET delivered_ms = ? WHERE id = ?", (now_ms, ev["id"]))
            continue

        body = ev["payload"].encode()
        headers = {"Content-Type": "application/json", "Signature": sign(endpoint["secret"], now_ms // 1000, body)}
        status = http_post(endpoint["url"], body, headers)

        if status is not None and status < 500:
            conn.execute("UPDATE events SET delivered_ms = ?, attempts = attempts + 1 WHERE id = ?", (now_ms, ev["id"]))
            delivered += 1
        elif now_ms - ev["created_ms"] >= MAX_AGE.total_seconds() * 1000:
            conn.execute("UPDATE events SET failed = 1, attempts = attempts + 1 WHERE id = ?", (ev["id"],))
        else:
            conn.execute("UPDATE events SET attempts = attempts + 1, next_attempt_ms = ? WHERE id = ?",
                         (now_ms + backoff_ms(ev["attempts"]), ev["id"]))
    return delivered
