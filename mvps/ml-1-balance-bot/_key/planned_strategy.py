"""Is ML-1 solvable by a planned approach? A 60-episode measurement plan, written as code, run many times against
the real robot model (fresh noise and a fresh budget each trial) and graded by the 1000-episode replay.

The plan reads only what robot.py shows the player (episode outcomes, achieved loop rate, overrun %, 50 Hz
telemetry of pitch_est / wheel_pos / torque_cmd) and uses textbook reasoning, not the hidden constants:
  1. The shipped config shakes itself to a driver trip within a second: an oscillation the delay-free sim
     can't have, so the real loop has delay. A faster loop cuts it, up to what the computer sustains. Two
     single-episode runs at 300 and 400 Hz give two overrun percentages; fit a shifted-exponential compute
     time to them and pick the fastest rate that overruns at most 3% of ticks.
  2. At that rate, sweep action smoothing (0.3, 0.45, 0.6, 0.75; 3 episodes each, tilt tau 1.0). Too little
     smoothing: a jittery tilt estimate and wandering (left the mat). Too much: the lag brings the shaking
     back (driver trips). Keep the best by outcomes, ties broken by lower pitch_est jitter.
  3. Episodes that survive show a steady wheel offset at the end; with a constant gyro bias the offset scales
     with the tilt filter's time constant. Scale tau so the largest offset seen would be about 0.25 m
     (clipped to 0.6-1.0 s).
  4. Spend the rest in blocks of 6 on the chosen config; on a failure, step the knob that the failure points
     to (trip: less smoothing; left with a steady offset: shorter tau; left with jitter: more smoothing).

    python _key/planned_strategy.py --trials 40
"""
import argparse
import json
import math
import os
import secrets
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)


class Robot:
    """What robot.py gives the player, in-process: outcomes, loop stats, telemetry."""

    def __init__(self, budget=60):
        self.left = budget
        self.log = []

    def __call__(self, cfg, n):
        from _sim import robot
        from deploy.runner import Runner
        n = min(n, self.left)
        if n <= 0:
            return None
        self.left -= n
        r = robot.run(Runner, n, secrets.randbits(63), cfg, record=True)
        eps = []
        for i in range(n):
            rows = np.array([(t, pe[i], x[i], u[i]) for (t, pe, g, x, u, alive) in r["tele"] if alive[i]])
            eps.append(dict(outcome=int(r["outcome"][i]), t=rows[:, 0], pitch=rows[:, 1], x=rows[:, 2],
                            u=rows[:, 3]))
        res = dict(cfg=dict(cfg), eps=eps, ok=sum(e["outcome"] == 0 for e in eps),
                   overrun=r["overruns"].sum() / max(r["ticks"].sum(), 1))
        self.log.append(res)
        return res


def jitter(e):
    return float(np.std(np.diff(e["pitch"]))) if len(e["pitch"]) > 3 else 1.0


def steady_offset(e):
    if e["outcome"] != 0:
        return None
    return float(np.median(e["x"][e["t"] > 15]))


def score(res):
    trips = sum(e["outcome"] == 3 for e in res["eps"])
    return (res["ok"] / len(res["eps"]), -trips, -np.mean([jitter(e) for e in res["eps"]]))


def strategy(bot):
    tau, base = 1.0, dict(tilt_filter_tau_s=1.0, action_smoothing=0.5)
    # 1. fastest sustainable loop
    p = {}
    for hz in (300, 400):
        p[hz] = max(bot(dict(base, control_hz=hz), 1)["overrun"], 1e-3)
    T3, T4 = 1 / 300, 1 / 400
    m = (T3 - T4) / max(math.log(p[400] / p[300]), 1e-3)  # P(c > T) = exp(-(T - c0) / m)
    c0 = T3 + m * math.log(p[300])
    hz = int(min(400, max(150, 1 / (c0 + m * math.log(1 / 0.03))))) // 5 * 5
    # 2. smoothing sweep
    sweep = []
    for a in (0.3, 0.45, 0.6, 0.75):
        sweep.append(bot(dict(control_hz=hz, tilt_filter_tau_s=tau, action_smoothing=a), 3))
    best = max(sweep, key=score)
    a = best["cfg"]["action_smoothing"]
    # 3. tilt filter from steady offsets of survivors at tau 1.0
    offs = [abs(o) for r in sweep for e in r["eps"] if (o := steady_offset(e)) is not None]
    if offs:
        k = len(offs)
        maxoff = max(offs) * (k + 1) / k
        tau = float(np.clip(round(tau * 0.25 / maxoff, 2), 0.6, 1.0))
    cfg = dict(control_hz=hz, tilt_filter_tau_s=tau, action_smoothing=a)
    # 4. verify and adjust
    record = {}
    while bot.left > 0:
        r = bot(cfg, 6)
        key = json.dumps(cfg, sort_keys=True)
        ok, n = record.get(key, (0, 0))
        record[key] = (ok + r["ok"], n + len(r["eps"]))
        fails = [e for e in r["eps"] if e["outcome"] != 0]
        if not fails:
            continue
        trips = sum(e["outcome"] == 3 for e in fails)
        lefts = [e for e in fails if e["outcome"] == 2]
        new = dict(cfg)
        if trips >= len(lefts):
            new["action_smoothing"] = round(max(0.0, cfg["action_smoothing"] - 0.05), 2)
        else:
            jit_fail = np.mean([jitter(e) for e in lefts])
            jit_ok = np.mean([jitter(e) for e in r["eps"] if e["outcome"] == 0] or [jit_fail])
            if jit_fail > 1.3 * jit_ok:
                new["action_smoothing"] = round(min(0.9, cfg["action_smoothing"] + 0.05), 2)
            else:
                new["tilt_filter_tau_s"] = round(max(0.4, cfg["tilt_filter_tau_s"] - 0.1), 2)
        cfg = new
    # final: the config with the best record (at least 6 episodes), else the last one
    tried = [(ok / n, n, json.loads(k)) for k, (ok, n) in record.items() if n >= 6]
    if tried:
        cfg = max(tried, key=lambda x: (x[0], x[1]))[2]
    return cfg


def one(_):
    import warnings
    warnings.filterwarnings("ignore")
    bot = Robot()
    return strategy(bot)


if __name__ == "__main__":
    import replay
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=40)
    a = ap.parse_args()
    with Pool(12) as pool:
        finals = pool.map(one, range(a.trials))
    cache, wins = {}, 0
    for i, cfg in enumerate(finals):
        k = json.dumps(cfg, sort_keys=True)
        if k not in cache:
            cache[k] = replay.evaluate(cfg=cfg, procs=12)
        res = cache[k]
        rate = res["ok"] / res["n"]
        wins += rate >= replay.PASS
        print(f"trial {i + 1:2d}: {cfg}  replay {100 * rate:.1f}%  {'PASS' if rate >= replay.PASS else 'fail'}",
              flush=True)
    print(f"solved {wins} of {a.trials}")
