# armrl: PPO for the 2-link reach arm

(alex, 2026-10-23, after splitting `train_ppo.py`)

```
train.py               entry point: python train.py --preset quick
enjoy.py               roll out a saved model
armrl/
  config.py            Config dataclass, presets, CLI (every field is a --flag)
  trainer.py           Trainer: collect() rollouts, train() loop, eval + logging
  buffer.py            RolloutBuffer: (T, N) storage, GAE, minibatch tensors
  ppo.py               PPO.update(): clipped surrogate, value loss, entropy
  agent.py             ActorCritic MLPs (separate actor and critic)
  normalize.py         running mean/std, obs normaliser, reward scaler (off)
  evaluate.py          deterministic eval on a separate env
  logger.py            CSV + console table
  callbacks.py         WIP, not wired up
  utils.py             seeding, lr schedule, misc
  envs/reach.py        the arm (numpy, vectorised)
  envs/wrappers.py     VecReach: time limit + auto reset, terminated/truncated
  envs/pickplace.py    from sam's branch, not used here
scripts/               plot_curves.py, summarize_runs.py, check_determinism.py
sweeps/                old random search (not ported), reach_v3 results
tests/                 python tests/test_buffer.py etc. (pytest works too)
runs/                  CSVs we keep; new runs land in runs/<exp>__s<seed>__<stamp>/
```

## Running

```
python train.py --preset quick --seed 1         # ~40 s, 250k steps
python train.py --preset full --seed 1          # what the group-meeting curves used
python train.py --preset quick --norm-adv false # any Config field is a flag
python scripts/plot_curves.py runs/before_refactor_s1.csv runs/reach__s1__*/progress.csv
```

`--verbose 2` prints a debug line per update.

## Conventions

- Envs are always vectorised, shape (n_envs, ...). Buffer is (n_steps, n_envs, ...).
- Actions are unsquashed Gaussian samples; the env clips. Log-probs are of the raw sample.
- Obs normalisation: updated on every collected obs, never in eval or bootstrapping.
- terminated = the arm hit the elbow limit. truncated = 100 steps. Truncated steps bootstrap
  from the critic's value of the final obs.
- Everything single-threaded on CPU (`threads=1`), so a seed reproduces exactly.

## Not done

- port sweeps/ to the new layout
- callbacks (checkpointing, early stop)
- pick-place
