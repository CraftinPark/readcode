"""Is MVP 14 humanly solvable? A planned 12-run experiment, written as code, run many times against the real noisy
bench (`_key/src/bench.py`, fresh noise each time) and graded by the noise-free replay.

The strategy reads only what the player sees in bench output (processed events/s, p50, p99, cpu %) and uses
textbook reasoning, not the hidden formulas:
  1. cpu % = load / cpu capacity, so one run at a known load measures capacity. Scan workers (8, 12, 16, 20)
     at batch 50 / prefetch 8 / 12k and keep the count with the most capacity.
  2. A run that falls behind while cpu < 100% is limited by something else. Batch 25 at 13k falls behind; the
     processed rate / 25 is the commit rate (batches/s), so a batch of b caps out near b * that rate.
  3. A p99 far above p50 (more than 6x) with p50 flat is a tail spike (GC or similar). Note the in-flight size
     (workers x prefetch x batch) of every run with and without a spike; stay below the smallest spiking one.
  4. Pick a batch that keeps the commit lock under ~75% busy at 13k, the largest prefetch that stays under the
     in-flight limit, check at 13k and 12k, and adjust with the runs left.

    python _key/planned_strategy.py --trials 40
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
sys.path.insert(0, HERE)
import replay  # noqa: E402

RE = re.compile(r"processed: ([\d,]+).*?p50: ([\d,]+) ms\s+p99: ([\d,]+) ms.*?cpu: (\d+)%", re.S)


class Bench:
    def __init__(self):
        import importlib
        import bench
        self.b = importlib.reload(bench)  # fresh random seed per trial
        self.root = tempfile.mkdtemp()
        self.log = []

    def __call__(self, w, b, p, load):
        json.dump({"workers": w, "batch": b, "prefetch": p}, open(os.path.join(self.root, "config.json"), "w"))
        out = self.b.run(self.root, load)
        m = RE.search(out)
        if not m:
            return None
        done, p50, p99, cpu = (float(x.replace(",", "")) for x in m.groups())
        r = {"w": w, "b": b, "p": p, "load": load, "done": done, "p50": p50, "p99": p99, "cpu": cpu,
             "behind": "falling behind" in out, "inflight": w * b * p}
        r["spike"] = p99 > 6 * p50
        self.log.append(r)
        return r


def strategy(bench):
    # 1. capacity scan
    caps = {}
    for w in (8, 12, 16, 20):
        r = bench(w, 50, 8, 12000)
        caps[w] = 12000 * 100 / max(r["cpu"], 1) if r["cpu"] < 99 else r["done"]
    w = max(caps, key=caps.get)
    cap8 = caps[w]  # capacity at prefetch 8
    # 2. commit rate
    r = bench(w, 25, 8, 13000)
    commit_rate = r["done"] / 25 if r["behind"] else 13000 / 25 * 1.1
    # 3. in-flight limit from spikes seen so far
    def limit():
        spikes = [x["inflight"] for x in bench.log if x["spike"]]
        safe = [x["inflight"] for x in bench.log if not x["spike"]]
        lo = min(spikes) if spikes else None
        hi = max([s for s in safe if lo is None or s < lo] or [0])
        return (hi + lo) / 2 if lo else hi * 1.5
    # 4. choose, test, adjust
    batch = int(13000 / (0.75 * commit_rate)) + 1
    best = None
    while len(bench.log) < 12:
        lim = limit()
        p = max(1, min(16, int(lim // (w * batch))))
        r13 = bench(w, batch, p, 13000)
        if r13 is None:
            break
        if r13["spike"]:
            continue  # limit() tightens; retry with lower prefetch
        if r13["behind"] or r13["p99"] > 230:
            if r13["cpu"] >= 90:   # cpu-bound: more prefetch helps only if in-flight allows; try fewer/more workers
                w = w + 1 if caps.get(w + 4, 0) >= caps.get(w - 4, 0) else w - 1
            else:                  # lock-bound
                batch = int(batch * 1.15) + 1
            continue
        best = (w, batch, p)
        if len(bench.log) < 12:
            r12 = bench(w, batch, p, 12000)
            if r12 and (r12["spike"] or r12["p99"] > 230):
                batch = int(batch * 0.9)
                best = None
                continue
        break
    return best or (w, batch, max(1, min(16, int(limit() // (w * batch)))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    wins, picks = 0, {}
    for t in range(a.trials):
        bench = Bench()
        w, b, p = strategy(bench)
        d = tempfile.mkdtemp()
        json.dump({"workers": w, "batch": b, "prefetch": p}, open(os.path.join(d, "config.json"), "w"))
        ok = replay.run(d, verbose=False)
        wins += ok
        picks[(w, b, p, ok)] = picks.get((w, b, p, ok), 0) + 1
        if a.v:
            print(t, (w, b, p), "PASS" if ok else "FAIL", f"runs used {len(bench.log)}")
        shutil.rmtree(bench.root, ignore_errors=True)
        shutil.rmtree(d, ignore_errors=True)
    print(f"solved {wins}/{a.trials}")
    for k, n in sorted(picks.items(), key=lambda kv: -kv[1]):
        print(f"  {k[:3]} {'PASS' if k[3] else 'FAIL'} x{n}")
