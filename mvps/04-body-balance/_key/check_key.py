"""Shipped body is sick; 'just buy more heart' is not enough; the reference balance clears the bar (80)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import body  # noqa: E402

TARGET = 80
cases = [
    ("shipped body.json", body.load(os.path.join(HERE, "..", "body.json")), False),
    ("more heart only", dict(body.load(os.path.join(HERE, "..", "body.json")), heart_capacity=300), False),
    ("reference", body.load(os.path.join(HERE, "reference.json")), True),
]
bad = 0
for name, cfg, should_pass in cases:
    r = body.simulate(cfg)
    passed = r["score"] >= TARGET
    print(f"{name}: score {r['score']} health {r['health']} cost {r['cost_vs_budget']} -> {'healthy' if passed else 'sick'}")
    bad += passed != should_pass
sys.exit(1 if bad else 0)
