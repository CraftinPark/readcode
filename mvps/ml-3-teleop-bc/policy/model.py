"""Chunked behaviour-cloning policy.

An MLP from a short observation history to a chunk of future actions. Each
chunk step has two positions (normalised) and one gripper logit. Small on
purpose: cell 2 runs on low-dimensional state (the block detector replaces the
image encoder), and the whole thing trains on a laptop CPU in under a minute.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from config import ACT_FIELDS, GRIP, OBS_FIELDS, PolicyConfig


class ChunkPolicy(nn.Module):
    def __init__(self, cfg: PolicyConfig):
        super().__init__()
        self.cfg = cfg
        d_in = cfg.obs_horizon * len(OBS_FIELDS)
        d_out = cfg.chunk * len(ACT_FIELDS)
        dims = [d_in] + [cfg.hidden] * cfg.layers
        blocks = []
        for a, b in zip(dims[:-1], dims[1:]):
            blocks += [nn.Linear(a, b), nn.LayerNorm(b), nn.GELU()]
        self.trunk = nn.Sequential(*blocks)
        self.head = nn.Linear(cfg.hidden, d_out)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        """obs (B, h, D) normalised -> (B, chunk, 3): [pos_x, pos_y, grip_logit]."""
        B = obs.shape[0]
        y = self.head(self.trunk(obs.reshape(B, -1)))
        return y.view(B, self.cfg.chunk, len(ACT_FIELDS))


def chunk_loss(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor,
               grip_weight: float) -> tuple[torch.Tensor, dict]:
    """Masked L1 on positions + masked BCE on the gripper. Returns (loss, parts)."""
    pos = [i for i in range(pred.shape[-1]) if i != GRIP]
    m = mask.to(pred.dtype)
    denom = m.sum().clamp_min(1.0)
    l1 = (pred[..., pos] - target[..., pos]).abs().mean(-1)
    l1 = (l1 * m).sum() / denom
    bce = F.binary_cross_entropy_with_logits(pred[..., GRIP], target[..., GRIP], reduction="none")
    bce = (bce * m).sum() / denom
    loss = l1 + grip_weight * bce
    return loss, {"l1": float(l1.detach()), "bce": float(bce.detach())}
