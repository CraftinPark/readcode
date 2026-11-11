import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armrl.normalize import ObsNormalizer, RunningMeanStd  # noqa: E402


def test_rms_matches_numpy():
    rng = np.random.default_rng(0)
    x = rng.normal(3.0, 2.0, size=(1000, 4))
    rms = RunningMeanStd(shape=(4,))
    for chunk in np.array_split(x, 7):
        rms.update(chunk)
    np.testing.assert_allclose(rms.mean, x.mean(0), rtol=1e-3)
    np.testing.assert_allclose(rms.var, x.var(0), rtol=1e-2)


def test_frozen_copy_does_not_move():
    n = ObsNormalizer(3)
    n(np.random.default_rng(1).normal(size=(50, 3)))
    c = n.copy()
    c.frozen = True
    before = c.rms.mean.copy()
    c(np.ones((10, 3)) * 100)
    np.testing.assert_array_equal(c.rms.mean, before)
    # and the original is untouched by the copy
    np.testing.assert_array_equal(n.rms.mean, before)


def test_clip():
    n = ObsNormalizer(1, clip=5.0)
    n(np.zeros((100, 1)))
    out = n(np.array([[1e6]]), update=False)
    assert out[0, 0] == 5.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
