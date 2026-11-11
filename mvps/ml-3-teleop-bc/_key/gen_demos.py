"""Generate the shipped demonstrations (key only; the player gets the output in data/demos).

A scripted operator teleoperates the bench twin through a leader arm; the rig v2
recorder writes each device's stream with its own host stamps. The leader
stream starts only when the deadman pedal goes down (0.3-0.9 s after
"record"), the follower and camera streams start within ~60 ms of it.

    python _key/gen_demos.py [OUT_DIR] [--n 150]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from rig.recorder import EpisodeRecorder  # noqa: E402
from sim.env import CellConfig, PickPlaceCell  # noqa: E402

OPERATORS = ["op_a", "op_b", "op_c"]
GAP_EPISODES = {17, 64, 101, 133}      # USB hiccup: camera drops out for ~0.6 s
SHORT_EPISODES = {45, 122}             # operator aborted early (pedal released before release)


def record_episode(out_root: str, ep: int, base_ns: int) -> str:
    rng = np.random.default_rng(10_000 + ep)
    cell = PickPlaceCell(CellConfig())
    s = cell.reset(seed=20_000 + ep)
    dt = cell.dt
    op = OPERATORS[ep % len(OPERATORS)]
    vmax = {"op_a": 0.20, "op_b": 0.16, "op_c": 0.24}[op] * rng.uniform(0.85, 1.15)

    start_ns = base_ns + ep * 37_000_000_000 + int(rng.integers(0, 10**9))
    rec = EpisodeRecorder(out_root, ep, op, task={"bin_xy": [float(s.bin[0]), float(s.bin[1])],
                                                  "cell": "cell-2"})
    rec.start(start_ns)

    pedal_at = rng.uniform(0.3, 0.9)
    follower_first = rng.uniform(0.002, 0.02)
    camera_first = rng.uniform(0.02, 0.06)
    cam_period = 1.0 / 30.0
    next_cam = camera_first
    next_leader = pedal_at
    gap = (rng.uniform(2.0, 4.0), 0.6) if ep in GAP_EPISODES else None

    leader = s.ee.copy()
    grip_cmd = 0
    phase = "reach"
    phase_t = 0.0
    bin_goal = s.bin + rng.normal(0, 0.006, 2)
    pedal_up_at = None
    stop_at = None
    tremor = np.zeros(2)
    hesitate = rng.uniform(0.05, 0.2)
    cmd_xy = s.ee.copy()
    cmd_grip = 0
    t = 0.0
    prev_ee = s.ee.copy()

    def ns(tt: float, jitter: float) -> int:
        return start_ns + int(round((tt + rng.normal(0, jitter)) * 1e9))

    while True:
        # --- operator + leader at 50 Hz, only while pedal is down
        if t + 1e-9 >= next_leader and pedal_up_at is None:
            fol_speed = np.linalg.norm(s.ee - prev_ee) / dt
            if phase == "reach":
                goal = s.block
                if (np.linalg.norm(s.ee - s.block) < 0.006 and fol_speed < 0.03):
                    phase, phase_t = "close", t
            elif phase == "close":
                goal = s.block
                if t - phase_t > hesitate:
                    grip_cmd = 1
                if s.holding and s.grip >= 0.99 and t - phase_t > hesitate + 0.25:
                    phase, phase_t = "carry", t
            elif phase == "carry":
                goal = bin_goal
                if np.linalg.norm(s.ee - bin_goal) < 0.008 and fol_speed < 0.03:
                    phase, phase_t = "open", t
            else:  # open
                goal = bin_goal
                if t - phase_t > hesitate:
                    grip_cmd = 0
                if t - phase_t > hesitate + 0.45:
                    pedal_up_at = t
                    stop_at = t + rng.uniform(0.3, 0.8)
            if ep in SHORT_EPISODES and phase == "carry" and t - phase_t > 0.8:
                pedal_up_at = t
                stop_at = t + 0.4

            d = goal - leader
            dist = np.linalg.norm(d)
            step = min(vmax, 3.0 * dist) * 0.02
            if dist > 1e-9:
                leader = leader + d / dist * min(step, dist)
            tremor = 0.85 * tremor + rng.normal(0, 0.0004, 2)
            cmd_xy = leader + tremor
            cmd_grip = grip_cmd
            rec.writer("leader").append(ns(t, 0.0008), pos=cmd_xy.astype(np.float32), grip=np.uint8(cmd_grip))
            next_leader += 0.02

        # --- physics + follower at 100 Hz
        prev_ee = s.ee.copy()
        cell._physics_step(cmd_xy, cmd_grip)
        t = s.t
        if t >= follower_first:
            pos, g = cell.read_follower()
            rec.writer("follower").append(ns(t, 0.0003), pos=pos.astype(np.float32), grip=np.float32(g))

        # --- camera ~30 Hz
        if t + 1e-9 >= next_cam:
            in_gap = gap is not None and gap[0] <= t < gap[0] + gap[1]
            if not in_gap:
                if rng.random() < cell.cfg.camera_dropout:
                    xy, det = np.full(2, np.nan), False
                else:
                    xy, det = s.block + rng.normal(0, cell.cfg.camera_noise, 2), True
                rec.writer("camera").append(ns(t, 0.002), block=np.asarray(xy, np.float32), detected=bool(det))
            next_cam += cam_period

        if stop_at is not None and t >= stop_at:
            break
        if t > 30.0:
            raise RuntimeError(f"episode {ep} did not finish")
    return rec.finish(notes="")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=os.path.join(ROOT, "data", "demos"))
    ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    base_ns = 88_412_000_000_000
    for ep in range(a.n):
        record_episode(a.out, ep, base_ns)
    print(f"wrote {a.n} episodes to {a.out}")


if __name__ == "__main__":
    main()
