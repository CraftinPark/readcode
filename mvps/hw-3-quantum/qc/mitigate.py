"""Readout error mitigation: undo each qubit's assignment matrix (from qc/calib.json) on the measured
distribution, clip negatives, renormalise."""
import json
import os

CALIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib.json")


def _bits(i):
    return "".join("1" if (i >> k) & 1 else "0" for k in range(4))


def mitigate(probs, calib=None):
    """probs: {bitstring: measured probability}. Returns {bitstring: estimated true probability}."""
    cal = calib or json.load(open(CALIB))
    p = [probs.get(_bits(i), 0.0) for i in range(16)]
    for q in range(4):
        r0, r1 = cal["readout"][q]["p1_given_0"], cal["readout"][q]["p0_given_1"]
        det = 1 - r0 - r1
        step = 1 << q
        for i in range(16):
            if not i & step:
                j = i | step
                m0, m1 = p[i], p[j]
                p[i] = ((1 - r1) * m0 - r1 * m1) / det
                p[j] = (-r0 * m0 + (1 - r0) * m1) / det
    p = [max(x, 0.0) for x in p]
    s = sum(p)
    return {_bits(i): x / s for i, x in enumerate(p)}
