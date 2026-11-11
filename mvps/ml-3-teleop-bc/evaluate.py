"""Closed-loop evaluation on the bench twin.

    python evaluate.py [--ckpt runs/latest.pt] [--episodes 50] [-v]

Each episode starts with the arm at rest, the block and the bin at new random
places, and runs the policy at 10 Hz until the block is released inside the
bin or the time limit passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

import numpy as np
import torch

from config import EvalConfig
from policy.runner import PolicyRunner
from sim.env import CellConfig, PickPlaceCell

POLICY_DT = 0.1


@dataclass
class Rollout:
    seed: int
    success: bool
    first_try: bool
    seconds: float
    missed_grasps: int
    drops: int


def rollout(runner: PolicyRunner, seed: int, ecfg: EvalConfig, cell_cfg: CellConfig | None = None) -> Rollout:
    cell = PickPlaceCell(cell_cfg)
    s = cell.reset(seed)
    runner.reset()
    steps = int(round(ecfg.time_limit_s / POLICY_DT))
    for _ in range(steps):
        ee, jaw = cell.read_follower()
        block, detected = cell.latest_frame()
        target, grip = runner.act(ee, jaw, block, detected, s.bin)
        cell.run(target, grip, POLICY_DT)
        if s.done:
            break
    return Rollout(seed, s.success, s.success and s.missed_grasps == 0 and s.drops == 0,
                   round(s.t, 2), s.missed_grasps, s.drops)


def run_eval(runner: PolicyRunner, ecfg: EvalConfig, verbose: bool = False) -> dict:
    results = []
    for i in range(ecfg.episodes):
        r = rollout(runner, ecfg.seed + i, ecfg)
        results.append(r)
        if verbose:
            tag = "ok  " if r.success else "FAIL"
            print(f"  {tag} seed {r.seed}  {r.seconds:5.1f}s  missed grasps {r.missed_grasps}  drops {r.drops}")
    ok = [r for r in results if r.success]
    return {
        "episodes": len(results),
        "success_rate": len(ok) / len(results),
        "first_try_rate": sum(r.first_try for r in results) / len(results),
        "mean_time_success_s": float(np.mean([r.seconds for r in ok])) if ok else None,
        "missed_grasps_per_episode": float(np.mean([r.missed_grasps for r in results])),
        "drops_per_episode": float(np.mean([r.drops for r in results])),
        "timeouts": sum(1 for r in results if not r.success),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="runs/latest.pt")
    ap.add_argument("--episodes", type=int, default=EvalConfig.episodes)
    ap.add_argument("--seed", type=int, default=EvalConfig.seed)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    torch.set_num_threads(1)
    ecfg = EvalConfig(episodes=a.episodes, seed=a.seed)
    runner = PolicyRunner.load(a.ckpt, ecfg)
    summary = run_eval(runner, ecfg, verbose=a.verbose)
    if a.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"success {summary['success_rate']:.0%} over {summary['episodes']} episodes"
              f" | first try {summary['first_try_rate']:.0%}"
              f" | mean time to success {summary['mean_time_success_s'] or float('nan'):.1f}s"
              f" | missed grasps/ep {summary['missed_grasps_per_episode']:.2f}"
              f" | drops/ep {summary['drops_per_episode']:.2f}"
              f" | failures {summary['timeouts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
