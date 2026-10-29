"""The vendor's acceptance check: GHZ-4 fidelity from populations and a parity scan. Spec: fidelity >= 0.80.
Runs in the vendor's slot (not charged to your shot budget).

    python check_ghz.py
"""
import cmath
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qc import backend  # noqa: E402
from qc.run import run  # noqa: E402

backend.FREE = True
GHZ = [("h", 0), ("cx", 0, 1), ("cx", 1, 2), ("cx", 2, 3)]
pop = run(GHZ, 20000)
p_ends = pop.get("0000", 0) + pop.get("1111", 0)
z = 0
for k in range(8):
    phi = k * math.pi / 16
    analysis = [g for q in range(4) for g in (("rz", q, -phi), ("h", q))]
    p = run(GHZ + analysis, 5000)
    parity = sum(v * (-1) ** b.count("1") for b, v in p.items())
    z += parity * cmath.exp(-4j * phi) / 4
contrast, offset = abs(z), cmath.phase(z)
fid = p_ends / 2 + contrast / 2
print(f"P(0000) + P(1111) = {p_ends:.3f}")
print(f"parity contrast   = {contrast:.3f}   (phase {offset:+.2f} rad)")
print(f"GHZ-4 fidelity    = {fid:.3f}   {'ok' if fid >= 0.80 else 'FAIL'} (spec >= 0.80)")
sys.exit(0 if fid >= 0.80 else 1)
