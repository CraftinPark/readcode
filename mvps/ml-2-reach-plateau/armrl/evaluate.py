import numpy as np
import torch

from .envs.wrappers import VecReach


def evaluate(agent, obs_norm, cfg, n_episodes=None, seed=10_000, deterministic=True):
    """Mean return over n_episodes fresh episodes.

    Uses its own env and a COPY of the obs normaliser so eval can never move
    the training statistics (that bit us on the quadruped project).
    """
    n_episodes = n_episodes or cfg.eval_episodes
    env = VecReach(n_episodes, max_steps=cfg.max_episode_steps, seed=seed, ctrl_cost=cfg.ctrl_cost)
    norm = obs_norm.copy() if obs_norm is not None else None
    if norm is not None:
        norm.frozen = True

    obs = env.reset()
    returns = np.full(n_episodes, np.nan)
    final_dist = np.full(n_episodes, np.nan)
    finished = np.zeros(n_episodes, dtype=bool)
    while not finished.all():
        x = norm(obs) if norm is not None else obs
        with torch.no_grad():
            a = agent.act(torch.as_tensor(x), deterministic=deterministic).numpy()
        obs, _, term, trunc, info = env.step(a)
        done = term | trunc
        if done.any():
            for k, i in enumerate(info["final_idx"]):
                if not finished[i]:
                    returns[i] = info["episodes"][k]["r"]
                    final_dist[i] = env.arm.target is not None and _dist_from_obs(info["final_obs"][k])
                    finished[i] = True
    return {
        "eval/return": float(np.mean(returns)),
        "eval/return_std": float(np.std(returns)),
        "eval/final_dist": float(np.mean(final_dist)),
    }


def _dist_from_obs(o):
    return float(np.hypot(o[8], o[9]))
