# ML-3: Cell 2 grabs air

*ReadCode problem, Tier 1.5 (AI tools allowed; large codebase; no hint where to look). Tailored to the **Robot Learning Engineer** posting in [posting.md](posting.md); how the posting picked this problem is in [tailoring.md](tailoring.md). AI-written MVP: an experiment, not shipped content.*

**Suggested time:** 60 minutes (about 40 for the Code tab, 20 for the Comprehension tab).

## The ticket

> **From:** Robot lab, cell 2 · **Priority:** P1
>
> First policy trained on the new cell-2 pick-and-place demos (150 teleop episodes, rig v2 recorder, three operators). Training looked normal and the loss curves are boring. On the arm it is quick, but it keeps shutting the gripper before it gets to the block: the jaws close on air, sometimes shove the block a few centimetres, then it reopens and tries again. About half the trials need more than one attempt and a good share never finish. The operators say they never close that early.
>
> The bench twin shows the same thing with the shipped code:
>
> `success 62% over 50 episodes | first try 46% | mean time to success 3.9s | missed grasps/ep 2.28`
>
> We need this policy on the cell next week. Find what is wrong and fix it.

## What's here

```
posting.md, tailoring.md   the job posting and how it was turned into this problem
rig/recorder.py            the rig v2 recorder: the on-disk episode format
data/demos/                the 150 recorded episodes (do not edit)
config.py                  every knob
pipeline/                  io (loading), sync (resampling), episodes (alignment + quality gates),
                           chunking, normalize, dataset (split + tensors)
policy/                    model (chunk MLP + loss), train, ensemble (temporal ensembling), runner (robot side)
sim/env.py                 the bench twin of cell 2 (the bench: do not edit)
train.py, evaluate.py      build data + train (~15-30 s on a laptop CPU); closed-loop bench eval (~5 s)
tools/inspect_episode.py   per-episode stream stats and aligned frames
tests/test_smoke.py        visible smoke test (it checks that things run, not that they are right)
comprehension.json         the Comprehension tab
```

Python 3.10+ with numpy and torch (CPU).

```
python tests/test_smoke.py
python train.py
python evaluate.py            # add -v for per-episode results
python tools/inspect_episode.py 12
```

## Code tab: fix it

Change whatever you need in `pipeline/`, `policy/`, `train.py` or `config.py`. Graded by hidden tests:

- your pipeline is run on recordings you have not seen, and must produce correct training data from them;
- things that already work must keep working (quality gates, chunking, ensembling, normalisation);
- `python train.py` then `python evaluate.py` on the shipped demos must reach **success >= 85% and first try >= 70%** on the bench.

Rules: keep these interfaces, the hidden tests call them: `pipeline.io.load_episode(ep_dir)`, `pipeline.episodes.align_episode(episode, DataConfig)` (returns `Frames`), `pipeline.episodes.build_frames`, `train.py --out PATH`, `evaluate.py --ckpt PATH --json`. Don't edit `sim/`, `evaluate.py`, `data/` or the bench settings in `EvalConfig` (time limit, seed, episode count).

## Comprehension tab

Seven multiple-choice questions in `comprehension.json` about this codebase as shipped. They don't ask about the fix. Answer as a JSON object: `{"Q1": "B", "Q2": "...", ...}`.
