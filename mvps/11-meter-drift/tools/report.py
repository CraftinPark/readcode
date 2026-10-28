"""Loads every packet in data/ through ingest.receive (in arrival order), then prints each meter's weekly
bill and how many packets were rejected.

    python tools/report.py
"""
import gzip
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from meterbill import billing, db, ingest  # noqa: E402

T0, WEEK = 1788134400, 7 * 86400  # Monday 31 Aug 2026, start of week 1
conn = sqlite3.connect(":memory:")
db.init(conn)
for line in gzip.open(os.path.join(ROOT, "data", "packets.jsonl.gz"), "rt", encoding="utf-8"):
    d = json.loads(line)
    ingest.receive(conn, d["packet"], d["received_at"])
meters = [m for (m,) in conn.execute("select distinct meter from readings order by meter")]
print("meter     " + " ".join(f"   wk{w}" for w in range(1, 9)) + "  rejected")
for m in meters:
    bills = [billing.bill(conn, m, T0 + (w - 1) * WEEK, T0 + w * WEEK) / 100 for w in range(1, 9)]
    rej = conn.execute("select count(*) from rejected where meter = ?", (m,)).fetchone()[0]
    print(f"{m:<9} " + " ".join(f"{b:6.2f}" for b in bills) + f"  {rej:8d}")
