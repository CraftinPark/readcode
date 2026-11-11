"""Same seed twice -> same numbers? (it should, single thread CPU)

    python scripts/check_determinism.py --steps 8192
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armrl.config import parse_args  # noqa: E402
from armrl.trainer import Trainer  # noqa: E402


def one(seed, steps):
    d = tempfile.mkdtemp(prefix="det_")
    cfg = parse_args(["--seed", str(seed), "--total-steps", str(steps), "--verbose", "0",
                      "--eval-every", "2", "--eval-episodes", "4"])
    hist = Trainer(cfg, out_dir=d).train()
    return [(r.get("loss/value"), r.get("eval/return")) for r in hist]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--steps", type=int, default=8192)
    a = p.parse_args()
    h1 = one(a.seed, a.steps)
    h2 = one(a.seed, a.steps)
    bad = [i for i, (x, y) in enumerate(zip(h1, h2)) if x != y]
    if bad:
        print("NOT deterministic, first differing iteration:", bad[0] + 1)
        print(h1[bad[0]], h2[bad[0]])
        return 1
    print(f"deterministic over {len(h1)} iterations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
