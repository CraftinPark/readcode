"""Rollout storage for PPO.

Layout is (n_steps, n_envs, ...) like the old Storage tuple, flattened only
when we hand out minibatches.

dones[t, i] == 1 means the transition stored at t ended env i's episode
(terminated OR truncated). For truncated steps the trainer has already
folded gamma * V(final_obs) into rewards[t], so GAE can treat every done
the same way.
"""
import numpy as np
import torch


class RolloutBuffer:
    def __init__(self, n_steps, n_envs, obs_dim, act_dim, gamma=0.99, gae_lambda=0.95):
        self.n_steps = n_steps
        self.n_envs = n_envs
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.reset()

    def reset(self):
        T, N = self.n_steps, self.n_envs
        self.obs = np.zeros((T, N, self.obs_dim), dtype=np.float32)
        self.actions = np.zeros((T, N, self.act_dim), dtype=np.float32)
        self.logprobs = np.zeros((T, N), dtype=np.float32)
        self.rewards = np.zeros((T, N), dtype=np.float32)
        self.dones = np.zeros((T, N), dtype=np.float32)
        self.values = np.zeros((T, N), dtype=np.float32)
        self.advantages = np.zeros((T, N), dtype=np.float32)
        self.returns = np.zeros((T, N), dtype=np.float32)
        self.ptr = 0
        self.full = False

    def add(self, obs, action, logprob, reward, done, value):
        if self.ptr >= self.n_steps:
            raise RuntimeError("buffer full, call reset()")
        t = self.ptr
        self.obs[t] = obs
        self.actions[t] = action
        self.logprobs[t] = logprob
        self.rewards[t] = reward
        self.dones[t] = done
        self.values[t] = value
        self.ptr += 1
        self.full = self.ptr == self.n_steps

    def add_to_reward(self, t, idx, amount):
        """used for time-limit bootstrapping, see Trainer.collect"""
        self.rewards[t, idx] += amount

    # ------------------------------------------------------------------
    def compute_gae(self, last_value):
        """last_value: V(obs after the final stored step), shape (n_envs,)"""
        assert self.full, "compute_gae on a partial rollout"
        lastgaelam = np.zeros(self.n_envs, dtype=np.float32)
        for t in reversed(range(self.n_steps)):
            if t == self.n_steps - 1:
                next_values = last_value
            else:
                next_values = self.values[t + 1]
            nonterminal = 1.0 - self.dones[t]
            delta = self.rewards[t] + self.gamma * next_values * nonterminal - self.values[t]
            lastgaelam = delta + self.gamma * self.gae_lambda * nonterminal * lastgaelam
            self.advantages[t] = lastgaelam
        # critic targets, fixed here before anything rescales the advantages
        self.returns = self.advantages + self.values
        return self.advantages

    def compute_nstep(self, last_value):
        """Plain discounted returns, no lambda. Only for --no-gae debugging."""
        ret = np.zeros((self.n_steps, self.n_envs), dtype=np.float32)
        running = last_value.copy()
        for t in reversed(range(self.n_steps)):
            running = self.rewards[t] + self.gamma * running * (1.0 - self.dones[t])
            ret[t] = running
        self.advantages = ret - self.values
        self.returns = ret
        return self.advantages

    def normalize_advantages(self, eps=1e-8):
        adv = self.advantages
        self.advantages = (adv - adv.mean()) / (adv.std() + eps)

    # ------------------------------------------------------------------
    def flat(self):
        """Flatten (T, N) -> (T*N,) and convert to tensors once per update."""
        B = self.n_steps * self.n_envs
        return {
            "obs": torch.as_tensor(self.obs.reshape(B, self.obs_dim)),
            "actions": torch.as_tensor(self.actions.reshape(B, self.act_dim)),
            "logprobs": torch.as_tensor(self.logprobs.reshape(B)),
            "advantages": torch.as_tensor(self.advantages.reshape(B)),
            "returns": torch.as_tensor(self.returns.reshape(B)),
            "values": torch.as_tensor(self.values.reshape(B)),
        }

    def episode_stats(self):
        """rough, only counts episodes that ended inside this rollout"""
        n_done = int(self.dones.sum())
        return {"episodes_in_rollout": n_done}
