"""True performance of the ingest worker pool (key only). Load in events/s. Returns (throughput, p50, p99, cpu%).

Hidden structure: cores contend past ~14 workers; each batch takes a global commit lock for 3.5 ms (so small
batches cap throughput); low prefetch leaves workers idle; and in-flight events (workers x prefetch x batch, ~40 KB
each) past ~256 MB of heap trigger GC pauses that wreck p99. Raising batch fixes the lock but tips the heap over
unless prefetch or workers come down."""


def perf(workers, batch, prefetch, load):
    cpu = workers * 2600 / (1 + (workers / 14) ** 2) * prefetch / (prefetch + 1)
    thr = min(cpu, batch / 0.0035)
    heap_mb = workers * prefetch * batch * 0.04
    rho = load / thr
    util = min(100.0, 100 * load / cpu)
    if rho >= 1:
        return thr, 2500.0, 5000.0, util
    p50 = 9 + 450 * batch / load + 8 * rho / (1 - rho)
    p99 = 18 + 900 * batch / load + 40 * rho / (1 - rho)
    if heap_mb > 256:
        p99 += 260 * (1 + (heap_mb - 256) / 256)
        p50 += 15
    return thr, p50, p99, util
