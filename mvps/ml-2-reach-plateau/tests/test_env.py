import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armrl.envs.reach import ReachArm, forward_kinematics, L1, L2  # noqa: E402
from armrl.envs.wrappers import VecReach  # noqa: E402


def test_fk_straight_arm():
    _, ee = forward_kinematics(np.zeros((1, 2)))
    np.testing.assert_allclose(ee[0], [L1 + L2, 0.0])


def test_obs_layout():
    arm = ReachArm(4, seed=0)
    o = arm.reset()
    assert o.shape == (4, 10)
    np.testing.assert_allclose(o[:, 0], np.cos(arm.q[:, 0]), atol=1e-6)
    np.testing.assert_allclose(o[:, 1], np.sin(arm.q[:, 0]), atol=1e-6)
    np.testing.assert_allclose(o[:, 6:8], arm.target, atol=1e-6)


def test_time_limit_truncates_and_resets():
    env = VecReach(3, max_steps=5, seed=0)
    env.reset()
    for k in range(5):
        obs, r, term, trunc, info = env.step(np.zeros((3, 2)))
    assert trunc.all() and not term.any()
    assert info["final_obs"].shape == (3, 10)
    assert (env.t == 0).all()
    # the returned obs is the new episode's first obs, final_obs is the old one
    assert not np.allclose(obs, info["final_obs"])


def test_elbow_limit_terminates():
    env = VecReach(1, max_steps=500, seed=0)
    env.reset()
    env.arm.q[0, 1] = 2.58
    _, _, term, trunc, _ = env.step(np.array([[0.0, 1.0]]))
    assert term[0] and not trunc[0]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
