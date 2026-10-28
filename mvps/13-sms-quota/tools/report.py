"""Daily summary of data/sends.jsonl.gz (every call we made to Textly in the last 6 weeks).

    python tools/report.py
"""
import collections
import datetime as dt
import gzip
import json
import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sends.jsonl.gz")
days = collections.defaultdict(collections.Counter)
for line in gzip.open(path, "rt", encoding="utf-8"):
    r = json.loads(line)
    day = dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).strftime("%a %d %b")
    days[(r["ts"] // 86400, day)][(r["kind"], r["status"])] += 1
print(f"{'day (UTC)':<11} {'otp sent':>9} {'otp timeout':>12} {'campaign sent':>14} {'campaign timeout':>17}")
for (_, day), c in sorted(days.items()):
    print(f"{day:<11} {c['otp', 'sent']:>9} {c['otp', 'timeout']:>12} {c['campaign', 'sent']:>14} "
          f"{c['campaign', 'timeout']:>17}")
