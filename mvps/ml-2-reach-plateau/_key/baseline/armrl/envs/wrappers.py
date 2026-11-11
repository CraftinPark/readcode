"""Time limit + auto reset around ReachArm.

New-style API (terminated / truncated split), see CHANGELOG 2026-10-20.

When an arm finishes (either flag) it is reset inside step(), so the obs we
hand back for that index is already the first obs of the next episode. The
last real obs is kept in info["final_obs"] for whoever needs it (the trainer
does, for time-limit bootstrapping).
"""
import numpy as np

from .reach import ReachArm, OBS_DIM, ACT_DIM


class VecReach:
    def __init__(self, n_envs, max_steps=100, seed=None, **env_kwargs):
        self.n = n_envs
        self.max_steps = max_steps
        self.arm = ReachArm(n_envs, seed=seed, **env_kwargs)
        self.t = np.zeros(n_envs, dtype=np.int64)
        self.ep_ret = np.zeros(n_envs, dtype=np.float64)
        self.ep_len = np.zeros(n_envs, dtype=np.int64)
        self.obs_dim = OBS_DIM
        self.act_dim = ACT_DIM

    def reset(self):
        self.t[:] = 0
        self.ep_ret[:] = 0
        self.ep_len[:] = 0
        return self.arm.reset()

    def step(self, action):
        obs, rew, terminated, info = self.arm.step(action)
        self.t += 1
        self.ep_ret += rew
        self.ep_len += 1
        truncated = (self.t >= self.max_steps) & ~terminated

        done = terminated | truncated
        info["final_obs"] = None
        info["episodes"] = []
        if done.any():
            idx = np.nonzero(done)[0]
            info["final_obs"] = obs[idx].copy()
            info["final_idx"] = idx
            for i in idx:
                info["episodes"].append({
                    "r": float(self.ep_ret[i]),
                    "l": int(self.ep_len[i]),
                    "hit": bool(terminated[i]),
                })
            self.arm.reset_idx(idx)
            self.t[idx] = 0
            self.ep_ret[idx] = 0
            self.ep_len[idx] = 0
            obs = self.arm.observe()
        return obs, rew, terminated, truncated, info


def make_env(cfg, seed, n_envs=None):
    return VecReach(
        n_envs or cfg.n_envs,
        max_steps=cfg.max_episode_steps,
        seed=seed,
        ctrl_cost=cfg.ctrl_cost,
    )


# --- old API, kept until the sweep scripts are ported -------------------
class LegacyVecReach(VecReach):
    """step() -> obs, rew, done, info  (done = terminated or truncated)

    TODO remove after sweeps/ is moved over (alex)
    """

    def step(self, action):
        obs, rew, term, trunc, info = super().step(action)
        return obs, rew, term | trunc, info
