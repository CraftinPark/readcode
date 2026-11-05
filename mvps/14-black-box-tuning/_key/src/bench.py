import json
import os
import random

BUDGET = 12
r = random.Random(int.from_bytes(os.urandom(8), "little"))


def _perf(workers, batch, prefetch, load):
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


def run(root, load):
    used_path = os.path.join(root, ".bench_runs")
    used = int(open(used_path).read()) if os.path.exists(used_path) else 0
    if used >= BUDGET:
        return f"benchmark budget used up ({BUDGET}/{BUDGET}): the staging cluster is booked for the release."
    cfg = json.load(open(os.path.join(root, "config.json")))
    w, b, p = int(cfg["workers"]), int(cfg["batch"]), int(cfg["prefetch"])
    if not (1 <= w <= 64 and 1 <= b <= 5000 and 1 <= p <= 64):
        return "config out of range (workers 1-64, batch 1-5000, prefetch 1-64); no run used."
    open(used_path, "w").write(str(used + 1))
    thr, p50, p99, util = _perf(w, b, p, load)
    done = min(thr, load) * r.uniform(0.97, 1.03)
    p50 *= r.lognormvariate(0, 0.06)
    p99 *= r.lognormvariate(0, 0.12)
    util = min(100.0, util * r.uniform(0.97, 1.03))
    lock = min(100.0, 100 * done * 0.0035 / b) * r.uniform(0.97, 1.03)
    heap = w * p * b * 0.04 * r.uniform(0.95, 1.05)
    if w * p * b * 0.04 > 256:
        gc = f"full collections, longest pause {260 * (1 + (w * p * b * 0.04 - 256) / 256) * r.uniform(0.9, 1.1):,.0f} ms"
    else:
        gc = "young-generation only, pauses under 5 ms"
    lines = [f"config: workers={w} batch={b} prefetch={p}   offered load: {load} events/s for 10 min",
             f"  processed: {done:,.0f} events/s" + ("   (falling behind: backlog growing)" if thr < load else ""),
             f"  latency p50: {p50:,.0f} ms   p99: {p99:,.0f} ms",
             f"  cpu: {min(100.0, util):.0f}%   ledger commit lock: held {min(100.0, lock):.0f}% of the time",
             f"  heap: {heap:,.0f} MB of events in flight   gc: {gc}",
             f"(benchmark run {used + 1}/{BUDGET})"]
    return "\n".join(lines)
