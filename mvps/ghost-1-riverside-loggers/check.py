"""The on-call check for the ticket: ingests everything in data/ into a fresh database, then asks billing for
each day from Mon 5 Oct to Tue 27 Oct 2026 for every meter. Every meter must have water on every day.

    python check.py
"""
import gzip
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wfl import bx, db, qn  # noqa: E402

DAY, START, END = 86400, 1791158400, 1793145600
conn = sqlite3.connect(":memory:")
db.init(conn)
rejected = 0
for line in gzip.open(os.path.join(HERE, "data", "packets.jsonl.gz"), "rt", encoding="utf-8"):
    try:
        qn.receive(conn, json.loads(line))
    except ValueError:
        rejected += 1
meters = [r[0] for r in conn.execute("select distinct m from mt order by m")]
empty = [(m, d) for m in meters for d in range(START, END, DAY) if bx.bill(conn, m, d, d + DAY)["litres"] <= 0]
for m in sorted({m for m, _ in empty}):
    print(f"{m}: {sum(1 for x, _ in empty if x == m)} of {(END - START) // DAY} days with no water billed")
print(f"{rejected} packets rejected; {len(meters) - len({m for m, _ in empty})}/{len(meters)} meters billed every day")
sys.exit(0 if not empty and not rejected else 1)
