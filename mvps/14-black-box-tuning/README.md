# MVP 14: The new boxes (black-box tuning on a budget, aiming at Tier 2)

*MVPs 05–13 show that Opus finds anything already in the problem: code, docs, logs, production data, slow trends. Here the answer isn't in the problem at all. It exists only as measurements the player makes, on a sourceless system, with 12 noisy benchmark runs. Settings interact, so tuning one at a time misleads. AI-written MVP: an experiment.*

## The ticket

> **From:** Platform on-call. **Priority:** P1
>
> We moved ingest to the new 32-core machines last week. Since then the worker pool falls behind at peak and p99 latency is in seconds. The migration set `workers` to 32 in `config.json`, one per core. On the old 8-core boxes (8 workers) it was fine at last year's traffic.
>
> Find settings that keep up with today's peak (12,000 events/s) **and** next quarter's (13,000 events/s), with p99 under 250 ms at both.

The pool is `ingest/pool.py`, and its settings are in `config.json` (`workers`, `batch`, `prefetch`). The decode, enrich and commit work happens in a compiled extension owned by another team; there's no source. `python bench.py [--load N]` runs the pool on the staging cluster (same hardware as production) under replayed production traffic, using whatever is in `config.json`, and prints the pool's telemetry: throughput, latency, CPU, how busy the ledger's commit lock was, the heap held by in-flight events, and GC pauses. **Staging is shared: you get 12 benchmark runs in total**, and like any real benchmark the numbers are noisy.

Change `config.json` only. Say "resolved" when the settings are in, and say what p99 you expect at 13,000 events/s with them.

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

## Human attempt (2026-11-04): Danny, not resolved

Danny worked blind in a clean clone (branch `solve/danny`, commit 0997ce4), with an AI pair session that had no access to the answers. He used 10 of 12 runs and reported "not resolved". His final config was 16/50/8: p99 232 ms at 12k (passes) and 426 ms at 13k (fails). That's the same config Opus gate run 2 ended on.

His feedback: "it seems like it's just a guessing game … I don't have to understand the problem at all. I just have to do a rather binary search … It didn't force me to learn anything new. It could have been any numbers."

What this says:
- Human with AI so far: 0 of 1. The planned strategy's 50/80 is still the only evidence that it can be solved.
- The critique is fair. The bench prints only throughput, p50, p99 and cpu %. So the knobs' meaning never pays off, and the problem rewards search tactics, not understanding of the system. That fails the "Learning" assumption even when it fails AI.
- Fix to try: print the telemetry a real engineer would read, such as commit-lock wait %, GC pause time and heap in use. Understanding the system then shows the bottleneck in 1–2 runs, while blind search still runs out of budget. Also ask for a graded prediction, for example "p99 at 14k with your config", so the model is tested, not the guess.

## Version 2 (2026-11-04): telemetry added, re-gated: still passes, 0 of 3

After Danny's feedback, `bench.py` now also prints how much of the time the ledger commit lock is held, the heap held by in-flight events, and GC pauses (full collections with the longest pause, or young-generation only). The ticket also asks for the p99 the player expects at 13k. Nothing else changed: same model, same 12 runs, same replay.

| Run | Final config | True p99 at 12k / 13k | Its prediction at 13k | What happened |
|---|---|---|---|---|
| 1 | 14 / 80 / 5 | 176 / **264** ms, failed (closest) | 250–310 ms | Found all three effects and pinned the GC cliff within a few MB, then chose batch 80, too big. |
| 2 | 12 / 50 / 4 | 232 / **426** ms, failed | 350–400 ms | Cut prefetch to 4 for heap headroom and stayed at batch 50; the commit lock still binds. |
| 3 | 12 / 100 / 5 | 155 / **~290** ms, failed | ~290 ms | Same pattern as run 1, with batch 100. |

With telemetry, every run named every mechanism correctly: contention past about 12–14 workers, the commit lock, the GC limit at about 250–270 MB, and prefetch starvation. Every run also reported "not resolved" honestly, with a well-calibrated prediction. The new failure is the trade-off itself. To relieve the lock, each run jumped to batch 80–100, and to stay under the heap limit it cut prefetch. Bigger batches add latency of their own, and lower prefetch costs CPU. None tried the middle: batch about 60 with prefetch 7–8 at 12–14 workers. Two of the three again said 13k probably needs changes outside the config.

What this says: understanding the system now pays off; it took Opus from 1 mechanism per run to all 4. But it isn't enough on its own. The remaining step is weighing three costs against each other under a budget, which is the judgement the problem is meant to grade. Next: a human attempt on this version.
