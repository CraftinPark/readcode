"""Training loop for the chunk policy."""
from __future__ import annotations

import math
import os
import time

import numpy as np
import torch

from config import DataConfig, PolicyConfig, TrainConfig, to_dict
from pipeline.dataset import DemoData
from policy.model import ChunkPolicy, chunk_loss


def lr_at(step: int, cfg: TrainConfig) -> float:
    if step < cfg.warmup:
        return cfg.lr * (step + 1) / cfg.warmup
    p = (step - cfg.warmup) / max(1, cfg.steps - cfg.warmup)
    return cfg.lr * 0.5 * (1.0 + math.cos(math.pi * min(1.0, p)))


@torch.no_grad()
def evaluate_loss(model: ChunkPolicy, split: dict, grip_weight: float, batch: int = 4096) -> dict:
    model.eval()
    tot = {"loss": 0.0, "l1": 0.0, "bce": 0.0}
    n = len(split["obs"])
    for i in range(0, n, batch):
        sl = slice(i, i + batch)
        loss, parts = chunk_loss(model(split["obs"][sl]), split["act"][sl], split["mask"][sl], grip_weight)
        w = min(batch, n - i) / n
        tot["loss"] += float(loss) * w
        tot["l1"] += parts["l1"] * w
        tot["bce"] += parts["bce"] * w
    model.train()
    return tot


def train(data: DemoData, pcfg: PolicyConfig, tcfg: TrainConfig, dcfg: DataConfig | None = None,
          verbose: bool = True) -> tuple[ChunkPolicy, dict]:
    # A model this small is fastest on one thread; more threads only contend.
    torch.set_num_threads(1)
    torch.manual_seed(tcfg.seed)
    gen = torch.Generator().manual_seed(tcfg.seed)
    model = ChunkPolicy(pcfg)
    opt = torch.optim.AdamW(model.parameters(), lr=tcfg.lr, weight_decay=tcfg.weight_decay)
    tr = data.train
    n = len(tr["obs"])
    history = []
    t_start = time.time()
    for step in range(tcfg.steps):
        for g in opt.param_groups:
            g["lr"] = lr_at(step, tcfg)
        idx = torch.randint(0, n, (tcfg.batch_size,), generator=gen)
        loss, parts = chunk_loss(model(tr["obs"][idx]), tr["act"][idx], tr["mask"][idx], tcfg.grip_weight)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if (step + 1) % tcfg.log_every == 0 or step + 1 == tcfg.steps:
            val = evaluate_loss(model, data.val, tcfg.grip_weight)
            rec = {"step": step + 1, "train": loss.item(), "val": val["loss"],
                   "val_l1": val["l1"], "val_bce": val["bce"]}
            history.append(rec)
            if verbose:
                print(f"step {step + 1:5d}  train {rec['train']:.4f}  val {rec['val']:.4f} "
                      f"(l1 {rec['val_l1']:.4f}, bce {rec['val_bce']:.4f})  {time.time() - t_start:.1f}s")
    model.eval()
    return model, {"history": history, "seconds": time.time() - t_start}


def save_checkpoint(path: str, model: ChunkPolicy, data: DemoData, pcfg: PolicyConfig,
                    tcfg: TrainConfig, dcfg: DataConfig, info: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    torch.save({
        "model": model.state_dict(),
        "policy_cfg": to_dict(pcfg)["PolicyConfig"],
        "normalizer": data.normalizer.state_dict(),
        "config": to_dict(dcfg, tcfg),
        "train_ids": data.train_ids,
        "val_ids": data.val_ids,
        "history": info["history"],
    }, path)


def seed_everything(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
