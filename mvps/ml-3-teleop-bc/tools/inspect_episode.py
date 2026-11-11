"""Print what the pipeline sees for one episode.

    python tools/inspect_episode.py 12            # episode id
    python tools/inspect_episode.py 12 --frames 40

Shows each stream's sample count, rate, span and largest gap, the quality
verdict, and the first aligned frames (obs and action columns side by side).
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ACT_FIELDS, OBS_FIELDS, DataConfig  # noqa: E402
from pipeline.episodes import Rejected, align_episode  # noqa: E402
from pipeline.io import load_episode  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", type=int)
    ap.add_argument("--data", default=DataConfig.root)
    ap.add_argument("--frames", type=int, default=15)
    a = ap.parse_args(argv)
    cfg = DataConfig(root=a.data)
    ep = load_episode(os.path.join(a.data, f"ep_{a.episode:04d}"))
    print(f"episode {ep.episode_id}  operator {ep.meta['operator']}  rig {ep.meta['rig_version']}  "
          f"bin {np.round(ep.bin_xy, 3).tolist()}")
    print(f"{'stream':9s} {'n':>6s} {'rate Hz':>8s} {'t first':>8s} {'t last':>8s} {'max gap':>8s}")
    for name, s in ep.streams.items():
        print(f"{name:9s} {len(s):6d} {s.rate_hz():8.1f} {s.t[0]:8.3f} {s.t[-1]:8.3f} {s.max_gap():8.3f}")
    try:
        fr = align_episode(ep, cfg)
    except Rejected as r:
        print(f"rejected: {r.reason}")
        return 0
    print(f"aligned: {len(fr)} frames at {cfg.policy_hz:g} Hz, {int((~fr.usable).sum())} unusable")
    cols = list(OBS_FIELDS) + list(ACT_FIELDS)
    print("    t  " + " ".join(f"{c:>8s}" for c in cols))
    for i in range(min(a.frames, len(fr))):
        row = np.concatenate([fr.obs[i], fr.act[i]])
        print(f"{fr.t[i]:6.2f} " + " ".join(f"{v:8.3f}" for v in row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
