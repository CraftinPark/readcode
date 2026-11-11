"""Read rig v2 episodes from disk (see `rig/recorder.py` for the layout)."""
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass

import numpy as np

STREAMS = ("leader", "follower", "camera")


@dataclass
class Stream:
    name: str
    t: np.ndarray                 # seconds, float64, strictly increasing
    values: dict                  # field -> array with len(t) rows

    def __len__(self) -> int:
        return len(self.t)

    @property
    def duration(self) -> float:
        return float(self.t[-1] - self.t[0]) if len(self.t) > 1 else 0.0

    def rate_hz(self) -> float:
        return (len(self.t) - 1) / self.duration if self.duration > 0 else 0.0

    def max_gap(self) -> float:
        return float(np.max(np.diff(self.t))) if len(self.t) > 1 else float("inf")


@dataclass
class Episode:
    episode_id: int
    meta: dict
    streams: dict                 # name -> Stream
    path: str

    @property
    def bin_xy(self) -> np.ndarray:
        return np.asarray(self.meta["task"]["bin_xy"], dtype=np.float64)


def _seconds(t_ns: np.ndarray) -> np.ndarray:
    # Host monotonic stamps are ~1e14 ns. Move the origin before converting so
    # the float32 tensors built downstream keep sub-millisecond resolution.
    t_ns = np.asarray(t_ns, dtype=np.int64)
    return (t_ns - t_ns.min()).astype(np.float64) * 1e-9


def _sorted_unique(t: np.ndarray, values: dict) -> tuple[np.ndarray, dict]:
    """Writer threads can flush a sample twice after a USB reconnect; keep the first."""
    order = np.argsort(t, kind="stable")
    t = t[order]
    keep = np.concatenate([[True], np.diff(t) > 0])
    return t[keep], {k: v[order][keep] for k, v in values.items()}


def load_stream(path: str, name: str) -> Stream:
    with np.load(path) as z:
        t = _seconds(z["t_ns"])
        values = {k: np.asarray(z[k]) for k in z.files if k != "t_ns"}
    t, values = _sorted_unique(t, values)
    return Stream(name=name, t=t, values=values)


def load_episode(ep_dir: str) -> Episode:
    with open(os.path.join(ep_dir, "meta.json")) as f:
        meta = json.load(f)
    streams = {}
    for name in STREAMS:
        path = os.path.join(ep_dir, f"{name}.npz")
        if not os.path.exists(path):
            raise FileNotFoundError(f"{ep_dir}: missing {name}.npz")
        streams[name] = load_stream(path, name)
    return Episode(episode_id=int(meta["episode_id"]), meta=meta, streams=streams, path=ep_dir)


def list_episodes(root: str) -> list[str]:
    return sorted(p for p in glob.glob(os.path.join(root, "ep_*")) if os.path.isdir(p))
