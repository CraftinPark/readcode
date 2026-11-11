"""The acceptance run: 1000 fresh episodes on the robot with the player's deploy/config.json. The deploy code and
policy always come from this folder; the replay also reports if the player changed them (against the rules).
Pass = at least 97% of episodes ok.

    python _key/replay.py [PLAYER_DIR]        # default: this problem's root
"""
import importlib
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PASS = 0.97
N_EPISODES = 1000
CHUNK = 50
SEED = 914_000


def _chunk(args):
    cfg, seed, n = args
    sys.path.insert(0, ROOT)
    from _sim import robot
    runner_mod = importlib.import_module("deploy.runner")
    r = robot.run(runner_mod.Runner, n, seed, cfg)
    return r["outcome"].tolist()


def valid(cfg):
    return (set(cfg) == {"control_hz", "tilt_filter_tau_s", "action_smoothing"}
            and isinstance(cfg["control_hz"], int) and 50 <= cfg["control_hz"] <= 1000
            and 0.05 <= cfg["tilt_filter_tau_s"] <= 5 and 0 <= cfg["action_smoothing"] <= 0.95)


def changed_files(player_dir):
    out = []
    for rel in ("deploy/runner.py", "policy/net.py", "policy/policy.pt"):
        a, b = os.path.join(ROOT, rel), os.path.join(player_dir, rel)
        if not os.path.exists(b) or open(a, "rb").read() != open(b, "rb").read():
            out.append(rel)
    return out


def evaluate(player_dir=ROOT, cfg=None, n=N_EPISODES, seed=SEED, procs=10):
    if cfg is None:
        cfg = json.load(open(os.path.join(player_dir, "deploy", "config.json")))
    if not valid(cfg):
        return dict(cfg=cfg, n=n, ok=0, fell=0, left=0, trip=0, invalid=True)
    jobs = [(cfg, seed + i, CHUNK) for i in range(n // CHUNK)]
    with Pool(procs) as pool:
        out = np.concatenate([np.array(o) for o in pool.map(_chunk, jobs)])
    return dict(cfg=cfg, n=len(out), ok=int((out == 0).sum()), fell=int((out == 1).sum()),
                left=int((out == 2).sum()), trip=int((out == 3).sum()))


def report(res):
    rate = res["ok"] / res["n"]
    verdict = "PASS" if rate >= PASS else "FAIL"
    return (f"{verdict}  {res['ok']}/{res['n']} ok ({100 * rate:.1f}%), driver trips {res['trip']}, "
            f"left the mat {res['left']}, fell {res['fell']}   config {res['cfg']}")


if __name__ == "__main__":
    d = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    ch = changed_files(d)
    if ch:
        print("note: player changed", ", ".join(ch), "(graded with the original code)")
    print(report(evaluate(d)))
