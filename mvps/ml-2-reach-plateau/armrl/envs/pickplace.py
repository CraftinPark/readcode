"""Pick-and-place on the same arm + a 1-DOF gripper.

Copied over from sam's pick-place branch so the refactor wouldn't diverge
from it. NOT registered in make_env and not tested on this branch; the grasp
logic is a placeholder (a block counts as grasped when the gripper is closed
within GRASP_R of it). Don't use for anything yet.
"""
import numpy as np

from .reach import ReachArm, forward_kinematics, DT

GRASP_R = 0.05
TABLE_R = 0.8
OBS_DIM = 15
ACT_DIM = 3


class PickPlaceArm(ReachArm):
    def __init__(self, n, seed=None, ctrl_cost=0.02, contact_reward=0.0, **kw):
        super().__init__(n, seed=seed, ctrl_cost=ctrl_cost, **kw)
        self.contact_reward = contact_reward
        self.block = np.zeros((n, 2))
        self.goal = np.zeros((n, 2))
        self.grip = np.zeros(n)          # 0 open .. 1 closed
        self.grasped = np.zeros(n, dtype=bool)

    def reset_idx(self, idx):
        super().reset_idx(idx)
        idx = np.asarray(idx)
        if idx.size == 0:
            return
        self.block[idx] = self._sample_targets(idx.size)
        self.goal[idx] = self._sample_targets(idx.size)
        self.grip[idx] = 0.0
        self.grasped[idx] = False

    def observe(self):
        base = super().observe()
        _, ee = forward_kinematics(self.q)
        return np.concatenate([
            base[:, :6],
            self.block, self.goal,
            ee - self.block,
            self.grip[:, None],
            self.grasped[:, None].astype(np.float64),
            np.zeros((self.n, 1)),   # TODO block velocity once it can be pushed
        ], axis=-1).astype(np.float32)

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        obs, _, hit, info = super().step(a[:, :2])
        self.grip = np.clip(self.grip + a[:, 2] * DT * 4.0, 0.0, 1.0)
        _, ee = forward_kinematics(self.q)

        near = np.linalg.norm(ee - self.block, axis=-1) < GRASP_R
        closing = self.grip > 0.8
        self.grasped = self.grasped | (near & closing)
        self.grasped &= self.grip > 0.5           # opening drops it
        self.block[self.grasped] = ee[self.grasped]

        d_reach = np.linalg.norm(ee - self.block, axis=-1)
        d_place = np.linalg.norm(self.block - self.goal, axis=-1)
        reward = np.where(self.grasped,
                          1.0 + (1.0 - np.tanh(4.0 * d_place)),
                          1.0 - np.tanh(4.0 * d_reach)) * 0.5
        reward = reward + self.contact_reward * (near & closing)
        reward = reward - self.ctrl_cost * np.sum(a * a, axis=-1)
        success = (~self.grasped) & (d_place < GRASP_R)
        info.update({"d_reach": d_reach, "d_place": d_place, "success": success})
        # TODO terminate on success? sam had it terminating, I think that's
        # why his value loss looked weird. leave as is for now
        return self.observe(), reward.astype(np.float32), hit, info


def scripted_policy(obs):
    """dumb proportional controller in joint space, for smoke tests only"""
    n = obs.shape[0]
    act = np.zeros((n, ACT_DIM))
    err = obs[:, 10:12]
    act[:, 0] = -np.clip(err[:, 1] * 3.0, -1, 1)
    act[:, 1] = -np.clip(err[:, 0] * 3.0, -1, 1)
    close = np.linalg.norm(err, axis=-1) < GRASP_R * 1.5
    act[:, 2] = np.where(close, 1.0, -1.0)
    return act
