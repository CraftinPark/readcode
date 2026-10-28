"""Every call to Textly is logged in `sends` (support and finance read it). data/sends.jsonl.gz is an export."""
import json


def record(conn, now, kind, to_number, status, headers):
    conn.execute("insert into sends (ts, kind, to_number, status, headers) values (?, ?, ?, ?, ?)",
                 (now, kind, to_number, status, json.dumps(headers) if headers else None))
