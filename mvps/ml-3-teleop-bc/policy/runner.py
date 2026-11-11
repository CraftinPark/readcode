"""Robot-side policy runner: raw observation in, follower command out.

The same class runs on the cell's control PC and in `evaluate.py`. It is
called once per policy step (10 Hz) with the latest follower state and camera
detection, and returns the position target and gripper command that the
follower driver holds until the next step.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import torch

from config import ACT_FIELDS, GRIP, OBS_FIELDS, EvalConfig, PolicyConfig
from pipeline.normalize import Normalizer
from policy.ensemble import TemporalEnsembler
from policy.model import ChunkPolicy


def build_obs(ee_xy, jaw, block_xy, bin_xy) -> np.ndarray:
    """One observation row in OBS_FIELDS order."""
    row = np.concatenate([np.asarray(ee_xy, float), [float(jaw)],
                          np.asarray(block_xy, float), np.asarray(bin_xy, float)])
    assert row.shape == (len(OBS_FIELDS),)
    return row


class PolicyRunner:
    def __init__(self, model: ChunkPolicy, normalizer: Normalizer, pcfg: PolicyConfig, ecfg: EvalConfig):
        self.model = model.eval()
        self.norm = normalizer
        self.pcfg = pcfg
        self.ecfg = ecfg
        self.ensembler = TemporalEnsembler(pcfg.chunk, ecfg.ensemble_m)
        self.history: deque = deque(maxlen=pcfg.obs_horizon)
        self._last_block = None
        self.queries = 0

    @classmethod
    def load(cls, path: str, ecfg: EvalConfig | None = None) -> "PolicyRunner":
        ck = torch.load(path, map_location="cpu", weights_only=False)
        pcfg = PolicyConfig(**ck["policy_cfg"])
        model = ChunkPolicy(pcfg)
        model.load_state_dict(ck["model"])
        return cls(model, Normalizer.from_state_dict(ck["normalizer"]), pcfg, ecfg or EvalConfig())

    def reset(self) -> None:
        self.ensembler.reset()
        self.history.clear()
        self._last_block = None

    def _push(self, obs_row: np.ndarray) -> np.ndarray:
        if not self.history:
            for _ in range(self.pcfg.obs_horizon):      # same padding as chunking.obs_history
                self.history.append(obs_row)
        else:
            self.history.append(obs_row)
        return np.stack(self.history)                    # (h, D), oldest first

    @torch.no_grad()
    def act(self, ee_xy, jaw, block_xy, detected: bool, bin_xy) -> tuple[np.ndarray, int]:
        if detected:
            self._last_block = np.asarray(block_xy, float)
        elif self._last_block is None:
            raise RuntimeError("no block detection yet")
        hist = self._push(build_obs(ee_xy, jaw, self._last_block, bin_xy))
        x = torch.from_numpy(self.norm.obs(hist)[None])
        out = self.model(x)[0].numpy()                   # (chunk, 3)
        self.queries += 1
        pos_cols = [i for i in range(len(ACT_FIELDS)) if i != GRIP]
        pos = self.norm.unact_pos(out[:, pos_cols])
        grip_p = 1.0 / (1.0 + np.exp(-out[:, GRIP]))
        self.ensembler.add(pos, grip_p)
        target, p = self.ensembler.current()
        return target, int(p >= self.ecfg.grip_threshold)
