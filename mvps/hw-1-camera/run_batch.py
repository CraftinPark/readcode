"""Measures yesterday's batch with the station code and compares with the lab's spectroradiometer.

    python run_batch.py
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _sim import camera  # noqa: E402
from station.measure import measure  # noqa: E402

bad = 0
for row in csv.DictReader(open(os.path.join(HERE, "data", "batch_1027.csv"))):
    got = measure(camera.mount(row["led"]))
    want = float(row["lab_mcd"])
    err = (got - want) / want
    bad += abs(err) > 0.03
    print(f"{row['led']}: station {got:10.2f} mcd   lab {want:8.2f} mcd   {err:+7.1%}{'' if abs(err) <= 0.03 else '  REJECT'}")
print(f"{12 - bad}/12 within 3%")
sys.exit(1 if bad else 0)
