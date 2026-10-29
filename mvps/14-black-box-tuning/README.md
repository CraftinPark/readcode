# MVP 14: The new boxes (black-box tuning on a budget, aiming at Tier 2)

*MVPs 05–13 show that Opus finds anything already in the problem: code, docs, logs, production data, slow trends. Here the answer isn't in the problem at all. It exists only as measurements the player makes, on a sourceless system, with 12 noisy benchmark runs. Settings interact, so tuning one at a time misleads. AI-written MVP: an experiment.*

## The ticket

> **From:** Platform on-call. **Priority:** P1
>
> We moved ingest to the new 32-core machines last week. Since then the worker pool falls behind at peak and p99 latency is in seconds. The migration set `workers` to 32 in `config.json`, one per core. On the old 8-core boxes (8 workers) it was fine at last year's traffic.
>
> Find settings that keep up with today's peak (12,000 events/s) **and** next quarter's (13,000 events/s), with p99 under 250 ms at both.

The pool is `ingest/pool.py`, and its settings are in `config.json` (`workers`, `batch`, `prefetch`). The decode, enrich and commit work happens in a compiled extension owned by another team; there's no source. `python bench.py [--load N]` runs the pool on the staging cluster (same hardware as production) under replayed production traffic, using whatever is in `config.json`. **Staging is shared: you get 12 benchmark runs in total**, and like any real benchmark the numbers are noisy.

Change `config.json` only. Say "resolved" when the settings are in.

## After "resolved" (hidden from the player)

`_key/replay.py` evaluates the player's `config.json` against the true model with no noise, at 12,000 and 13,000 events/s. Both must keep up with p99 ≤ 250 ms.

The hidden structure (`_key/src/model.py`):
- **CPU contention:** throughput per worker falls past about 14 workers (32 workers do *less* than 14).
- **Commit lock:** each batch holds a global commit lock for 3.5 ms, so batch size caps throughput (batch 50 tops out at 14,286 events/s).
- **Prefetch:** low prefetch leaves workers idle between batches (throughput × p/(p+1)).
- **GC:** in-flight events (workers × prefetch × batch, about 40 KB each) beyond ~256 MB of heap cause GC pauses that add hundreds of ms to p99.

The trap is the interaction. Cutting workers to ~14 fixes today's peak but leaves the lock binding at 13,000. Raising the batch to fix the lock tips the heap over and p99 gets *worse*, unless prefetch or workers come down at the same time. Only 76 of 36,816 configurations on a fine grid (0.2%) pass. They cluster around 11–15 workers, batch 60–70 and prefetch 7–9.

## Key (`_key/`)

| Config (workers, batch, prefetch) | Today 12k | Next quarter 13k |
|---|---|---|
| shipped (32, 50, 8) | falls behind (11,881) | falls behind |
| `old_boxes/` (8, 50, 8) | p99 269 | p99 576 |
| `fewer_workers/` (14, 50, 8) | p99 232, ok | p99 426 (lock-bound) |
| `bigger_batch/` (14, 100, 8) | p99 595 (GC) | p99 644 |
| `reference/` (13, 60, 8) | p99 139 | p99 188 |

`python _key/check_key.py` checks all five. `engine/stage.pyc` is compiled from `_key/src/bench.py` with docstrings stripped (`python -c "import py_compile; py_compile.compile('_key/src/bench.py', cfile='engine/stage.pyc', optimize=2)"`). It keeps the run budget in `.bench_runs`. Like MVP 12, the budget relies on the honour system: someone who disassembles the `.pyc` can read the model.

## Gate result (2026-10-28): passes the gate, 0 of 3 solved

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only, 12 benchmark runs each). Run time 76-90 s each. **All three failed, and all three said so**: each reported "not resolved" instead of claiming success.

| Run | Final config | True p99 at 12k / 13k | How it searched |
|---|---|---|---|
| 1 | 16 / 80 / 5 | 182 / **279** ms, failed (closest) | Found contention, the prefetch trade-off and that a bigger batch helps; got within 29 ms. Asked for more staging runs. Did not open `stage.pyc`, "because that is the benchmark itself". |
| 2 | 16 / 50 / 8 | 232 / **426** ms, failed | One knob at a time. Tried batch 75 and 100 at prefetch 8 (both into GC) and never combined a bigger batch with lower prefetch. Worked out from a batch-25 run that commits cap at about 280/s (true: 286/s), but didn't act on it. |
| 3 | 8 / 50 / 16 | 232 / **426** ms, failed | Went back to the old 8 workers and raised prefetch. Never tried 9–15 workers. Kept its 12th run unused. |

All three concluded that 13,000 events/s "can't be met by settings alone" and escalated to the platform team or asked for more capacity. That's wrong: about 76 configurations pass, e.g. 13 / 60 / 8 or 14 / 60 / 7.

What this tells us: this is the first problem where the answer exists only as measurements the player makes, and it's the first clean 0/3. Opus diagnosed each mechanism (contention, the commit cap, prefetch starvation) from single noisy runs, but it didn't plan the experiment around interactions and ran out of budget doing one-knob sweeps. Then it called the target infeasible instead of saying its search was incomplete.

**Caveat before counting this as Tier 2: no human has tried it.** The feasible region is 0.2% of a fine grid and the benchmark is noisy, so it may just be too hard for anyone with 12 runs. The definition needs "AI alone fails" *and* a human (with AI) can succeed. Next step: one human solve, or a reasoning check that a planned design (estimate the lock cap from a small-batch run, the contention peak from two worker counts, then size batch and prefetch to the heap) reaches the region in 12 runs.

## Is it humanly solvable? A planned strategy run against the noisy bench (2026-10-28)

`_key/planned_strategy.py` writes down a 12-run plan a careful engineer could follow. It reads only what the bench prints (processed events/s, p50, p99, cpu %) and uses textbook reasoning, not the hidden formulas:
1. **Measure capacity, don't guess it.** cpu % = load ÷ capacity, so one run measures capacity. Scan 8, 12, 16 and 20 workers (batch 50, prefetch 8, 12k) and keep the best.
2. **Find the second bottleneck.** Batch 25 at 13k falls behind with cpu under 100%, so something else limits it. Processed ÷ 25 is the commit rate, and a batch of *b* caps out near *b* × that rate.
3. **Spot tail spikes.** A p99 more than 6× p50 means a tail spike. Keep the in-flight size (workers × prefetch × batch) below the smallest one that spiked.
4. **Choose and check.** Pick a batch that keeps commits under ~75% busy at 13k and the largest prefetch under the in-flight limit. Check it at 13k and at 12k, and adjust with the runs left.

Each trial gets fresh bench noise and a fresh 12-run budget, and the noise-free replay grades the result. **Solved 50 of 80** (27/40 and 23/40), usually in 8–9 runs, with 12/60/8 or 16/61/6. Failures follow one pattern: the capacity peak is flat (12 and 16 workers are within the ±3% noise), and after picking 16 the plan read a cpu-bound miss as a commit-lock miss. It raised the batch, which forced prefetch down, and it ran out of runs.

What this says: a planned design reaches the narrow region about 60% of the time on 12 noisy runs. Opus, tuning one knob at a time, went 0 of 3 and called the target infeasible. So the problem is solvable by method, not just by luck, and it separates planned experimenting from one-knob tuning.

Caveats:
- I wrote the plan knowing the hidden model, so its choices (which worker counts, the 6× spike rule, the 75% target) may be better than a fresh person would make.
- This is evidence that the problem can be solved, not a human solve. A real person trying it is still the stronger test.
