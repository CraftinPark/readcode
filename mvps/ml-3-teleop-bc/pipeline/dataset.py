"""From the demo folder to normalised train/val tensors."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from config import DataConfig, PolicyConfig
from pipeline.chunking import episode_samples, stack_samples
from pipeline.episodes import BuildReport, Frames, build_frames
from pipeline.normalize import Normalizer


def split_episodes(ids: list[int], val_fraction: float, seed: int) -> tuple[list[int], list[int]]:
    """Split by episode, never by frame: neighbouring frames are near-duplicates."""
    ids = sorted(ids)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(ids))
    n_val = max(1, int(round(val_fraction * len(ids))))
    val = sorted(ids[i] for i in perm[:n_val])
    train = sorted(ids[i] for i in perm[n_val:])
    return train, val


@dataclass
class DemoData:
    train: dict              # obs (N, h, D), act (N, k, 3), mask (N, k): torch tensors
    val: dict
    normalizer: Normalizer
    report: BuildReport
    train_ids: list
    val_ids: list

    def describe(self) -> str:
        n_tr, n_va = len(self.train["obs"]), len(self.val["obs"])
        return (f"{self.report.summary()}\n"
                f"train: {len(self.train_ids)} episodes, {n_tr} samples | "
                f"val: {len(self.val_ids)} episodes, {n_va} samples")


def _to_tensors(samples: dict, norm: Normalizer) -> dict:
    return {
        "obs": torch.from_numpy(norm.obs(samples["obs"])),
        "act": torch.from_numpy(norm.act(samples["act"])),
        "mask": torch.from_numpy(samples["mask"]),
    }


def load_demo_data(dcfg: DataConfig, pcfg: PolicyConfig,
                   frames: list[Frames] | None = None) -> DemoData:
    report = None
    if frames is None:
        frames, report = build_frames(dcfg)
    else:
        report = BuildReport([f.episode_id for f in frames], [])
    by_id = {f.episode_id: f for f in frames}
    train_ids, val_ids = split_episodes(list(by_id), dcfg.val_fraction, dcfg.split_seed)
    train_frames = [by_id[i] for i in train_ids]
    norm = Normalizer.fit(train_frames)

    def samples(ids):
        return stack_samples([episode_samples(by_id[i], pcfg.obs_horizon, pcfg.chunk) for i in ids])

    return DemoData(
        train=_to_tensors(samples(train_ids), norm),
        val=_to_tensors(samples(val_ids), norm),
        normalizer=norm, report=report, train_ids=train_ids, val_ids=val_ids,
    )
