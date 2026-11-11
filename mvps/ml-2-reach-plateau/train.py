"""python train.py --preset quick --seed 1"""
import sys

from armrl.config import parse_args
from armrl.trainer import Trainer


def main(argv=None):
    cfg = parse_args(argv)
    tr = Trainer(cfg)
    print(f"run dir: {tr.out_dir}  ({cfg.n_iterations} iterations, batch {cfg.batch_size})")
    hist = tr.train()
    evals = [r["eval/return"] for r in hist if "eval/return" in r]
    if evals:
        last = evals[-3:]
        print(f"final eval return (mean of last {len(last)} evals): {sum(last) / len(last):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
