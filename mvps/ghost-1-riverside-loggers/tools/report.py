"""Prints what the billing run would send: litres and euros per meter per calendar month, from data/.

    python tools/report.py [meter ...]
"""
import datetime
import gzip
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from wfl import bx, db, qn  # noqa: E402

MONTHS = ["2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01"]


def ts(s):
    return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp())


conn = sqlite3.connect(":memory:")
db.init(conn)
bad = 0
for line in gzip.open(os.path.join(ROOT, "data", "packets.jsonl.gz"), "rt", encoding="utf-8"):
    try:
        qn.receive(conn, json.loads(line))
    except ValueError:
        bad += 1
want = sys.argv[1:] or [r[0] for r in conn.execute("select m from mt order by m")]
print("meter   " + "".join(f"{a[:7]:>18}" for a in MONTHS[:-1]))
for m in want:
    row = [bx.bill(conn, m, ts(a), ts(b)) for a, b in zip(MONTHS, MONTHS[1:])]
    print(f"{m:8}" + "".join(f"{r['litres']:>9} L {r['eur']:>6.2f}" for r in row))
print(f"(October is up to Tue 27 Oct; {bad} packets rejected)")
