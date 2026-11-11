"""Put asynchronous device streams on one policy-rate time grid.

Each device samples at its own rate with its own jitter, so nothing lines up
sample for sample. We build one grid at the policy rate over the window where
every stream has data, and read each stream on it:

- continuous signals (positions, jaw opening) are linearly interpolated;
- discrete commands (the gripper trigger) are held: the value on the grid is
  the last command sent at or before that instant. Interpolating a 0/1 trigger
  would invent half-closed commands that the operator never sent;
- camera detections are interpolated between valid frames only, and every grid
  point also gets the age of the newest valid frame, so frames too far from
  any real detection can be masked.
"""
from __future__ import annotations

import numpy as np


def common_window(streams) -> tuple[float, float]:
    """[start, end] covered by every stream."""
    t0 = max(float(s.t[0]) for s in streams)
    t1 = min(float(s.t[-1]) for s in streams)
    if t1 <= t0:
        raise ValueError("streams do not overlap")
    return t0, t1


def make_grid(t0: float, t1: float, rate_hz: float) -> np.ndarray:
    """Grid points t0, t0 + 1/rate, ... up to and including t1 (within 1 us)."""
    n = int(np.floor((t1 - t0) * rate_hz + 1e-6)) + 1
    return t0 + np.arange(n, dtype=np.float64) / rate_hz


def interp_linear(t: np.ndarray, x: np.ndarray, grid: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        return np.interp(grid, t, x)
    return np.stack([np.interp(grid, t, x[:, j]) for j in range(x.shape[1])], axis=1)


def hold_last(t: np.ndarray, x: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Zero-order hold: x at the latest t <= grid (the first sample before the stream starts)."""
    idx = np.searchsorted(t, grid, side="right") - 1
    idx = np.clip(idx, 0, len(t) - 1)
    return np.asarray(x)[idx]


def interp_valid(t: np.ndarray, x: np.ndarray, valid: np.ndarray,
                 grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate over valid samples only. Returns (values, age of newest valid sample)."""
    valid = np.asarray(valid, dtype=bool)
    if valid.sum() < 2:
        raise ValueError("fewer than two valid samples")
    tv, xv = t[valid], np.asarray(x)[valid]
    values = interp_linear(tv, xv, grid)
    idx = np.searchsorted(tv, grid, side="right") - 1
    age = np.where(idx >= 0, grid - tv[np.clip(idx, 0, None)], np.inf)
    return values, age
