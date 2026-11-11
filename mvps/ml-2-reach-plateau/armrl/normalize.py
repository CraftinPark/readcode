import numpy as np


class RunningMeanStd:
    """Parallel (Chan et al.) running mean / var. Same as everyone's."""

    def __init__(self, shape=(), epsilon=1e-4):
        self.mean = np.zeros(shape, dtype=np.float64)
        self.var = np.ones(shape, dtype=np.float64)
        self.count = epsilon

    def update(self, x):
        x = np.asarray(x, dtype=np.float64)
        batch_mean = x.mean(axis=0)
        batch_var = x.var(axis=0)
        batch_count = x.shape[0]
        self._update_from_moments(batch_mean, batch_var, batch_count)

    def _update_from_moments(self, batch_mean, batch_var, batch_count):
        delta = batch_mean - self.mean
        tot = self.count + batch_count
        new_mean = self.mean + delta * batch_count / tot
        m_a = self.var * self.count
        m_b = batch_var * batch_count
        m2 = m_a + m_b + delta ** 2 * self.count * batch_count / tot
        self.mean = new_mean
        self.var = m2 / tot
        self.count = tot

    def state_dict(self):
        return {"mean": self.mean.copy(), "var": self.var.copy(), "count": self.count}

    def load_state_dict(self, d):
        self.mean = np.array(d["mean"], dtype=np.float64)
        self.var = np.array(d["var"], dtype=np.float64)
        self.count = float(d["count"])


class ObsNormalizer:
    def __init__(self, dim, clip=5.0, eps=1e-8):
        self.rms = RunningMeanStd(shape=(dim,))
        self.clip = clip
        self.eps = eps
        self.frozen = False

    def __call__(self, obs, update=True):
        if update and not self.frozen:
            self.rms.update(obs)
        out = (obs - self.rms.mean) / np.sqrt(self.rms.var + self.eps)
        # clip was 10 before the refactor; 5 is what the old tf code used
        return np.clip(out, -self.clip, self.clip).astype(np.float32)

    def copy(self):
        o = ObsNormalizer(self.rms.mean.shape[0], clip=self.clip, eps=self.eps)
        o.rms.load_state_dict(self.rms.state_dict())
        o.frozen = self.frozen
        return o


class RewardScaler:
    """Divide rewards by the running std of the discounted return.

    Not used by default (cfg.norm_reward=False), it made reach worse in
    September's sweep. Kept because the pick-place branch uses it.
    """

    def __init__(self, n_envs, gamma, eps=1e-8):
        self.rms = RunningMeanStd(shape=())
        self.ret = np.zeros(n_envs)
        self.gamma = gamma
        self.eps = eps

    def __call__(self, rew, done):
        self.ret = self.ret * self.gamma + rew
        self.rms.update(self.ret)
        self.ret[done] = 0.0
        return rew / np.sqrt(self.rms.var + self.eps)
