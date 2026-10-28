"""Every call to Textly is logged in `sends` (support and finance read it). data/sends.jsonl.gz is an export."""
import json


def record(conn, now, kind, to_number, status, headers):
    conn.execute("insert into sends (ts, kind, to_number, status, headers) values (?, ?, ?, ?, ?)",
                 (now, kind, to_number, status, json.dumps(headers) if headers else None))


def note_quota(conn, now, headers):
    """Textly's X-RateLimit-Remaining: what's left of today's (UTC) account quota, shared by every message."""
    if headers and "X-RateLimit-Remaining" in headers:
        conn.execute("insert or replace into quota values (1, ?, ?)", (int(headers["X-RateLimit-Remaining"]), now))
