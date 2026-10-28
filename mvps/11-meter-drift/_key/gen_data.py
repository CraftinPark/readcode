"""Writes data/packets.jsonl.gz (weeks 1-8 as received, in arrival order) and data/meters.csv.

    python _key/gen_data.py
"""
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "data")
meters, deliveries = sim.world(8)
cut = sim.week_start(9) + 600  # export ran at 00:10 Monday
os.makedirs(OUT, exist_ok=True)
n = 0
with gzip.open(os.path.join(OUT, "packets.jsonl.gz"), "wt", encoding="utf-8", newline="\n") as f:
    for received, packet in deliveries:
        if received < cut:
            f.write(json.dumps({"received_at": received, "packet": packet}, separators=(",", ":")) + "\n")
            n += 1
with open(os.path.join(OUT, "meters.csv"), "w", encoding="utf-8", newline="\n") as f:
    f.write("meter,district,installed,customer_plan\n")
    for m in meters:
        f.write(f"{m.id},{m.district},2026-08-21,{'tou-evening' if m.scale > 0.7 else 'tou-evening-lite'}\n")
print(f"{n} packets")
