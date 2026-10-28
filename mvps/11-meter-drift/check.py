"""The on-call check for the ticket: replays MTR-0115's packets for week 8 (Mon 19 - Sun 25 Oct 2026) exactly
as they arrived, then checks every 15-minute interval of the week was billed.

    python check.py
"""
import gzip
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from meterbill import billing, db, ingest  # noqa: E402

METER, START, END = "MTR-0115", 1792368000, 1792972800
conn = sqlite3.connect(":memory:")
db.init(conn)
for line in gzip.open(os.path.join(HERE, "data", "packets.jsonl.gz"), "rt", encoding="utf-8"):
    d = json.loads(line)
    if d["packet"]["meter"] == METER:
        ingest.receive(conn, d["packet"], d["received_at"])
n = conn.execute("select count(*) from readings where meter = ? and ts >= ? and ts < ?", (METER, START, END)).fetchone()[0]
print(f"{METER} week 8: {n}/672 intervals stored, bill {billing.bill(conn, METER, START, END) / 100:.2f}")
sys.exit(0 if n == 672 else 1)
