# ml-2 key: reach_v3 after the refactor (SPOILERS)

*Tier 1 RL problem, stage notice / define. AI-written MVP: an experiment, not shipped content.*

## The cause

`armrl/buffer.py`, the `returns` property (shipped lines 80-84):

```python
@property
def returns(self):
    # targets for the critic. GAE gives A = R_lambda - V, so we don't
    # keep a second (T, N) array around and risk it going stale
    return self.advantages + self.values
```

In the refactor Alex (a) stopped storing the critic targets and derived them from `advantages + values`, and (b) moved advantage normalisation from per-minibatch (on a copy) to once per batch, in the buffer (`PPO.update` -> `buf.normalize_advantages()`, which replaces `self.advantages`). Each change is fine alone. Together, `buf.flat()` (called after normalising) reads `returns = normalised_adv + V_old`. The critic is regressed onto its own old values plus a mean-0, std-1 term.

Why that hurts:
- Nothing anchors the critic to the real returns. Its level only drifts (the batch mean of the normalised advantage is 0), so it never learns that a reaching state is worth ~40 more than a far one, and GAE advantages are mostly noise from a garbage baseline.
- When the drift takes values below zero, the elbow limit (termination, future = 0) beats the bootstrapped future. The shipped agent learns to slam the elbow: `train/hit_rate` 0.6-0.98 in `runs/after_refactor_s1/progress.csv` (the baseline's is ~0).
- `explained_var` stays ~0.95, because it's measured against the same wrong targets. The log says the critic is fine.

Clues a player can use: `--norm-adv false` brings most of the performance back (54.8 vs 60.9 baseline mean); `--verbose 2` prints `ret` equal to `v` every update; `hit_rate` in the CSV; the stale `test_returns_are_lambda_returns` only checks before normalising.

Fix (`baseline/armrl/buffer.py`): store `self.returns = self.advantages + self.values` at the end of `compute_gae` (and `ret` in `compute_nstep`) and drop the property. That is the only difference between `baseline/` and the shipped code.

## Accepted locations (graded within 3 lines, span at most 15)

Anything in the chain counts, the question checks understanding:

| Site | Lines (shipped) |
|---|---|
| `returns` property (primary) | buffer.py 80-84 |
| `normalize_advantages` | buffer.py 86-88 |
| `flat()` reading `returns` | buffer.py 99 |
| the `norm_adv` call in `PPO.update` | ppo.py 26-28 |

Answers: q1 **b**, q2 **a**, q3 **a**. Distractors:
- q1 a = truncation bootstrap misread as double counting; c = unclipped-action misread; d = "batch vs minibatch normalisation is the bug" (right place, wrong reason); e = eval/no-bug story.
- q2 b = normalise returns too (still unanchored); c = only subtract the mean (targets still shift by mean(A) every update); d = copy in `normalize_advantages` (it already rebinds; the property reads the new array anyway); e = clip the stored action (red-herring fix).
- q3 checks the truncation code beyond the bug: a is right (bootstrap in the reward, `dones = 1` masks the next stored value, which is the reset episode's); b, c, d are the three usual misreads.

## Red herrings (all correct or harmless)

1. **Time-limit bootstrapping** (`trainer.py` `collect`): `gamma * V(final_obs)` added to the reward of truncated steps, with `done = 1`. Looks like double counting or like truncation treated as termination; it's the standard SB3 trick and correct.
2. **Unclipped action stored** (`trainer.py`, comment above `env.step`): log-prob of the raw Gaussian sample, the env clips. Correct for an unsquashed Gaussian.
3. **Eval normaliser** (`evaluate.py`): frozen copy, separate env seed. Correct, and doesn't touch training.
4. **LR schedule** `1 - (it - 1) / n` with 1-based `it`: correct.
5. **Obs clip 10 -> 5**, **separate eval env**, **CSV logger**: refactor changes in the CHANGELOG that do nothing to learning.
6. Mess on purpose: stale docstrings (`--no-gae` flag that doesn't exist; sweep script "not ported" but calling `train.py`), unused `clip_vloss`, `callbacks.py` not wired, `pickplace.py` from another branch, `discount_cumsum` unused, a commented print, `--verbose 2` debug print, the normaliser updated twice on the obs at each rollout boundary (harmless), `evaluate` computing `final_dist` with an odd `and`, `enjoy.py` printing distance after the reset.

## Verified (2026-10-29, Python 3.14, numpy 2.4.3, torch 2.10 CPU)

`python _key/verify.py` (quick preset, 250k steps, seeds 1-5; final eval return = mean of last 3 evals):

| Variant | s1 | s2 | s3 | s4 | s5 | mean |
|---|---|---|---|---|---|---|
| baseline | 55.1 | 65.1 | 60.2 | 59.1 | 65.0 | 60.9 |
| shipped | 20.7 | 22.0 | 14.6 | 28.1 | 24.0 | 21.9 |
| shipped `--norm-adv false` | 39.5 | 61.3 | 51.5 | 54.3 | 67.2 | 54.8 |

Shipped is 64% below baseline; worst baseline seed beats best shipped seed by 27. Runs are deterministic per seed (`scripts/check_determinism.py`). The ticket curves: `runs/before_refactor_s1.csv` is the baseline at the full preset (400k), seed 1, rewritten as a tensorboard export (eval return only); `runs/after_refactor_s1/` is the shipped code, same preset and seed (ends ~7, peaks ~22, hit rate up to 0.98).

`python _key/check_key.py --self-test`: reference answers pass (at the property and at the ppo.py call site); the batch-norm misread, truncation herring, clipped-action herring, eval/no-bug story, whole-file selection and copy-fix misread all fail.

## Not verified

- No human solve, no AI gate run. Expected difficulty is a guess: an RL engineer who knows the CleanRL ordering (returns computed before advantages are normalised) may spot it in 15 minutes; the `--norm-adv false` experiment narrows it fast for anyone who thinks to toggle refactor-touched flags.
- The ticket says ~30% lower in the brief; the real effect is larger (64% on the quick preset, collapse at 400k for seed 1), so the ticket describes the curves as they are.
- One quick run takes ~30-45 s on an idle core; on a loaded machine it took 80 s.
- The pre-refactor single file in the CHANGELOG story is fiction; the "before" curve comes from the baseline.
