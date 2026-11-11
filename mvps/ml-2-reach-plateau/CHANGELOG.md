# git log --oneline --no-merges (trimmed to the last month)

```
f3a91c2  2026-10-24  alex   train: print final eval summary
0b7d5e1  2026-10-23  alex   README: new layout, how to run
9e2c4a8  2026-10-23  alex   tests: buffer GAE vs naive loop, normaliser, env
c71f0d3  2026-10-22  alex   eval: own env + frozen copy of the obs normaliser (no more shared env in eval)
5d0a6b9  2026-10-22  alex   ppo: normalise advantages once over the full batch, not per minibatch
a18e7f4  2026-10-21  alex   normalize: obs clip 10 -> 5 (matches what the old tf code used)
2c39b10  2026-10-21  alex   logging: drop tensorboard, CSVLogger + console table
77e0d25  2026-10-21  alex   ppo: move update into PPO class (ppo.py)
e4b8812  2026-10-20  alex   buffer: RolloutBuffer out of trainer.py, (T, N) arrays, flat() for minibatching
3f6c0a9  2026-10-20  alex   env: terminated/truncated API (#41); time-limit bootstrap moved from TimeLimitBootstrap wrapper into Trainer.collect
19ad5b3  2026-10-20  alex   config: dataclass + presets instead of argparse soup
d02e6f1  2026-10-20  alex   start refactor: split train_ppo.py (1100 lines) into armrl/
---- everything below is the pre-refactor single file ----
8b1e7c4  2026-10-14  priya  reach_v3 curves for the group meeting (runs/before_refactor_s1.csv)
6aa30d2  2026-10-09  sam    reach: hit_penalty -5 -> 0 (#37)
c5f91e0  2026-10-02  priya  sweep reach_v3: lr 1e-3, gamma 0.97, 16 envs x 64 steps
41c0b7a  2026-09-28  priya  clip_vloss off by default (#22)
e90d1f3  2026-09-25  sam    tanh squashing experiment, reverted (#29)
b2275ad  2026-09-25  sam    tanh squashing for actions (#29)
```
