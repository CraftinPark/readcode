"""Hyperparameters. Defaults are the reach_v3 settings from the September sweep
(sweeps/reach_v3/best.json), don't change them here without rerunning it.
"""
import argparse
import dataclasses
from dataclasses import dataclass, field


@dataclass
class Config:
    exp_name: str = "reach"
    seed: int = 1
    torch_deterministic: bool = True
    threads: int = 1

    # env
    n_envs: int = 16
    max_episode_steps: int = 100
    ctrl_cost: float = 0.02

    # rollout / ppo
    total_steps: int = 400_000
    n_steps: int = 64            # per env per rollout
    lr: float = 1e-3
    anneal_lr: bool = True
    gamma: float = 0.97
    gae_lambda: float = 0.95
    use_gae: bool = True
    n_minibatches: int = 4
    update_epochs: int = 10
    norm_adv: bool = True
    clip_coef: float = 0.2
    clip_vloss: bool = False     # off since #22, made no difference
    ent_coef: float = 0.0
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    target_kl: float = None

    # normalisation
    norm_obs: bool = True
    obs_clip: float = 5.0
    norm_reward: bool = False    # see normalize.RewardScaler docstring

    # model
    hidden: tuple = (64, 64)
    init_log_std: float = -0.5

    # eval / logging
    eval_every: int = 10         # iterations
    eval_episodes: int = 16
    log_dir: str = "runs"
    save_model: bool = False
    verbose: int = 1

    # pick-place leftovers, ignored by reach
    gripper_obs: bool = False
    contact_reward: float = 0.0

    @property
    def batch_size(self):
        return self.n_envs * self.n_steps

    @property
    def n_iterations(self):
        return self.total_steps // self.batch_size


PRESETS = {
    # ~45 s on a laptop CPU, enough to see the plateau
    "quick": dict(total_steps=250_000),
    # what the curves in runs/ were made with
    "full": dict(total_steps=400_000),
    "smoke": dict(total_steps=4096, eval_every=1, eval_episodes=4),
}


def _str2bool(v):
    if isinstance(v, bool):
        return v
    return v.lower() in ("1", "true", "yes", "y", "on")


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=sorted(PRESETS), default=None)
    for f in dataclasses.fields(Config):
        if f.name in ("hidden",):
            continue
        kw = {"default": None}
        if f.type in (bool, "bool"):
            kw["type"] = _str2bool
        elif f.type in (int, "int"):
            kw["type"] = int
        elif f.type in (float, "float"):
            kw["type"] = float
        p.add_argument("--" + f.name.replace("_", "-"), **kw)
    args = p.parse_args(argv)

    cfg = Config()
    if args.preset:
        for k, v in PRESETS[args.preset].items():
            setattr(cfg, k, v)
    for f in dataclasses.fields(Config):
        v = getattr(args, f.name, None)
        if v is not None:
            setattr(cfg, f.name, v)
    return cfg
