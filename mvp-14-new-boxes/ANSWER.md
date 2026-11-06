# MVP 14 (the new boxes): answer

## 1. Time

- **Start:** 15:52
- **End:** 17:02
- **Thinking vs waiting:** 90/10

## 2. AI tools

Claude Code (Claude Opus 5.5) in VS Code. I used it to read `ingest/pool.py` and explain the three settings, run `bench.py` and edit `config.json`, organize each run's telemetry into tables, and think through the trade-offs (lock time per commit, heap vs GC, CPU queueing). I picked which runs to spend the budget on. It did not open or decompile any `.pyc` files.

## 3. Runs used

**12 of 12.**

| # | workers / batch / prefetch | load | p99 | CPU | lock | heap | GC |
|---|---|---|---|---|---|---|---|
| 1 | 32 / 50 / 8 | 12k | 4,444 ms (falling behind) | 100% | 80% | 531 MB | full, 532 ms |
| 2 | 16 / 50 / 8 | 12k | 278 ms | 73% | 82% | 254 MB | young-gen |
| 3 | 8 / 50 / 8 | 12k | 255 ms | 84% | 85% | 125 MB | young-gen |
| 4 | 16 / 50 / 3 | 12k | 265 ms | 91% | 82% | 97 MB | young-gen |
| 5 | 16 / 100 / 3 | 12k | 364 ms | 86% | 43% | 195 MB | young-gen |
| 6 | 16 / 200 / 3 | 12k | 736 ms | 91% | 21% | 377 MB | full, 379 ms |
| 7 | 16 / 100 / 1 | 12k | 5,239 ms (falling behind) | 99% | 32% | 63 MB | young-gen |
| 8 | 16 / 100 / 2 | 12k | 19,215 ms (unstable) | 100% | 43% | 128 MB | young-gen |
| 9 | 16 / 100 / 4 | 12k | **205 ms** | 85% | 42% | 262 MB | young-gen |
| 10 | 16 / 100 / 8 | 12k | 727 ms | 77% | 42% | 515 MB | full, 532 ms |
| 11 | 16 / 100 / 5 | 13k | 652 ms | 85% | 45% | 316 MB | full, 305 ms |
| 12 | 16 / 100 / 4 | 13k | **397 ms** | 92% | 46% | 257 MB | young-gen |

## 4. Final answer

**Not resolved.**

`config.json` is set to `{"workers": 16, "batch": 100, "prefetch": 4}`, the best config I measured:

- **12,000 events/s:** p99 205 ms, under the 250 ms target (one run, about 45 ms of margin).
- **13,000 events/s:** p99 397 ms, over the target. **I expect a p99 of about 400 ms at 13k with these settings.** Single runs varied by roughly ±100–150 ms, so the true value is probably 300–500 ms.

This fixes today's incident: the 32-worker config is at p99 4.4 s and falling behind. It doesn't meet next quarter's target. At 13k the limit is CPU (92%), not the lock or GC. The one lead I didn't get to test is fewer workers with deeper prefetch at the same heap (8/100/8 or 12/100/5). In run 11, deeper prefetch lowered CPU, but that config's heap was too large. If that doesn't work, these three settings alone probably can't meet 13k at 250 ms, and the fix would need the extension's owners or more machines.

## 5. Approach and what confused me

I changed one setting at a time and used the telemetry to find which limit applied: GC with 32 workers, then the commit lock with batch 50, then workers running dry when prefetch was low, and finally CPU at 13k. The confusing part was prefetch. It has a minimum (1–2 makes the pool fall behind or become unstable) and a maximum (5 or more triggers full GCs), and the only good value was 4. The 8- vs 16-worker CPU numbers also didn't fit a clear pattern.

### How we approached it

I worked through this in a conversation with Claude Code. Claude explained the three knobs, and I chose each experiment. Claude noticed that workers × batch × prefetch gives the number of events in memory at once. With the original config that was about 12,800 events, roughly a second of traffic. We started by testing 8, 16 and 32 workers. That showed 32 workers was the outage: a 531 MB heap caused half-second full GC pauses. But neither 8 nor 16 workers got p99 under 250 ms, and the commit lock was busy about 82% of the time no matter how many workers ran. I then tested batch sizes 50, 100 and 200. Lock busy time halved each time batch doubled, which showed it costs about 3.5 ms per commit regardless of batch size. So batch 100 was needed to leave room for 13k, while 200 caused full GCs again. Next I tested prefetch from 1 to 8. Claude first predicted that lower prefetch would help p99, and the data proved that wrong: prefetch 1 and 2 left workers running dry and made the pool fall behind or become unstable, 5 and 8 triggered full GCs, and 4 was the only good value (p99 205 ms at 12k). That run also showed the full-GC threshold sits between 262 and 316 MB of heap. In my last run, 16/100/4 at 13k gave p99 397 ms with CPU at 92%. Claude's per-commit lock model predicted the lock busy time correctly in every run. The final limit was CPU, which these settings couldn't solve. With more benchmark runs, I would test deeper prefetch with fewer workers.
