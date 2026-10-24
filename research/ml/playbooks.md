# What experts say goes wrong: playbooks and bug studies

Read 2026-10-24. Each line is a failure class an expert source names, as *symptom → cause → check*. Sources are abbreviated in brackets; full links at the end. Summaries are mine, from the sources; nothing is copied.

## Data and input pipeline
- Validation curve shows a periodic pattern → train/test overlap or bad shuffling → check the split and shuffling [TP]
- Model learns partly but oddly with flip augmentation → labels or keypoints not flipped with the image → visualise exactly what enters the net [KR]
- Pretrained weights underperform → preprocessing (mean/std, channel order) differs from the checkpoint's → match preprocessing [KR]
- Duplicates, corrupted images or labels, class imbalance → skewed training and eval → inspect data by hand, sort by loss [KR]
- Accelerators idle, step time grows with batch size → I/O or host-device sync bottleneck (e.g. pulling metrics every step) → profile, prefetch, precompute [TP]
- Data bugs and logic bugs are the most severe DL bug types, >48% of cases [IS]

## Model and loss
- Poor accuracy → softmax applied before a loss that already applies log-softmax; probabilities into NLLLoss; softmax over the wrong dim [UV]
- NaN or divergence → BCE on sigmoid outputs (log of ~0) instead of the with-logits loss [UV]
- Network silently ignores other examples → `view` used where `transpose`/`permute` was needed, mixing the batch dim → gradient check: loss on example i should only touch input i [KR]
- Wrong results, no error → LSTM batch and time axes swapped; matmul "works" because batch size equals a feature size → test with several batch sizes [UV]
- "Hockey stick" loss → final-layer bias badly initialised → initial loss should be about -log(1/C) [KR]
- Autoregressive model looks too good → it sees its own target (off-by-one) [KR]
- Embedding re-created in `forward`, or modules in a plain list → parameters never learn or never reach the optimiser [UV]

## Optimisation and training loop
- Wrong gradients → `zero_grad()` missing [UV]; gradients clipped on the loss instead of the gradients [KR]
- Unexpected regularisation → weight decay with Adam instead of AdamW [UV]
- Early instability → warmup and initialisation; many NaN trials → unstable region or a code bug [TP]
- Learning rate fine in short runs, fails in long runs → schedule tuned on a short horizon [TP]
- "Improvement" vanishes on rerun → trial variance → rerun the best config several times [TP]
- Can't overfit a tiny batch → pipeline bug → overfit one batch first [KR]

## Evaluation
- Odd behaviour after validation → model left in eval mode (dropout/BatchNorm) [UV]
- Wrong metric → averaged over classes instead of the batch; padded final batch counted [UV][TP]
- Best checkpoint is not the last one → keep the N best and choose afterwards [TP]
- Smoothed, batch-wise test loss misleads → evaluate on the full set [KR]

## Distributed / multi-device
- BatchNorm differs across devices; saved moving averages are only device 0's → sync stats before eval and checkpoint [TP]
- Duplicate logs/checkpoints, wrong randomness → same seed for init, different seeds for data per host [TP]

## Reinforcement learning
- Value targets far outside about ±10 → reward scale or discounting wrong [AJ]
- Value wrong near episode ends; terminal correlation near zero → end-of-episode / reset handling in returns and advantages [AJ]
- Advantages not near mean-zero → advantage bug, especially at resets [AJ]
- Negative KL → calculation bug, often invalid-action handling; KL growing steadily → stale experience replayed [AJ]
- Learner sees near-identical early samples → environments not decorrelated at reset [AJ]
- Throughput decays over time → state accumulating (e.g. logging) [AJ]
- Probe environments isolate value, backprop, discounting and policy bugs in seconds [AJ]
- PPO details that differ between implementations and change results: Adam epsilon (1e-5 vs framework defaults), value-loss clipping, observation/reward normalisation and clipping, shared vs separate networks, action clipping vs tanh, LR/clip annealing, truncation handling, LSTM state reset at episode end, invalid-action masking [PPO]

## JAX-specific
- `print` and globals behave "wrongly" under `jit` (traced once, cached) → keep functions pure [JX]
- Out-of-bounds indexing never errors: reads clamp to the last element, updates are dropped silently [JX]
- `float64` silently becomes `float32` unless x64 is enabled at startup [JX]
- Boolean-mask indexing fails under `jit` (dynamic shapes) → use three-argument `where` [JX]
- Iterators inside `lax` loops give silently wrong results [JX]
- (PRNG key reuse is covered in JAX's random-numbers tutorial, not this page; still to read.)

## Sources
- [TP] Google Research, *Deep Learning Tuning Playbook* — https://github.com/google-research/tuning_playbook (the optimisation-failures section was past the part read)
- [KR] Andrej Karpathy, *A Recipe for Training Neural Networks* (2019) — https://karpathy.github.io/2019/04/25/recipe/
- [AJ] Andy Jones, *Debugging RL, Without the Agonizing Pain* — https://andyljones.com/posts/rl-debugging.html
- [UV] UvA Deep Learning notebooks, *Guide 3: Debugging in PyTorch* — https://uvadlc-notebooks.readthedocs.io/en/latest/tutorial_notebooks/guide3/Debugging_PyTorch.html
- [JX] JAX docs, *Common Gotchas in JAX* ("Sharp Bits") — https://docs.jax.dev/en/latest/notebooks/Common_Gotchas_in_JAX.html
- [PPO] Huang et al., *The 37 Implementation Details of Proximal Policy Optimization* (ICLR Blog Track 2022) — https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/
- [HU] Humbatova et al., *Taxonomy of Real Faults in Deep Learning Systems* (arXiv:1910.11015, 2019): 1,059 GitHub artefacts (TensorFlow, Keras, PyTorch), Stack Overflow posts, 20 interviews; 15 fault categories, 13 experienced by ≥50% of surveyed developers. Category names not yet read (need the full paper).
- [IS] Islam et al., *A Comprehensive Study on Deep Learning Bug Characteristics* (ESEC/FSE 2019, arXiv:1906.01388): 2,716 Stack Overflow posts + 500 bug-fix commits across five libraries.
- Not yet read: Zhang et al., *An Empirical Study on TensorFlow Program Bugs* (ISSTA 2018); Islam et al., *Repairing Deep Neural Networks: Fix Patterns and Challenges* (ICSE 2020).
