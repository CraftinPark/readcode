"""Per-dimension normalisation statistics.

Statistics come from the training episodes only and travel inside the
checkpoint, so the robot-side runner normalises with exactly the numbers the
network was trained with. Observations are z-scored in every dimension.
Actions are z-scored in the position dimensions only: the gripper stays a 0/1
target for the classification head.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import GRIP

STD_FLOOR = 1e-3


@dataclass
class Normalizer:
    obs_mean: np.ndarray
    obs_std: np.ndarray
    act_mean: np.ndarray     # position dims only
    act_std: np.ndarray

    @classmethod
    def fit(cls, frames: list) -> "Normalizer":
        obs = np.concatenate([f.obs[f.usable] for f in frames]).astype(np.float64)
        act = np.concatenate([f.act[f.usable] for f in frames]).astype(np.float64)
        pos = np.delete(act, GRIP, axis=1)
        return cls(
            obs_mean=obs.mean(0), obs_std=np.maximum(obs.std(0), STD_FLOOR),
            act_mean=pos.mean(0), act_std=np.maximum(pos.std(0), STD_FLOOR),
        )

    # observations ----------------------------------------------------------
    def obs(self, x: np.ndarray) -> np.ndarray:
        return ((x - self.obs_mean) / self.obs_std).astype(np.float32)

    # actions: (..., 3) with the gripper in column GRIP -----------------------
    def act(self, a: np.ndarray) -> np.ndarray:
        out = np.array(a, dtype=np.float32, copy=True)
        pos = [i for i in range(out.shape[-1]) if i != GRIP]
        out[..., pos] = (out[..., pos] - self.act_mean) / self.act_std
        return out

    def unact_pos(self, p: np.ndarray) -> np.ndarray:
        """Normalised positions (..., 2) back to metres."""
        return np.asarray(p, dtype=np.float64) * self.act_std + self.act_mean

    def state_dict(self) -> dict:
        return {k: getattr(self, k).tolist() for k in ("obs_mean", "obs_std", "act_mean", "act_std")}

    @classmethod
    def from_state_dict(cls, d: dict) -> "Normalizer":
        return cls(**{k: np.asarray(v, dtype=np.float64) for k, v in d.items()})
