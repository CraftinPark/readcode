# ML field guide: the wild animals, ranked

ReadCode ML track · field research sprint, 2026-10-24 · first version

The question: which real failures do ML, computer-vision, RL and robot-learning engineers actually meet, how often, and which would make the most authentic problems? Five kinds of evidence, each in this folder:

| Evidence | What | File |
|---|---|---|
| Job postings | 1,186 ML engineering roles from 63 companies' public job boards (AI labs, ML infra, robotics, autonomy, applied ML) | [postings.md](postings.md), `roles.json` |
| Interview reports | What ML debugging rounds look like (OpenAI, Anthropic, startups, take-homes) | [interviews.md](interviews.md) |
| Expert playbooks | Google Tuning Playbook, Karpathy's recipe, Andy Jones on RL debugging, UvA PyTorch guide, JAX Sharp Bits, 37 PPO details | [playbooks.md](playbooks.md) |
| Bug studies | Humbatova et al. 2019 (taxonomy of real DL faults), Islam et al. FSE 2019 (DL bug characteristics) | [playbooks.md](playbooks.md) |
| Real fixed bugs | 1,045 recent closed issues with a fix PR from 16 repos (RL, robot learning, vision, training frameworks, JAX) | [issues.md](issues.md), `issues.json` |

## Five findings first

1. **Postings name skills, not failures.** Evaluation (58% of roles), inference/latency (48%), experimentation (39%) and production monitoring (38%) are everywhere; specific failures (NaNs, leakage, drift, OOMs) appear in 1-5% of postings. So which failures matter has to come from bugs, playbooks and interviews, not job ads.
2. **The ML debugging round is real.** Frontier labs (OpenAI reported in several sources) and startups run an hour-long round: a training loop or transformer with planted bugs, then an extension (e.g. a KV cache). Take-homes give a NaN-producing training script to fix. This is the format ReadCode fits best.
3. **What breaks in real ML code is mostly not "the math".** In the fixed issues, the largest classes are geometry and coordinate conventions in augmentation, devices and distributed training, checkpoint save/load/resume, and **settings that are silently ignored**, ahead of RL-specific and numerical bugs.
4. **The experts agree on a short list of silent killers**: preprocessing that doesn't match the checkpoint, labels not transformed with the image, train/eval mode, losses on probabilities, `view` vs `permute`, state not reset between episodes, statistics that aren't synchronised or merged correctly, and "improvements" that are only noise.
5. **The wildest animals give no error.** Silently ignored settings, stale state after resets, wrong statistics and misleading evaluation all *train fine*: the symptom is "a bit worse" or "fine in sim, bad on the robot". That is what separates experienced engineers, and what tame puzzles never show.

## The ranked field guide

Rank combines: how often it appears in real fixed issues, how many expert sources name it, whether interviews probe it, which role families meet it (from postings), and how "wild" it is (silent, symptom far from cause). The question is what a practitioner asks while stuck.

| # | Failure class | Real fixed issues (n = 1,045) | Experts | Interviews | Who meets it | The question people ask |
|---|---|---|---|---|---|---|
| 1 | **Quiet training-loop bugs**: softmax before a loss on logits, missing `zero_grad`, model left in eval mode, loss on probabilities, labels shuffled apart from inputs, graph built during validation | few (user code, not libraries) | UvA, Karpathy, PyCon talk | **yes, the core of debugging rounds** | everyone | "Why won't this train?" / "Why is loss stuck at ln(C)?" |
| 2 | **Data and preprocessing mismatches**: normalization statistics computed or merged wrongly, preprocessing that differs from the checkpoint, channel order, train/val leakage, duplicates | 32 stats + 59 data loading | TP, Karpathy, Islam (data bugs most severe) | yes | applied ML, robotics, CV | "Why is validation suspiciously good?" / "Why does the pretrained model underperform?" |
| 3 | **Augmentation, geometry and coordinate conventions**: boxes or keypoints not transformed with the image, height/width swapped, pixels vs fractions, frame and quaternion conventions | **88 + 14 units** (largest class) | Karpathy (flip labels) | sometimes | CV / perception, robotics | "Why are my boxes misaligned after augmentation?" |
| 4 | **Settings silently ignored / wrong defaults**: an option that has no effect on one code path, `x or default` treating 0 as missing, a check that compares something with itself | **69** | (implicit in all) | rarely, a great opportunity | everyone, especially infra | "Why does changing this setting do nothing?" |
| 5 | **Distributed and multi-device**: BatchNorm statistics not synced, only device 0's averages saved, same data seed on every host, rank-dependent bugs | **83** | TP | sometimes (infra roles) | ML infra / training systems | "Why does 8-GPU training differ from 1 GPU?" |
| 6 | **Checkpoint, save/load, resume**: resume not restoring optimizer, scheduler or RNG; pretrained keys dropped and a random layer silently kept; state-dict key mismatches | **77** | TP (best checkpoint) | rarely | everyone | "Why does the resumed run diverge?" / "Why do features change every load?" |
| 7 | **Stale state across resets and episodes**: observations or sensors from before a reset, recurrent state not reset, buffers carrying over | **42** | Andy Jones, PPO details | RL roles | RL / robotics | "Why does the policy flail right after every reset?" |
| 8 | **Misleading evaluation**: wrong averaging dimension, padded batches counted, smoothed curves, sampled eval set unlike the full set, eval mode, sim metrics that don't predict the robot | **40** | TP, Karpathy, UvA | yes (in system design) | everyone (58% of postings mention evaluation) | "The metric says better; is the model actually better?" |
| 9 | **RL specifics**: truncation vs termination, advantages across resets, reward scale, replay buffers, exploration noise shared across a batch or unscaled | **51** | Andy Jones, PPO details | RL roles (Figure, Apptronik postings) | RL / robotics | "Why does value loss explode near time limits?" / "Why is exploration so uniform?" |
| 10 | **Numerical problems**: NaN/inf, precision and dtype (bf16, uint8), overflow | **41** | TP (NaN trials), UvA | **yes (NaN take-homes)** | inference, training systems | "Why is the loss NaN at step 3k?" |
| 11 | **Performance, memory and input bottlenecks**: idle accelerators, data-loading stalls, host-device syncs, leaks, hangs | **30** | TP, Andy Jones | infra roles | infra (32%), inference (44%) mention bottlenecks | "Why is GPU utilisation 30%?" |
| 12 | **Compile / jit / export divergences**: side effects vanishing under `jit`, out-of-bounds reads clamped silently, `torch.compile` changing results, export breaking | **25** | JAX Sharp Bits | JAX roles | research, robotics (JAX in 9-16%) | "Why does the jitted version give a different answer?" |
| 13 | **Batch / environment indexing mixes items**: `view` instead of `permute`, every environment reading environment 0's data | **19** | Karpathy | sometimes | robotics, training | "Why do all my environments behave the same?" |
| 14 | **Randomness and seeding**: seed not passed to one component, identical randomness across workers or hosts | **17** | Karpathy, TP, Andy Jones | sometimes | everyone | "Why do two runs with the same seed differ?" |
| 15 | **Shapes and broadcasting**: `(B,)` against `(B,1)` silently becoming `(B,B)`, batch size equal to a feature size hiding a bug | **21** | UvA | **yes** | everyone | "Why is the loss shape wrong only sometimes?" |

## Real instances to start from (read in full)

| Class | Instance | What happened |
|---|---|---|
| 2 | [LeRobot #4156](https://github.com/huggingface/lerobot/issues/4156) | Percentile statistics (q01/q99) aggregated wrongly when merging datasets |
| 3 | [torchvision #9299](https://github.com/pytorch/vision/issues/9299) | Elastic transform normalised horizontal and vertical displacement by the wrong dimensions on non-square images |
| 3 | [Kornia #6215](https://github.com/kornia/kornia/issues/6215) | Translate augmentation read the same magnitude as pixels in one path and a fraction of the image in another |
| 4 | [Stable-Baselines3 #2274](https://github.com/DLR-RM/stable-baselines3/issues/2274) | n-step returns silently ignored when a replay buffer class was passed explicitly |
| 4 | [Gymnasium #1707](https://github.com/Farama-Foundation/Gymnasium/issues/1707) | An environment-matching check compared one environment's observation space with itself |
| 6 | [timm #2682](https://github.com/huggingface/pytorch-image-models/issues/2682) | `out_features or in_features` treated 0 as missing, creating a random layer that loading never overwrote |
| 7 | [Isaac Lab #8652](https://github.com/isaac-sim/IsaacLab/issues/8652) | Sensors returned reset values for an extra update after a reset, and that read still counted as an update |
| 9 | [CleanRL #279](https://github.com/vwxyzjn/cleanrl/issues/279) | TD3 used one noise sample for the whole batch and ignored the action scale |
| 13 | [Isaac Lab #8680](https://github.com/isaac-sim/IsaacLab/issues/8680) | Every environment got environment 0's copy of a mesh |
| 14 | [CleanRL #133](https://github.com/vwxyzjn/cleanrl/issues/133) | DQN did not respect the seed |

More, with links, in [issues.md](issues.md).

## Which to turn into problems first, and why

1. **Quiet training-loop bugs (#1)**: exactly what debugging rounds test, cheap to reproduce on a CPU, and a natural "nothing is wrong, it just needs longer" twin.
2. **Data and preprocessing mismatches (#2)**: the most severe class in the research and the most common cause of "suspiciously good" or "mysteriously bad" results.
3. **Augmentation and geometry (#3)**: the largest class in real fixed issues and the heart of computer-vision work; easy to make visible in a playground (show the image and the boxes).
4. **Silently ignored settings (#4)**: the wildest animal there is, under-tested in interviews, and common in every framework.
5. **Stale state across resets (#7) and RL specifics (#9)**: the robot-learning differentiator; ties to sim-to-real, which 30% of robotics postings name.
6. **Misleading evaluation (#8)**: the skill postings mention most, and the basis for "is this better or just noise?" questions with no code change at all.

Each should come in several habitats: the real repo at the real commit where the license allows (all 16 repos used here are Apache-2.0, MIT or BSD except Isaac Lab and CleanRL, whose licenses GitHub could not classify, so check them), a real reproduction in PyTorch or JAX at small scale, and a purpose-built codebase only when needed.

## Method

- **Postings**: public Greenhouse, Ashby and Lever boards for about 130 candidate companies; 72 answered (10,122 postings); ML engineering roles filtered by title (1,186), grouped into families by title, and keyword-counted over the description. LinkedIn was not used (its terms forbid scraping).
- **Interviews**: web search across interview-report and prep sites; most sources secondhand and several paywalled.
- **Playbooks and papers**: read directly; summaries in my own words.
- **Fixed issues**: GitHub search, latest up to 100 closed issues with a linked PR per repo; feature requests, docs, install and CI issues removed; titles classified by keyword.

## Limitations

- Keyword counts are rough: one posting mentioning "evaluation" is not a requirement, and title-based classification puts a quarter of issues in "Other". Treat shares as ordering, not measurement.
- Waymo, Databricks and a few others contribute many roles each; families are counted by title and some titles fit several.
- Library issue trackers under-represent user-code bugs (#1, quiet training-loop bugs, are mostly found in users' own scripts, interviews and playbooks, not in library issues). Stack Overflow, which the bug studies used, was not mined here.
- Interview reports are secondhand; none were verified with the companies.
- Not yet read: the full Humbatova taxonomy (category names), Zhang et al. ISSTA 2018, Islam et al. ICSE 2020, JAX's random-numbers tutorial (PRNG key reuse), and the Tuning Playbook's optimisation-failures section.

## Next

- Run the mining prompt (`docs/prompts/mine-bugs.md`) on the top 4-5 repos to turn the strongest issues into full bug cards with exact code.
- Read the remaining papers for their category lists and frequencies, and reconcile them with the classes above.
- Pick habitats for the first six classes and build one problem of each, including at least one "nothing is wrong" case.
