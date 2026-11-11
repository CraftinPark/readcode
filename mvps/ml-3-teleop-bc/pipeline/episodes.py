"""Turn one recorded episode into policy-rate frames: (obs, action) pairs on a grid."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import ACT_FIELDS, OBS_FIELDS, DataConfig
from pipeline import sync
from pipeline.io import Episode, list_episodes, load_episode


@dataclass
class Frames:
    episode_id: int
    t: np.ndarray            # (T,) grid times, seconds
    obs: np.ndarray          # (T, len(OBS_FIELDS)) float32
    act: np.ndarray          # (T, len(ACT_FIELDS)) float32
    usable: np.ndarray       # (T,) bool: False where the camera reading is too old

    def __len__(self) -> int:
        return len(self.t)


class Rejected(Exception):
    """An episode that fails a quality gate. `reason` is shown in the dataset report."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def check_quality(ep: Episode, cfg: DataConfig) -> None:
    for name, s in ep.streams.items():
        if len(s) < 2:
            raise Rejected(f"{name}: fewer than 2 samples")
        limit = cfg.max_gap_s.get(name)
        if limit is not None and s.max_gap() > limit:
            raise Rejected(f"{name}: gap of {s.max_gap():.3f} s")
    detected = ep.streams["camera"].values["detected"].astype(bool)
    if detected.mean() < cfg.min_detected:
        raise Rejected(f"camera: only {detected.mean():.0%} of frames detected the block")


def _trim_tail(act: np.ndarray, cfg: DataConfig) -> int:
    """Number of frames to keep: the static tail after the last motion is cut to `tail_keep`."""
    moved = np.linalg.norm(np.diff(act[:, :2], axis=0), axis=1) > cfg.idle_eps
    moved |= np.diff(act[:, 2]) != 0
    if not moved.any():
        return len(act)
    last = int(np.nonzero(moved)[0][-1]) + 1        # index of the last frame that differs
    return min(len(act), last + 1 + cfg.tail_keep)


def align_episode(ep: Episode, cfg: DataConfig) -> Frames:
    """Resample an episode onto the policy grid. Raises `Rejected` on bad data."""
    check_quality(ep, cfg)
    leader, follower, camera = (ep.streams[n] for n in ("leader", "follower", "camera"))
    t0, t1 = sync.common_window([leader, follower, camera])
    if t1 - t0 < cfg.min_window_s:
        raise Rejected(f"only {t1 - t0:.2f} s where all streams have data")
    grid = sync.make_grid(t0, t1, cfg.policy_hz)

    ee = sync.interp_linear(follower.t, follower.values["pos"], grid)
    jaw = sync.interp_linear(follower.t, follower.values["grip"], grid)
    block, age = sync.interp_valid(camera.t, camera.values["block"], camera.values["detected"], grid)
    bin_xy = np.broadcast_to(ep.bin_xy, (len(grid), 2))

    target = sync.interp_linear(leader.t, leader.values["pos"], grid)
    grip = sync.hold_last(leader.t, leader.values["grip"], grid).astype(np.float64)

    obs = np.column_stack([ee, jaw, block, bin_xy]).astype(np.float32)
    act = np.column_stack([target, grip]).astype(np.float32)
    assert obs.shape[1] == len(OBS_FIELDS) and act.shape[1] == len(ACT_FIELDS)

    keep = _trim_tail(act, cfg)
    usable = age[:keep] <= cfg.max_camera_age_s
    return Frames(ep.episode_id, grid[:keep], obs[:keep], act[:keep], usable)


@dataclass
class BuildReport:
    kept: list
    rejected: list           # (episode_id, reason)

    def summary(self) -> str:
        lines = [f"{len(self.kept)} episodes kept, {len(self.rejected)} rejected"]
        lines += [f"  ep {eid:04d}: {why}" for eid, why in self.rejected]
        return "\n".join(lines)


def build_frames(cfg: DataConfig) -> tuple[list[Frames], BuildReport]:
    frames, rejected = [], []
    for ep_dir in list_episodes(cfg.root):
        ep = load_episode(ep_dir)
        try:
            frames.append(align_episode(ep, cfg))
        except Rejected as r:
            rejected.append((ep.episode_id, r.reason))
    return frames, BuildReport([f.episode_id for f in frames], rejected)
