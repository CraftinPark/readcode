"""Build the dataset from data/demos and train the chunk policy.

    python train.py [--steps 3000] [--out runs/latest.pt]
"""
from __future__ import annotations

import argparse
import sys
import time

from config import DataConfig, PolicyConfig, TrainConfig
from pipeline.dataset import load_demo_data
from policy.train import save_checkpoint, seed_everything, train


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DataConfig.root)
    ap.add_argument("--steps", type=int, default=TrainConfig.steps)
    ap.add_argument("--seed", type=int, default=TrainConfig.seed)
    ap.add_argument("--out", default=TrainConfig.out)
    a = ap.parse_args(argv)

    dcfg = DataConfig(root=a.data)
    pcfg = PolicyConfig()
    tcfg = TrainConfig(steps=a.steps, seed=a.seed, out=a.out)
    seed_everything(tcfg.seed)

    t0 = time.time()
    data = load_demo_data(dcfg, pcfg)
    print(data.describe())
    print(f"dataset built in {time.time() - t0:.1f}s")

    model, info = train(data, pcfg, tcfg, dcfg)
    save_checkpoint(tcfg.out, model, data, pcfg, tcfg, dcfg, info)
    print(f"saved {tcfg.out} ({info['seconds']:.1f}s training)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
