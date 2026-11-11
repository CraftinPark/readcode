"""Training samples: an observation history and the action chunk that follows it.

For frame i of an episode the sample is

    obs:     frames i-h+1 .. i          (h = obs_horizon; before the first frame, frame 0 repeats)
    actions: frames i .. i+k-1          (k = chunk; past the last frame, the last action repeats)
    mask:    True for real actions, False for the repeated padding

The padding keeps every frame usable as a sample (otherwise the end of every
episode, where the gripper opens over the bin, would never be a training
target); the mask keeps the invented actions out of the loss.
"""
from __future__ import annotations

import numpy as np

from pipeline.episodes import Frames


def obs_history(obs: np.ndarray, horizon: int) -> np.ndarray:
    """(T, D) -> (T, horizon, D), oldest first."""
    T = len(obs)
    idx = np.arange(T)[:, None] + np.arange(-horizon + 1, 1)[None, :]
    return obs[np.clip(idx, 0, T - 1)]


def action_chunks(act: np.ndarray, chunk: int) -> tuple[np.ndarray, np.ndarray]:
    """(T, A) -> chunks (T, chunk, A) and mask (T, chunk)."""
    T = len(act)
    idx = np.arange(T)[:, None] + np.arange(chunk)[None, :]
    mask = idx < T
    return act[np.minimum(idx, T - 1)], mask


def episode_samples(fr: Frames, obs_horizon: int, chunk: int) -> dict:
    """All samples of one episode; frames whose camera reading is stale are left out."""
    obs = obs_history(fr.obs, obs_horizon)
    acts, mask = action_chunks(fr.act, chunk)
    keep = fr.usable
    return {
        "obs": obs[keep],
        "act": acts[keep],
        "mask": mask[keep],
        "episode": np.full(int(keep.sum()), fr.episode_id, dtype=np.int64),
    }


def stack_samples(per_episode: list[dict]) -> dict:
    if not per_episode:
        raise ValueError("no samples")
    return {k: np.concatenate([s[k] for s in per_episode]) for k in per_episode[0]}
