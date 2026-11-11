"""Hidden autograder for the Code tab (key only).

Run against a solver's folder with `python _key/check_key.py --solution DIR`
(or `SOLUTION_DIR=DIR pytest _key/hidden_tests`). Plain asserts, no fixtures,
so it also runs without pytest.

What it checks:
- alignment: synthetic rig v2 episodes whose streams start at different
  moments; every signal is a known function of absolute time, so each aligned
  frame can be checked for whether its observation and action come from the
  same instant, whatever time origin or grid the solver chose;
- guards: behaviour that was already right must stay right (quality gates,
  gripper hold, chunk padding, ensembling, normalisation);
- closed loop: the full train.py + evaluate.py on the shipped demos must reach
  the bench bar.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import numpy as np

SOLUTION = os.path.abspath(os.environ.get("SOLUTION_DIR", os.getcwd()))
if SOLUTION not in sys.path:
    sys.path.insert(0, SOLUTION)

PRISTINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
START_NS = 51_234_567_000_000
DUR = 6.0
TOL_S = 0.006          # 6 ms: well under one 30 Hz camera period


# --------------------------------------------------------------------- helpers
def _write_episode(root: str, ep_id: int, starts: dict, ends: dict, grip_at: float = 2.5) -> str:
    """A rig v2 episode where every signal is a linear function of absolute time tau (s)."""
    d = os.path.join(root, f"ep_{ep_id:04d}")
    os.makedirs(d)
    rng = np.random.default_rng(ep_id)

    def stamps(name, hz, jitter):
        n = int(np.floor((ends[name] - starts[name]) * hz)) + 1
        tau = starts[name] + np.arange(n) / hz + rng.normal(0, jitter, n)
        tau = np.sort(tau)
        tau[0] = starts[name]
        return tau, START_NS + np.round(tau * 1e9).astype(np.int64)

    tau, t_ns = stamps("leader", 50.0, 0.0005)
    pos = np.column_stack([0.30 + 0.04 * tau, np.full_like(tau, 0.25)]).astype(np.float32)
    grip = (tau >= grip_at).astype(np.uint8)
    np.savez_compressed(os.path.join(d, "leader.npz"), t_ns=t_ns, pos=pos, grip=grip)

    tau, t_ns = stamps("follower", 100.0, 0.0002)
    pos = np.column_stack([0.05 + 0.03 * tau, np.full_like(tau, 0.2)]).astype(np.float32)
    np.savez_compressed(os.path.join(d, "follower.npz"), t_ns=t_ns, pos=pos,
                        grip=np.zeros(len(tau), np.float32))

    tau, t_ns = stamps("camera", 30.0, 0.001)
    block = np.column_stack([0.10 + 0.02 * tau, np.full_like(tau, 0.1)]).astype(np.float32)
    np.savez_compressed(os.path.join(d, "camera.npz"), t_ns=t_ns, block=block,
                        detected=np.ones(len(tau), bool))

    meta = {"episode_id": ep_id, "operator": "test", "rig_version": "2.1", "start_ns": START_NS,
            "task": {"bin_xy": [0.3, 0.3], "cell": "cell-2"},
            "streams": {}, "notes": ""}
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f)
    return d


def _check_alignment(starts: dict, ends: dict | None = None) -> None:
    from config import DataConfig
    from pipeline.episodes import align_episode
    from pipeline.io import load_episode

    ends = ends or {k: v + DUR for k, v in starts.items()}
    with tempfile.TemporaryDirectory() as tmp:
        fr = align_episode(load_episode(_write_episode(tmp, 1, starts, ends)), DataConfig(root=tmp))
    obs, act = np.asarray(fr.obs, np.float64), np.asarray(fr.act, np.float64)
    assert len(obs) >= 40, f"only {len(obs)} frames"
    tau_follower = (obs[:, 0] - 0.05) / 0.03
    tau_camera = (obs[:, 3] - 0.10) / 0.02
    tau_leader = (act[:, 0] - 0.30) / 0.04
    worst_cam = float(np.max(np.abs(tau_camera - tau_follower)))
    worst_act = float(np.max(np.abs(tau_leader - tau_follower)))
    assert worst_cam < TOL_S, f"camera vs follower off by up to {worst_cam * 1000:.0f} ms (starts {starts})"
    assert worst_act < TOL_S, f"action vs observation off by up to {worst_act * 1000:.0f} ms (starts {starts})"
    lo, hi = max(starts.values()), min(ends.values())
    assert tau_follower.min() >= lo - TOL_S and tau_follower.max() <= hi + TOL_S, \
        "frames outside the window where every stream has data"
    spacing = np.diff(tau_follower)
    assert np.allclose(spacing, 0.1, atol=TOL_S), "frames are not 0.1 s apart"
    g = act[:, 2]
    assert np.all(g[tau_follower > 2.53] == 1) and np.all(g[tau_follower < 2.5 - TOL_S] == 0), \
        "gripper command not held from the moment it was sent"


# ------------------------------------------------------------------ alignment
def test_alignment_streams_start_together():
    _check_alignment({"leader": 0.0, "follower": 0.0, "camera": 0.0})


def test_alignment_leader_starts_late():
    _check_alignment({"leader": 0.62, "follower": 0.01, "camera": 0.04})


def test_alignment_follower_starts_late():
    _check_alignment({"leader": 0.0, "follower": 0.47, "camera": 0.02})


def test_alignment_camera_starts_late():
    _check_alignment({"leader": 0.03, "follower": 0.0, "camera": 0.33})


def test_alignment_leader_late_and_ends_early():
    _check_alignment({"leader": 0.85, "follower": 0.005, "camera": 0.03},
                     {"leader": 6.2, "follower": 7.1, "camera": 7.05})


# --------------------------------------------------------------------- guards
def test_guard_quality_gates_on_shipped_demos():
    from config import DataConfig
    from pipeline.episodes import build_frames
    _, report = build_frames(DataConfig(root=os.path.join(SOLUTION, "data", "demos")))
    rejected = sorted(eid for eid, _ in report.rejected)
    assert rejected == [17, 45, 64, 101, 108, 122, 133], f"rejected episodes changed: {rejected}"


def test_guard_hold_last_and_chunks():
    from pipeline import sync
    from pipeline.chunking import action_chunks, obs_history
    t = np.array([0.0, 1.0, 2.0])
    assert sync.hold_last(t, np.array([0, 1, 0]), np.array([0.5, 1.0, 1.99, 2.5])).tolist() == [0, 1, 1, 0]
    a = np.arange(12, dtype=np.float32).reshape(4, 3)
    chunks, mask = action_chunks(a, 3)
    assert chunks.shape == (4, 3, 3) and mask[3].tolist() == [True, False, False]
    assert np.array_equal(chunks[3, 2], a[3]) and np.array_equal(chunks[1, 1], a[2])
    h = obs_history(a, 2)
    assert np.array_equal(h[0, 0], a[0]) and np.array_equal(h[2, 0], a[1]) and np.array_equal(h[2, 1], a[2])


def test_guard_ensembler():
    from policy.ensemble import TemporalEnsembler
    e = TemporalEnsembler(chunk=3, m=0.5)
    e.add(np.array([[0.0, 0], [1, 1], [2, 2]]), np.array([0.0, 0.0, 0.0]))
    p0, _ = e.current()
    e.add(np.array([[10.0, 10], [11, 11], [12, 12]]), np.array([1.0, 1.0, 1.0]))
    p1, g1 = e.current()
    w = np.exp(-0.5 * np.arange(2)); w /= w.sum()
    assert np.allclose(p0, [0, 0])
    assert np.allclose(p1, w[0] * 1 + w[1] * 10), p1
    assert abs(g1 - w[1]) < 1e-9


def test_guard_normalizer_keeps_gripper_binary():
    from pipeline.episodes import Frames
    from pipeline.normalize import Normalizer
    rng = np.random.default_rng(0)
    fr = Frames(0, np.arange(50) / 10, rng.normal(size=(50, 7)).astype(np.float32),
                np.column_stack([rng.normal(3, 2, (50, 2)), rng.integers(0, 2, 50)]).astype(np.float32),
                np.ones(50, bool))
    n = Normalizer.fit([fr])
    out = n.act(fr.act)
    assert np.array_equal(out[:, 2], fr.act[:, 2])
    assert abs(out[:, 0].mean()) < 1e-4 and abs(out[:, 0].std() - 1) < 1e-3


def test_guard_bench_untouched():
    def norm(path):
        with open(path, "rb") as f:
            return f.read().replace(b"\r\n", b"\n")
    for rel in ("sim/env.py", "evaluate.py"):
        assert norm(os.path.join(SOLUTION, rel)) == norm(os.path.join(PRISTINE, rel)), f"{rel} was modified"
    from config import EvalConfig
    e = EvalConfig()
    assert (e.time_limit_s, e.seed, e.episodes) == (20.0, 900_000, 50), "bench settings in config.py were changed"


# ---------------------------------------------------------------- closed loop
def test_closed_loop_bench():
    if os.environ.get("SKIP_CLOSED_LOOP"):
        return
    with tempfile.TemporaryDirectory() as tmp:
        ck = os.path.join(tmp, "policy.pt")
        r = subprocess.run([sys.executable, "train.py", "--out", ck], cwd=SOLUTION,
                           capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
        r = subprocess.run([sys.executable, "evaluate.py", "--ckpt", ck, "--episodes", "50", "--json"],
                           cwd=SOLUTION, capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
        summary = json.loads(r.stdout[r.stdout.index("{"):])
    assert summary["success_rate"] >= 0.85 and summary["first_try_rate"] >= 0.70, \
        f"bench: success {summary['success_rate']:.0%}, first try {summary['first_try_rate']:.0%}"
