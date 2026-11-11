"""python -m pytest tests  (or just python tests/test_buffer.py)"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armrl.buffer import RolloutBuffer  # noqa: E402


def naive_gae(rewards, values, dones, last_value, gamma, lam):
    """one env, written the slow obvious way"""
    T = len(rewards)
    adv = np.zeros(T)
    for t in range(T):
        a = 0.0
        coef = 1.0
        for k in range(t, T):
            v_next = values[k + 1] if k + 1 < T else last_value
            delta = rewards[k] + gamma * v_next * (1 - dones[k]) - values[k]
            a += coef * delta
            if dones[k]:
                break
            coef *= gamma * lam
        adv[t] = a
    return adv


def _filled(T=12, N=3, seed=0):
    rng = np.random.default_rng(seed)
    buf = RolloutBuffer(T, N, obs_dim=2, act_dim=1, gamma=0.9, gae_lambda=0.8)
    dones = (rng.random((T, N)) < 0.2).astype(np.float32)
    for t in range(T):
        buf.add(rng.normal(size=(N, 2)), rng.normal(size=(N, 1)), rng.normal(size=N),
                rng.normal(size=N), dones[t], rng.normal(size=N))
    last_value = rng.normal(size=N).astype(np.float32)
    return buf, last_value


def test_gae_matches_naive():
    buf, last_value = _filled()
    adv = buf.compute_gae(last_value)
    for i in range(buf.n_envs):
        ref = naive_gae(buf.rewards[:, i], buf.values[:, i], buf.dones[:, i], last_value[i], 0.9, 0.8)
        np.testing.assert_allclose(adv[:, i], ref, rtol=1e-5, atol=1e-5)


def test_returns_are_lambda_returns():
    buf, last_value = _filled(seed=1)
    buf.compute_gae(last_value)
    np.testing.assert_allclose(buf.returns, buf.advantages + buf.values)


def test_lambda_one_is_monte_carlo():
    buf, last_value = _filled(seed=2)
    buf.gae_lambda = 1.0
    buf.compute_gae(last_value)
    i = 0
    run = last_value[i]
    for t in reversed(range(buf.n_steps)):
        run = buf.rewards[t, i] + buf.gamma * run * (1 - buf.dones[t, i])
        assert abs(buf.returns[t, i] - run) < 1e-4


def test_normalize_advantages():
    buf, last_value = _filled(seed=3)
    buf.compute_gae(last_value)
    buf.normalize_advantages()
    assert abs(buf.advantages.mean()) < 1e-5
    assert abs(buf.advantages.std() - 1.0) < 1e-3


def test_add_overflow():
    buf, _ = _filled()
    try:
        buf.add(np.zeros((3, 2)), np.zeros((3, 1)), np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3))
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
