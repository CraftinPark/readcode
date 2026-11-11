"""Every knob of the pipeline, trainer and bench evaluation in one place."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# Observation and action layouts at the policy rate.
OBS_FIELDS = ("ee_x", "ee_y", "jaw", "block_x", "block_y", "bin_x", "bin_y")
ACT_FIELDS = ("target_x", "target_y", "grip")
GRIP = ACT_FIELDS.index("grip")


@dataclass
class DataConfig:
    root: str = "data/demos"
    policy_hz: float = 10.0
    # quality gates (an episode failing any of them is skipped, with a reason)
    max_gap_s: dict = field(default_factory=lambda: {"leader": 0.06, "follower": 0.03, "camera": 0.25})
    min_detected: float = 0.8        # fraction of camera frames with a detection
    min_window_s: float = 4.0        # overlap of all streams
    max_camera_age_s: float = 0.2    # a grid point further than this from a detection is not used
    # trimming of the static tail after the operator lets go of the pedal
    idle_eps: float = 0.002          # metres
    tail_keep: int = 3
    val_fraction: float = 0.1
    split_seed: int = 7


@dataclass
class PolicyConfig:
    obs_horizon: int = 2             # current + previous policy step
    chunk: int = 10                  # actions predicted per query (1 s at 10 Hz)
    hidden: int = 256
    layers: int = 3


@dataclass
class TrainConfig:
    steps: int = 3000
    batch_size: int = 256
    lr: float = 1e-3
    weight_decay: float = 1e-4
    warmup: int = 100
    grip_weight: float = 0.5         # BCE weight next to the L1 position loss
    log_every: int = 250
    seed: int = 0
    out: str = "runs/latest.pt"


@dataclass
class EvalConfig:
    episodes: int = 50
    seed: int = 900_000
    time_limit_s: float = 20.0
    ensemble_m: float = 0.1          # temporal-ensembling decay (ACT's m)
    grip_threshold: float = 0.5


def to_dict(*cfgs) -> dict:
    return {type(c).__name__: asdict(c) for c in cfgs}
