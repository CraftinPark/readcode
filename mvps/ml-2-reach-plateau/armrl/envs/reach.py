"""Planar 2-link arm, reach a random target and stay there.

Vectorised in numpy: one ReachArm holds `n` independent arms so we don't pay
python overhead per env. Nothing fancy physically: first-order joint velocity
response (the real arm's servo loop is fast enough that this matched the
bench logs better than the full rigid-body model did, see notes/arm_model.txt
on the shared drive).

obs (10,): cos q1, sin q1, cos q2, sin q2, qd1, qd2, tx, ty, ex - tx, ey - ty
act (2,):  joint velocity command in [-1, 1], scaled by QD_MAX
"""
import numpy as np

L1 = 0.5
L2 = 0.4
DT = 0.05
QD_MAX = 2.5          # rad/s at |a| = 1
SERVO_ALPHA = 0.35    # first order lag on the velocity command
Q2_LIMIT = 2.6        # elbow, past this the forearm hits the base
TARGET_R_MIN = 0.2
TARGET_R_MAX = 0.85

OBS_DIM = 10
ACT_DIM = 2


def forward_kinematics(q):
    """q: (n, 2) -> elbow (n, 2), end effector (n, 2)"""
    q1 = q[:, 0]
    q12 = q[:, 0] + q[:, 1]
    elbow = np.stack([L1 * np.cos(q1), L1 * np.sin(q1)], axis=-1)
    ee = elbow + np.stack([L2 * np.cos(q12), L2 * np.sin(q12)], axis=-1)
    return elbow, ee


class ReachArm:
    """Bare dynamics + reward. No time limit, no auto reset (see wrappers.py)."""

    def __init__(self, n, seed=None, ctrl_cost=0.02, reach_scale=4.0, hit_penalty=0.0):
        self.n = n
        self.rng = np.random.default_rng(seed)
        self.ctrl_cost = ctrl_cost
        self.reach_scale = reach_scale
        self.hit_penalty = hit_penalty  # was -5, set to 0 in #37, losing the future reward is enough
        self.q = np.zeros((n, 2))
        self.qd = np.zeros((n, 2))
        self.target = np.zeros((n, 2))

    # -- sampling -------------------------------------------------------
    def _sample_targets(self, k):
        r = self.rng.uniform(TARGET_R_MIN, TARGET_R_MAX, size=k)
        th = self.rng.uniform(-np.pi, np.pi, size=k)
        return np.stack([r * np.cos(th), r * np.sin(th)], axis=-1)

    def _sample_q(self, k):
        q = np.empty((k, 2))
        q[:, 0] = self.rng.uniform(-np.pi, np.pi, size=k)
        q[:, 1] = self.rng.uniform(-1.5, 1.5, size=k)
        return q

    def reset_idx(self, idx):
        idx = np.asarray(idx)
        if idx.size == 0:
            return
        self.q[idx] = self._sample_q(idx.size)
        self.qd[idx] = 0.0
        self.target[idx] = self._sample_targets(idx.size)

    def reset(self):
        self.reset_idx(np.arange(self.n))
        return self.observe()

    # -- stepping -------------------------------------------------------
    def observe(self):
        _, ee = forward_kinematics(self.q)
        return np.concatenate([
            np.cos(self.q), np.sin(self.q),
            self.qd,
            self.target,
            ee - self.target,
        ], axis=-1)[:, [0, 2, 1, 3, 4, 5, 6, 7, 8, 9]].astype(np.float32)

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        cmd = a * QD_MAX
        self.qd = (1.0 - SERVO_ALPHA) * self.qd + SERVO_ALPHA * cmd
        self.q = self.q + self.qd * DT
        # wrap shoulder, elbow has hard limits
        self.q[:, 0] = (self.q[:, 0] + np.pi) % (2 * np.pi) - np.pi

        _, ee = forward_kinematics(self.q)
        dist = np.linalg.norm(ee - self.target, axis=-1)
        reward = 1.0 - np.tanh(self.reach_scale * dist)
        reward = reward - self.ctrl_cost * np.sum(a * a, axis=-1)

        hit = np.abs(self.q[:, 1]) > Q2_LIMIT
        reward = np.where(hit, reward + self.hit_penalty, reward)
        info = {"dist": dist}
        return self.observe(), reward.astype(np.float32), hit, info
