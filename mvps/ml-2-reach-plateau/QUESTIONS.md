# Questions (open only after your verdict and line range are written down)

One letter each, into `answers.json` as `q1`, `q2`, `q3`.

## q1. How does the problem you found hurt training?

If you answered `no_bug`, pick the option that matches your explanation.

- **a)** On a time-limit step the stored reward already holds gamma * V(final obs), and GAE adds gamma * V of the next stored obs on top, so every truncated episode's last step is counted twice.
- **b)** The critic is fit to its own old values plus a unit-scale term, so nothing ties its level to the real returns; values drift, and once they go negative, ending the episode early starts to look good.
- **c)** The ratio compares the log-prob of the raw Gaussian sample with the action the env actually executed after clipping, so it is wrong for every saturated action and the clip fires almost everywhere.
- **d)** Normalising over the whole batch instead of per minibatch leaves each minibatch's advantages with a non-zero mean, which biases the policy gradient toward whatever actions dominate that minibatch.
- **e)** Nothing in training changed: eval now runs a frozen copy of the normaliser on its own env seed, so the new curve is measured on a different set of targets than the old one.

## q2. Which is the smallest correct fix that keeps the refactor's intent (advantages normalised once over the full batch)?

- **a)** Store the critic targets as their own array when GAE (or the n-step fallback) is computed, before anything rescales the advantages.
- **b)** Normalise the critic targets with the same mean and std as the advantages, so value loss and policy loss see the same scale.
- **c)** In `normalize_advantages`, subtract the mean but don't divide by the std, so the advantages keep their reward units.
- **d)** Make `normalize_advantages` work on a copy (`adv = self.advantages.copy()`) so the write can't leak into other arrays.
- **e)** Pass the clipped action to `buf.add` in `Trainer.collect`, so the stored action matches what the env executed.

## q3. An arm reaches the 100-step limit without hitting the elbow limit (truncated, not terminated). What TD target does `compute_gae` use for that step?

- **a)** r + gamma * V(final obs): the trainer folded the bootstrap into the reward, and `dones = 1` stops GAE from also using the next stored value, which belongs to the new episode.
- **b)** r alone: `dones = 1` is written for terminated and truncated steps alike, so a time limit is handled exactly like hitting the elbow limit.
- **c)** r + gamma * V(final obs) + gamma * V(next stored obs): the bootstrap sits in the reward and GAE adds the next state's value on top of it.
- **d)** r + gamma * V(first obs of the next episode): the vec env has already reset that arm, and GAE bootstraps from whatever obs is stored next.
