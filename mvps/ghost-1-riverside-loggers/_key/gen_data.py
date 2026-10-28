"""Regenerates data/ from the world in sim.py: everything the ingest gateway received before Wed 28 Oct 2026,
the meter list, and the water board's weekly zone inlet readings.

    python _key/gen_data.py
"""
import gzip
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim  # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "data")


def main():
    ms, packets, truth, bulk = sim.run()
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "meters.csv"), "w", newline="") as f:
        f.write("meter,zone,logger,hw,since\n")
        for m in ms:
            since = "2026-10-05" if m.model == "BX" else "2019-0%d-1%d" % (3 + len(m.id) % 5, int(m.id[-1]))
            f.write(f"{m.id},{m.zone},{m.model},{m.hw.upper() if m.model == 'BX' else m.hw},{since}\n")
    with gzip.open(os.path.join(DATA, "packets.jsonl.gz"), "wt", encoding="utf-8", compresslevel=9) as f:
        for rx, p in packets:
            if rx < sim.T_DATA:
                f.write(json.dumps(p, separators=(",", ":")) + "\n")
    rng = random.Random(77)
    with open(os.path.join(DATA, "bulk.csv"), "w", newline="") as f:
        f.write("zone,week_from,week_to,inlet_m3\n")
        wk = sim.T0
        while wk + 7 * sim.DAY <= sim.T_DATA:
            for z in ("W", "E"):
                used = sum(bulk.get((z, h), 0) for h in range(wk, wk + 7 * sim.DAY, sim.H))
                inlet = used * (1 + rng.uniform(0.004, 0.009)) / 1000
                a = sim._dt.datetime.fromtimestamp(wk, sim._dt.timezone.utc).date()
                b = sim._dt.datetime.fromtimestamp(wk + 7 * sim.DAY, sim._dt.timezone.utc).date()
                f.write(f"{z},{a},{b},{inlet:.2f}\n")
            wk += 7 * sim.DAY
    print("wrote", DATA)


if __name__ == "__main__":
    main()
