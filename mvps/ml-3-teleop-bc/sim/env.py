"""Bench twin of the pick-and-place cell.

A planar model of cell 2: the follower arm's end effector moves in the table
plane, a parallel gripper closes on a block, and the block has to be put down
inside the bin. Units are metres and seconds throughout.

The twin is what `evaluate.py` runs policies against before they go on the
real cell. Its dynamics were fitted to the follower's position controller:
a first-order lag towards the commanded position with a speed limit, and a
gripper that takes about 0.2 s to travel from open to closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class CellConfig:
    physics_hz: int = 100
    camera_hz: float = 30.0
    tau_s: float = 0.25            # follower position-controller time constant
    max_speed: float = 0.35        # m/s, follower speed limit
    gripper_travel_s: float = 0.2  # open -> closed
    grasp_radius: float = 0.015    # block must be this close when the jaws shut
    knock_radius: float = 0.05     # closer than this, a miss pushes the block
    bin_radius: float = 0.04
    table_x: tuple = (0.0, 0.5)
    table_y: tuple = (0.0, 0.4)
    proprio_noise: float = 0.0005
    camera_noise: float = 0.0015
    camera_dropout: float = 0.03


@dataclass
class CellState:
    t: float = 0.0
    ee: np.ndarray = field(default_factory=lambda: np.zeros(2))
    grip: float = 0.0              # 0 open, 1 closed (jaw position)
    block: np.ndarray = field(default_factory=lambda: np.zeros(2))
    bin: np.ndarray = field(default_factory=lambda: np.zeros(2))
    holding: bool = False
    done: bool = False
    success: bool = False
    missed_grasps: int = 0
    drops: int = 0


class PickPlaceCell:
    """Physics of the cell. Commands are follower position targets + a binary gripper."""

    def __init__(self, cfg: CellConfig | None = None):
        self.cfg = cfg or CellConfig()
        self.dt = 1.0 / self.cfg.physics_hz
        self.s = CellState()
        self.rng = np.random.default_rng(0)
        self._last_frame_t = -1.0
        self._last_frame = (np.zeros(2), False)
        self._frame_phase = 0.0

    # ----------------------------------------------------------------- setup
    def reset(self, seed: int) -> CellState:
        self.rng = np.random.default_rng(seed)
        c = self.cfg
        lo = np.array([c.table_x[0] + 0.05, c.table_y[0] + 0.05])
        hi = np.array([c.table_x[1] - 0.05, c.table_y[1] - 0.05])
        while True:
            ee = self.rng.uniform(lo, hi)
            block = self.rng.uniform(lo, hi)
            bin_ = self.rng.uniform(lo, hi)
            if (np.linalg.norm(block - ee) > 0.12 and np.linalg.norm(bin_ - block) > 0.15
                    and np.linalg.norm(bin_ - ee) > 0.08):
                break
        self.s = CellState(t=0.0, ee=ee, grip=0.0, block=block, bin=bin_)
        self._frame_phase = float(self.rng.uniform(0.0, 1.0 / c.camera_hz))
        # The camera has been streaming before the episode starts: the newest
        # frame is from just before t = 0 and shows the block.
        self._last_frame_t = self._frame_phase - 1.0 / c.camera_hz
        self._last_frame = (block + self.rng.normal(0.0, c.camera_noise, 2), True)
        return self.s

    # ---------------------------------------------------------------- physics
    def _physics_step(self, cmd_xy: np.ndarray, cmd_grip: float) -> None:
        c, s = self.cfg, self.s
        if s.done:
            s.t += self.dt
            return
        lo = np.array([c.table_x[0], c.table_y[0]])
        hi = np.array([c.table_x[1], c.table_y[1]])
        target = np.clip(np.asarray(cmd_xy, dtype=float), lo, hi)
        v = (target - s.ee) / c.tau_s
        speed = float(np.linalg.norm(v))
        if speed > c.max_speed:
            v *= c.max_speed / speed
        s.ee = s.ee + v * self.dt

        was = s.grip
        rate = self.dt / c.gripper_travel_s
        goal = 1.0 if cmd_grip >= 0.5 else 0.0
        s.grip = float(np.clip(s.grip + np.sign(goal - s.grip) * rate, 0.0, 1.0))

        if was < 0.95 <= s.grip and not s.holding:
            if np.linalg.norm(s.ee - s.block) < c.grasp_radius:
                s.holding = True
            else:
                s.missed_grasps += 1
                d = s.block - s.ee
                dist = float(np.linalg.norm(d))
                if dist < c.knock_radius:
                    # a jaw closing next to the block shoves it away
                    push = self.rng.uniform(0.02, 0.04) * (d / max(dist, 1e-6))
                    lo = np.array([c.table_x[0], c.table_y[0]])
                    hi = np.array([c.table_x[1], c.table_y[1]])
                    s.block = np.clip(s.block + push, lo + 0.01, hi - 0.01)
        if s.holding:
            s.block = s.ee.copy()
            if s.grip < 0.5:
                s.holding = False
                if np.linalg.norm(s.block - s.bin) < c.bin_radius:
                    s.success = True
                    s.done = True
                else:
                    s.drops += 1
        s.t += self.dt

    def run(self, cmd_xy, cmd_grip, duration_s: float) -> None:
        n = int(round(duration_s * self.cfg.physics_hz))
        for _ in range(n):
            self._physics_step(cmd_xy, cmd_grip)

    # ---------------------------------------------------------------- sensing
    def read_follower(self) -> tuple[np.ndarray, float]:
        """Joint-encoder readout mapped to the table plane (what the follower driver publishes)."""
        noise = self.rng.normal(0.0, self.cfg.proprio_noise, 2)
        return self.s.ee + noise, self.s.grip

    def camera_due(self) -> bool:
        period = 1.0 / self.cfg.camera_hz
        k = np.floor((self.s.t - self._frame_phase) / period + 1e-9)
        frame_t = self._frame_phase + k * period
        return frame_t > self._last_frame_t + 1e-9 and frame_t <= self.s.t + 1e-9

    def capture(self) -> tuple[np.ndarray, bool]:
        """One overhead-camera frame run through the block detector: (xy, detected)."""
        period = 1.0 / self.cfg.camera_hz
        k = np.floor((self.s.t - self._frame_phase) / period + 1e-9)
        self._last_frame_t = self._frame_phase + k * period
        if self.rng.random() < self.cfg.camera_dropout:
            self._last_frame = (np.full(2, np.nan), False)
        else:
            xy = self.s.block + self.rng.normal(0.0, self.cfg.camera_noise, 2)
            self._last_frame = (xy, True)
        return self._last_frame

    def latest_frame(self) -> tuple[np.ndarray, bool]:
        if self.camera_due():
            self.capture()
        return self._last_frame
