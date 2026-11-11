"""Smoke test: the pipeline runs end to end and produces sane shapes.

    python tests/test_smoke.py        (or: pytest tests)

It checks that things run, not that the policy is any good.
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import ACT_FIELDS, OBS_FIELDS, DataConfig, EvalConfig, PolicyConfig, TrainConfig  # noqa: E402

DEMOS = os.path.join(ROOT, "data", "demos")


def test_load_and_align_one_episode():
    from pipeline.episodes import align_episode
    from pipeline.io import list_episodes, load_episode
    ep = load_episode(list_episodes(DEMOS)[0])
    assert set(ep.streams) == {"leader", "follower", "camera"}
    for s in ep.streams.values():
        assert np.all(np.diff(s.t) > 0)
    fr = align_episode(ep, DataConfig(root=DEMOS))
    assert fr.obs.shape == (len(fr), len(OBS_FIELDS))
    assert fr.act.shape == (len(fr), len(ACT_FIELDS))
    assert np.isfinite(fr.obs).all() and np.isfinite(fr.act).all()
    assert set(np.unique(fr.act[:, 2])) <= {0.0, 1.0}
    assert np.allclose(np.diff(fr.t), 0.1)


def test_dataset_build():
    from pipeline.dataset import load_demo_data
    data = load_demo_data(DataConfig(root=DEMOS), PolicyConfig())
    assert len(data.train_ids) > 100 and len(data.val_ids) > 5
    assert not set(data.train_ids) & set(data.val_ids)
    assert data.train["obs"].shape[1:] == (PolicyConfig.obs_horizon, len(OBS_FIELDS))
    assert data.train["act"].shape[1:] == (PolicyConfig.chunk, len(ACT_FIELDS))


def test_short_training_and_rollout():
    from evaluate import rollout
    from pipeline.dataset import load_demo_data
    from policy.runner import PolicyRunner
    from policy.train import save_checkpoint, train
    dcfg, pcfg = DataConfig(root=DEMOS), PolicyConfig()
    tcfg = TrainConfig(steps=60, log_every=30)
    data = load_demo_data(dcfg, pcfg)
    model, info = train(data, pcfg, tcfg, dcfg, verbose=False)
    assert np.isfinite(info["history"][-1]["val"])
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "smoke.pt")
        save_checkpoint(path, model, data, pcfg, tcfg, dcfg, info)
        runner = PolicyRunner.load(path, EvalConfig(time_limit_s=2.0))
    r = rollout(runner, seed=1, ecfg=EvalConfig(time_limit_s=2.0))
    assert r.seconds > 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("smoke test passed")
