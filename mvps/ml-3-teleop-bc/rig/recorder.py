"""Teleop recorder (rig v2).

Rig v1 recorded inside the 50 Hz control loop: every row held the leader
command, the follower state and the most recent camera detection, stamped once.
That tied the camera to the control rate and dropped frames whenever the loop
overran, so v2 records asynchronously: every device has its own writer thread
that stamps each sample with the host monotonic clock (`time.monotonic_ns()`,
shared by all threads) the moment it arrives, and writes its own stream file.

Episode layout on disk::

    ep_0042/
      meta.json      episode id, operator, session start, task, rig version
      leader.npz     t_ns int64 (N,), pos float32 (N, 2), grip uint8 (N,)
      follower.npz   t_ns int64 (N,), pos float32 (N, 2), grip float32 (N,)
      camera.npz     t_ns int64 (N,), block float32 (N, 2), detected bool (N,)

Devices on cell 2:

- leader: the operator's leader arm, read by the teleop node at 50 Hz. `pos` is
  the leader's end-effector position mapped to the table plane, i.e. the
  position target sent to the follower. `grip` is the trigger, 1 = close.
  The teleop node only forwards the leader while the deadman pedal is held.
- follower: the follower arm driver at 100 Hz. `pos` is the measured
  end-effector position, `grip` the measured jaw position (0 open, 1 closed).
- camera: the overhead camera, ~30 Hz, run through the block detector.
  `detected` is False when the detector found nothing; `block` is NaN there.

`meta.json["start_ns"]` is the host clock when the operator pressed "record".
Every writer thread is started at that moment; each stream begins with that
device's first sample.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field

import numpy as np

RIG_VERSION = "2.1"

STREAM_FIELDS = {
    "leader": {"pos": (np.float32, 2), "grip": (np.uint8, 0)},
    "follower": {"pos": (np.float32, 2), "grip": (np.float32, 0)},
    "camera": {"block": (np.float32, 2), "detected": (np.bool_, 0)},
}


@dataclass
class StreamWriter:
    """Buffers one device's samples; `flush` writes `<name>.npz`."""

    name: str
    t_ns: list = field(default_factory=list)
    cols: dict = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, t_ns: int, **values) -> None:
        spec = STREAM_FIELDS[self.name]
        if set(values) != set(spec):
            raise ValueError(f"{self.name}: expected fields {sorted(spec)}, got {sorted(values)}")
        with self.lock:
            self.t_ns.append(int(t_ns))
            for k, v in values.items():
                self.cols.setdefault(k, []).append(v)

    def flush(self, ep_dir: str) -> str:
        spec = STREAM_FIELDS[self.name]
        with self.lock:
            out = {"t_ns": np.asarray(self.t_ns, dtype=np.int64)}
            for k, (dtype, width) in spec.items():
                arr = np.asarray(self.cols.get(k, []), dtype=dtype)
                if width and arr.size == 0:
                    arr = arr.reshape(0, width)
                out[k] = arr
        path = os.path.join(ep_dir, f"{self.name}.npz")
        np.savez_compressed(path, **out)
        return path


class EpisodeRecorder:
    """One recording session. The rig's device threads call `writer(name).append(...)`."""

    def __init__(self, root: str, episode_id: int, operator: str, task: dict,
                 clock=time.monotonic_ns):
        self.root = root
        self.episode_id = episode_id
        self.operator = operator
        self.task = task
        self.clock = clock
        self.start_ns: int | None = None
        self.writers = {name: StreamWriter(name) for name in STREAM_FIELDS}

    @property
    def ep_dir(self) -> str:
        return os.path.join(self.root, f"ep_{self.episode_id:04d}")

    def start(self, start_ns: int | None = None) -> None:
        self.start_ns = int(self.clock() if start_ns is None else start_ns)

    def writer(self, name: str) -> StreamWriter:
        return self.writers[name]

    def finish(self, notes: str = "") -> str:
        if self.start_ns is None:
            raise RuntimeError("finish() before start()")
        os.makedirs(self.ep_dir, exist_ok=True)
        for w in self.writers.values():
            w.flush(self.ep_dir)
        meta = {
            "episode_id": self.episode_id,
            "operator": self.operator,
            "rig_version": RIG_VERSION,
            "start_ns": self.start_ns,
            "task": self.task,
            "streams": {n: len(w.t_ns) for n, w in self.writers.items()},
            "notes": notes,
        }
        with open(os.path.join(self.ep_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        return self.ep_dir
