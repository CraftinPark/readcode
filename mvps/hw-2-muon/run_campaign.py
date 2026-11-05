"""Runs one day of the zenith-angle campaign on the telescope with board/config.json and muon/analysis.py:
24 one-hour runs, cycling 0, 15, 30, 45, 60, 75 degrees. Fits I0 * cos^n. It books the telescope for a
whole day, so you get 3 campaign days per attempt (separate from the 10 hours of bench time).

Pass = n within 1.9-2.1 and the vertical rate I0 within 3% of last year's 3.79 muons/s (same paddles, same site).

    python run_campaign.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _sim import telescope  # noqa: E402
from muon.analysis import muon_rate  # noqa: E402
from muon.fit import fit_cos_n, per_angle  # noqa: E402

config = json.load(open(os.path.join(HERE, "board", "config.json")))
points, day = telescope.campaign(config, muon_rate, per_angle, HERE)
print(f"campaign day {day} of {telescope.CAMPAIGN_DAYS}")
for ang, r, s in points:
    print(f"{ang:3d} deg: {r:7.3f} +- {s:.3f} muons/s")
i0, n = fit_cos_n(points)
ok = 1.9 <= n <= 2.1 and abs(i0 / 3.79 - 1) <= 0.03
print(f"fit: I0 = {i0:.3f} muons/s ({i0 / 3.79 - 1:+.1%} vs last year), n = {n:.3f}  -> {'ok' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
