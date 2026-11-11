"""Callbacks for Trainer.train().

WIP (alex): Trainer doesn't call these yet. The idea is to move eval,
checkpointing and the console table out of the train loop so the pick-place
branch can plug in its own. Until then train() does it inline.
"""
import os

import numpy as np
import torch


class Callback:
    def on_train_start(self, trainer):
        pass

    def on_iteration_end(self, trainer, it, row):
        """return False to stop training"""
        return True

    def on_train_end(self, trainer):
        pass


class CheckpointCallback(Callback):
    def __init__(self, every=50, keep=3):
        self.every = every
        self.keep = keep
        self.saved = []

    def on_iteration_end(self, trainer, it, row):
        if it % self.every:
            return True
        path = os.path.join(trainer.out_dir, f"ckpt_{it:05d}.pt")
        torch.save({
            "agent": trainer.agent.state_dict(),
            "optim": trainer.ppo.optimizer.state_dict(),
            "obs_rms": None if trainer.obs_norm is None else trainer.obs_norm.rms.state_dict(),
            "it": it,
        }, path)
        self.saved.append(path)
        while len(self.saved) > self.keep:
            old = self.saved.pop(0)
            try:
                os.remove(old)
            except OSError:
                pass
        return True


class EarlyStopOnPlateau(Callback):
    """stop when eval/return hasn't improved by min_delta for `patience` evals"""

    def __init__(self, patience=10, min_delta=0.5):
        self.patience = patience
        self.min_delta = min_delta
        self.best = -np.inf
        self.bad = 0

    def on_iteration_end(self, trainer, it, row):
        r = row.get("eval/return")
        if r is None:
            return True
        if r > self.best + self.min_delta:
            self.best = r
            self.bad = 0
        else:
            self.bad += 1
        return self.bad < self.patience


class GradNormLogger(Callback):
    # print("grad norm", ...) was in ppo.update before, moved here, not wired up
    def on_iteration_end(self, trainer, it, row):
        total = 0.0
        for p in trainer.agent.parameters():
            if p.grad is not None:
                total += float(p.grad.norm() ** 2)
        row["grad_norm"] = total ** 0.5
        return True
