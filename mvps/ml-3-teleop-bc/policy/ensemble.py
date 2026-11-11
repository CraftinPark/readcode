"""Temporal ensembling of overlapping action chunks (as in ACT).

The policy is queried at every control step and each query predicts the next
`chunk` actions, so at step t up to `chunk` earlier queries each hold a
prediction for t. The command sent is their weighted average, with weight
exp(-m * i) where i = 0 is the OLDEST prediction still covering t. Older
predictions weigh more: that is what keeps the commanded motion smooth when a
new query disagrees with the plan already under way. A larger m makes the
weights fall off faster, so the oldest predictions dominate even more.

Positions are averaged in metres. The gripper is averaged as a probability
and thresholded afterwards, so a single query that flips does not toggle the
jaws.
"""
from __future__ import annotations

from collections import deque

import numpy as np


class TemporalEnsembler:
    def __init__(self, chunk: int, m: float = 0.1):
        self.chunk = chunk
        self.m = m
        self._chunks: deque = deque(maxlen=chunk)    # (issued_step, pos (k,2), grip_p (k,))
        self.step = 0

    def reset(self) -> None:
        self._chunks.clear()
        self.step = 0

    def add(self, pos: np.ndarray, grip_p: np.ndarray) -> None:
        """Register the chunk predicted at the current step."""
        self._chunks.append((self.step, np.asarray(pos, np.float64), np.asarray(grip_p, np.float64)))

    def current(self) -> tuple[np.ndarray, float]:
        """Ensembled (position, gripper probability) for the current step, then advance."""
        preds_pos, preds_grip = [], []
        for issued, pos, gp in self._chunks:          # oldest first
            offset = self.step - issued
            if 0 <= offset < self.chunk:
                preds_pos.append(pos[offset])
                preds_grip.append(gp[offset])
        if not preds_pos:
            raise RuntimeError("no prediction covers this step; call add() first")
        w = np.exp(-self.m * np.arange(len(preds_pos)))
        w /= w.sum()
        out_pos = (w[:, None] * np.stack(preds_pos)).sum(0)
        out_grip = float((w * np.asarray(preds_grip)).sum())
        self.step += 1
        return out_pos, out_grip
