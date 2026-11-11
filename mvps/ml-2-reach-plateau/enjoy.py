"""Roll out a saved policy and print what the arm does.

    python train.py --preset quick --save-model true
    python enjoy.py runs/reach__s1__<stamp>/model.pt --episodes 3
"""
import argparse
import json
import os

import numpy as np
import torch

from armrl.agent import ActorCritic
from armrl.config import Config
from armrl.envs.wrappers import VecReach
from armrl.normalize import ObsNormalizer


def load(path):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    cfg = Config()
    cfg_path = os.path.join(os.path.dirname(path), "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            for k, v in json.load(f).items():
                if hasattr(cfg, k) and not isinstance(getattr(type(cfg), k, None), property):
                    setattr(cfg, k, tuple(v) if isinstance(v, list) else v)
    agent = ActorCritic(10, 2, cfg.hidden, cfg.init_log_std)
    agent.load_state_dict(ck["agent"])
    norm = None
    if ck.get("obs_rms") is not None:
        norm = ObsNormalizer(10, clip=cfg.obs_clip)
        norm.rms.load_state_dict(ck["obs_rms"])
        norm.frozen = True
    return agent, norm, cfg


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model")
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--stochastic", action="store_true")
    a = p.parse_args()

    agent, norm, cfg = load(a.model)
    env = VecReach(1, max_steps=cfg.max_episode_steps, seed=a.seed, ctrl_cost=cfg.ctrl_cost)
    for ep in range(a.episodes):
        obs = env.reset()
        total = 0.0
        for t in range(cfg.max_episode_steps):
            x = norm(obs, update=False) if norm is not None else obs
            act = agent.act(torch.as_tensor(x), deterministic=not a.stochastic).numpy()
            obs, r, term, trunc, info = env.step(act)
            total += float(r[0])
            if t % 10 == 0:
                d = np.hypot(obs[0, 8], obs[0, 9])
                print(f"  ep {ep} t {t:3d}  dist {d:.3f}  r {r[0]:.3f}")
            if term[0] or trunc[0]:
                break
        print(f"episode {ep}: return {total:.2f}, len {t + 1}, hit {bool(term[0])}")


if __name__ == "__main__":
    main()
