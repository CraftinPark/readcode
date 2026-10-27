"""Clip a probe onto the running board. You have a budget of 3 probes per attempt (they cost line downtime).

    python probe.py --list
    python probe.py SIGNAL --at SECONDS [--window SECONDS]

Each probe records one signal for a window around a moment of the last long job (10 ms samples, every 5th shown).
"""
import argparse
import os

from _sim import plant
from firmware.drive import Drive

SIGNALS = ["motor_current_a", "temperature_c", "enc_raw", "pos_estimate", "pwm"]
BUDGET = 3
USED = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".probes_used")

ap = argparse.ArgumentParser()
ap.add_argument("signal", nargs="?")
ap.add_argument("--at", type=float, default=0.0)
ap.add_argument("--window", type=float, default=0.5)
ap.add_argument("--list", action="store_true")
a = ap.parse_args()
if a.list or not a.signal:
    print("signals:", ", ".join(SIGNALS))
    raise SystemExit
if a.signal not in SIGNALS:
    raise SystemExit(f"no test point for {a.signal}; try --list")
used = int(open(USED).read()) if os.path.exists(USED) else 0
if used >= BUDGET:
    raise SystemExit(f"probe budget spent ({BUDGET}). Delete .probes_used only to start a new attempt.")
open(USED, "w").write(str(used + 1))

log = plant.run(Drive)
lo, hi = a.at - a.window / 2, a.at + a.window / 2
for i, t in enumerate(log["t"]):
    if lo <= t <= hi and i % 5 == 0:
        print(f"{t:6.2f}s  {a.signal} = {log[a.signal][i]}")
print(f"\nprobes used: {used + 1} of {BUDGET}")
