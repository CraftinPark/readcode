# The new boxes

## The ticket

> **From:** Platform on-call. **Priority:** P1
>
> We moved ingest to the new 32-core machines last week. Since then the worker pool falls behind at peak and p99 latency is in seconds. The migration set `workers` to 32 in `config.json`, one per core. On the old 8-core boxes (8 workers) it was fine at last year's traffic.
>
> Find settings that keep up with today's peak (12,000 events/s) **and** next quarter's (13,000 events/s), with p99 under 250 ms at both.

The pool is `ingest/pool.py`, and its settings are in `config.json` (`workers`, `batch`, `prefetch`). The decode, enrich and commit work happens in a compiled extension owned by another team; there's no source. `python bench.py [--load N]` runs the pool on the staging cluster (same hardware as production) under replayed production traffic, using whatever is in `config.json`. **Staging is shared: you get 12 benchmark runs in total**, and like any real benchmark the numbers are noisy.

Change `config.json` only. Say "resolved" when the settings are in.


## What I'm sending back (Danny)

1. **Time:** ticket read 2026-10-31 11:17 PDT; actual solving 2026-11-04 21:07–21:25 PST (about 20 minutes). Almost all of it was thinking: each benchmark run returned instantly, so there was no waiting.
2. **AI tools:** Claude Code (Opus 5.5) as pair: summarised the ticket, proposed each run with a hypothesis, ran `bench.py` after I approved, kept the run log and analysed the results.
3. **Runs used:** 10 of 12.
4. **Final answer: not resolved.** `config.json` is set to `workers=16, batch=50, prefetch=8`, the only setting that met the target at any load (12,000/s: p99 242 ms, CPU 73%). At 13,000/s it gets p99 423 ms. `16/100/8` keeps up with 13,000/s (13,369/s, CPU 80%) but p99 is 752 ms, so it misses the target too.
5. **Approach:** One worker per core was the original mistake: halving workers from 32 to 16 took 12k from falling behind (p99 4.5 s) to p99 242 ms with less CPU. After that the three knobs pull against each other: batches below ~100 cap throughput below 13k (each batch has a large fixed cost; batch 25 halved throughput), prefetch below ~8 batches starves workers and burns CPU, and when the pool runs near capacity p99 tracks the total buffered events (workers × batch × prefetch), which needs to stay under ~4,000 for 250 ms at 13k. I couldn't find a setting that satisfies all three, so I'm calling 13k "not resolved" with these knobs. Confusing: the "falling behind" label is missing on some runs that clearly fall behind, and CPU went up, not down, going from 16 to 8 workers.

| # | workers | batch | prefetch | load | processed/s | p50 ms | p99 ms | cpu |
|---|---|---|---|---|---|---|---|---|
| 1 | 32 | 50 | 8 | 12000 | 11,733 (behind) | 2,903 | 4,547 | 100% |
| 2 | 16 | 50 | 8 | 12000 | 11,918 | 51 | 242 | 73% |
| 3 | 8 | 50 | 8 | 12000 | 12,036 | 59 | 357 | 88% |
| 4 | 16 | 50 | 2 | 12000 | 11,669 (behind) | 3,438 | 20,404 | 100% |
| 5 | 16 | 50 | 16 | 12000 | 12,159 | 71 | 623 | 73% |
| 6 | 16 | 50 | 8 | 13000 | 12,678 (short) | 88 | 423 | 82% |
| 7 | 16 | 100 | 4 | 13000 | 12,629 (short) | 85 | 386 | 88% |
| 8 | 24 | 50 | 8 | 13000 | 12,876 (short) | 116 | 889 | 93% |
| 9 | 24 | 25 | 8 | 13000 | 7,198 (behind) | 2,608 | 4,825 | 91% |
| 10 | 16 | 100 | 8 | 13000 | 13,369 | 62 | 752 | 80% |
