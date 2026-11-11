import os
import time
from collections import deque

import numpy as np
import torch

from .agent import ActorCritic
from .buffer import RolloutBuffer
from .envs.wrappers import make_env
from .evaluate import evaluate
from .logger import CSVLogger, ConsoleLog, dump_config
from .normalize import ObsNormalizer, RewardScaler
from .ppo import PPO
from .utils import linear_schedule, run_dir, seed_everything

CSV_FIELDS = [
    "iter", "steps", "time", "train/return", "train/ep_len", "train/hit_rate",
    "eval/return", "eval/final_dist", "loss/policy", "loss/value", "loss/entropy",
    "approx_kl", "clipfrac", "explained_var", "lr",
]


class Trainer:
    def __init__(self, cfg, out_dir=None):
        self.cfg = cfg
        seed_everything(cfg.seed, cfg.torch_deterministic)
        torch.set_num_threads(cfg.threads)

        self.env = make_env(cfg, seed=cfg.seed)
        self.agent = ActorCritic(self.env.obs_dim, self.env.act_dim, cfg.hidden, cfg.init_log_std)
        self.ppo = PPO(self.agent, cfg)
        self.buf = RolloutBuffer(cfg.n_steps, cfg.n_envs, self.env.obs_dim, self.env.act_dim,
                                 gamma=cfg.gamma, gae_lambda=cfg.gae_lambda)
        self.obs_norm = ObsNormalizer(self.env.obs_dim, clip=cfg.obs_clip) if cfg.norm_obs else None
        self.rew_scale = RewardScaler(cfg.n_envs, cfg.gamma) if cfg.norm_reward else None

        self.out_dir = out_dir or run_dir(cfg.log_dir, cfg.exp_name, cfg.seed)
        dump_config(cfg, os.path.join(self.out_dir, "config.json"))
        self.csv = CSVLogger(os.path.join(self.out_dir, "progress.csv"), CSV_FIELDS)
        self.console = ConsoleLog(cfg.verbose)

        self.recent = deque(maxlen=50)
        self.global_step = 0

    # ------------------------------------------------------------------
    def _norm(self, obs, update=True):
        if self.obs_norm is None:
            return obs
        return self.obs_norm(obs, update=update)

    @torch.no_grad()
    def _value(self, x):
        return self.agent.get_value(torch.as_tensor(x)).numpy()

    def collect(self, obs):
        """Fill the buffer with n_steps from every env. obs is the raw obs."""
        cfg = self.cfg
        self.buf.reset()
        x = self._norm(obs)
        for t in range(cfg.n_steps):
            with torch.no_grad():
                action, logp, _, value = self.agent.get_action_and_value(torch.as_tensor(x))
            action = action.numpy()
            # env clips to [-1, 1] itself; store the unclipped sample so the
            # stored logp is the logp of what's in the buffer
            next_obs, reward, term, trunc, info = self.env.step(action)
            self.global_step += cfg.n_envs
            done = term | trunc

            if self.rew_scale is not None:
                reward = self.rew_scale(reward, done)

            self.buf.add(x, action, logp.numpy(), reward, done.astype(np.float32), value.numpy())

            # time limit: the episode didn't really end, bootstrap from the
            # obs we would have seen next (the vec env already reset it)
            if trunc.any():
                fidx = info["final_idx"]
                fobs = info["final_obs"]
                sel = trunc[fidx]
                if sel.any():
                    # print("trunc", t, fidx[sel], fobs[sel][:, 8:10])
                    fx = self._norm(fobs[sel], update=False)
                    self.buf.add_to_reward(t, fidx[sel], cfg.gamma * self._value(fx))

            for ep in info["episodes"]:
                self.recent.append(ep)

            obs = next_obs
            x = self._norm(obs)

        last_value = self._value(x)
        return obs, x, last_value

    # ------------------------------------------------------------------
    def train(self):
        cfg = self.cfg
        n_iters = cfg.n_iterations
        obs = self.env.reset()
        t0 = time.time()
        history = []
        for it in range(1, n_iters + 1):
            if cfg.anneal_lr:
                lr = linear_schedule(cfg.lr, it, n_iters)
                self.ppo.set_lr(lr)
            else:
                lr = cfg.lr

            obs, x, last_value = self.collect(obs)
            if cfg.use_gae:
                self.buf.compute_gae(last_value)
            else:
                self.buf.compute_nstep(last_value)
            stats = self.ppo.update(self.buf)

            row = {"iter": it, "steps": self.global_step, "time": time.time() - t0, "lr": lr}
            row.update(stats)
            if self.recent:
                row["train/return"] = float(np.mean([e["r"] for e in self.recent]))
                row["train/ep_len"] = float(np.mean([e["l"] for e in self.recent]))
                row["train/hit_rate"] = float(np.mean([e["hit"] for e in self.recent]))
            eval_ret = None
            if it % cfg.eval_every == 0 or it == n_iters:
                ev = evaluate(self.agent, self.obs_norm, cfg)
                row.update(ev)
                eval_ret = ev["eval/return"]
            self.csv.log(row)
            sps = self.global_step / max(time.time() - t0, 1e-6)
            self.console.row(it, n_iters, self.global_step, row.get("train/return", 0.0), eval_ret, stats, sps)
            history.append(row)

        self.csv.close()
        if cfg.save_model:
            torch.save({"agent": self.agent.state_dict(),
                        "obs_rms": None if self.obs_norm is None else self.obs_norm.rms.state_dict()},
                       os.path.join(self.out_dir, "model.pt"))
        return history
