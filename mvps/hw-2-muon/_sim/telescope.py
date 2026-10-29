"""The physical world (key side; the player gets only a compiled .pyc without docstrings). A two-paddle muon
telescope (A on top, B 1 m below) in an unheated hut, read by a CB-2 coincidence board.

The hidden truth, which a player can only learn by running the telescope:
- B's signal arrives 20.5 ns after A's for the same muon (new PMT transit time + the longer cable), jitter 3 ns.
- B's discriminator is a different model: its output pulse is 45 ns whatever width_b says. So the accidental
  window is width_a + 45 ns, not width_a + width_b.
- Both discriminators hold off for 1.5 us after each pulse (non-paralyzable). Harmless on A (1.8 kHz), but B is
  a noisy new PMT whose dark rate doubles every 12 C: 30 kHz at 12 C today, ~6 kHz at -15 C, ~85 kHz at 30 C.
  A muon is lost when B is in hold-off, so the muon rate drops 4% today and 11% on a hot day.
- Muons through both paddles: 4.2 Hz * cos^2(zenith), times paddle efficiencies 0.96 and 0.94.
- Coincidence = the two output pulses overlap. Accidentals = mA * mB * (wA + wB), with measured singles.
"""
import base64
import json
import math
import random

_P = json.loads(base64.b64decode(
    b"eyJkZWx0YSI6IDIwLjUsICJqaXQiOiAzLjAsICJ3YiI6IDQ1LjAsICJob2xkIjogMS41ZS0wNiwgImEwIjogMTgwMC4wLCAiYjAiOiAzMDAwMC4wLCAidGRvdWJsZSI6IDEyLjAsICJtdTAiOiA0LjIsICJlYSI6IDAuOTYsICJlYiI6IDAuOTR9"))
TODAY_C = 12.0


def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _poisson(rng, mean):
    if mean < 50:
        k, p, L = 0, 1.0, math.exp(-mean)
        while True:
            p *= rng.random()
            if p <= L:
                return k
            k += 1
    return max(0, int(round(rng.gauss(mean, math.sqrt(mean)))))


def rates(config, angle_deg, temp_c, source_b=False):
    """Expected (singles A, singles B, coincidences) per second, as counted by the board."""
    th = math.radians(angle_deg)
    mu = _P["mu0"] * math.cos(th) ** 2
    nA = _P["a0"] * 2 ** ((temp_c - TODAY_C) / 20.0) + mu * 1.6
    nB = _P["b0"] * 2 ** ((temp_c - TODAY_C) / _P["tdouble"]) + mu * 1.6 + (60000.0 if source_b else 0.0)
    mA = nA / (1 + nA * _P["hold"])
    mB = nB / (1 + nB * _P["hold"])
    wA = float(config["width_a_ns"])
    wB = _P["wb"]
    d = _P["delta"] + config["delay_b_ns"] - config["delay_a_ns"]   # B start minus A start, ns
    eff = _phi((wA - d) / _P["jit"]) - _phi((-wB - d) / _P["jit"])
    live = (1 - mA * _P["hold"]) * (1 - mB * _P["hold"])
    true = mu * _P["ea"] * _P["eb"] * eff * live
    acc = mA * mB * (wA + wB) * 1e-9
    return mA, mB, true + acc


def run(config, angle_deg, seconds, temp_c=TODAY_C, source_b=False, seed=None):
    """One run: counts {A, B, AB, seconds, hut_c} as the board reports them."""
    for k in ("delay_a_ns", "delay_b_ns", "width_a_ns", "width_b_ns"):
        if not 0 <= int(config[k]) <= 255:
            raise ValueError(f"{k} must be 0..255 ns")
    if int(config["width_a_ns"]) < 5 or int(config["width_b_ns"]) < 5:
        raise ValueError("widths must be at least 5 ns")
    rng = random.Random(seed)
    mA, mB, ab = rates(config, angle_deg, temp_c, source_b)
    return {"A": _poisson(rng, mA * seconds), "B": _poisson(rng, mB * seconds), "AB": _poisson(rng, ab * seconds),
            "seconds": seconds, "angle_deg": angle_deg, "hut_c": round(temp_c, 1)}


def vertical_truth():
    """Muons per second through both paddles, vertical, as last year's analysis reported it."""
    return _P["mu0"] * _P["ea"] * _P["eb"]
