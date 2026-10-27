"""A body run as a backend. 30 ticks; an infection (traffic spike + errors) and an injury (outage) hit it.

    python body.py                 # run with body.json
    python body.py --config my.json --verbose

Organ        -> backend concept
lungs        -> ingress: oxygen arrives as requests
liver        -> cache: serves some requests without the heart
heart        -> worker pool: pumps (processes) requests; capacity costs nutrients
blood vessels-> queue: requests waiting for the heart
immune system-> error handling: retries and timeouts
"""
import argparse
import json
import statistics

TICKS = 30
BASE_DEMAND = 100
INFECTION = range(12, 18)   # traffic x2.5, 25% of processed requests fail
INJURY = range(22, 25)      # half the heart is down
BUDGET = 400.0
OXYGEN_VALUE = [1.0, 0.8, 0.4, 0.0]  # by ticks waited: 0, 1, 2, 3+ (latency)              # nutrients per tick a healthy body can afford

KNOBS = {
    "heart_capacity": (10, 400),     # requests the heart can process per tick
    "vessel_queue": (0, 2000),       # requests that can wait
    "timeout_ticks": (1, 10),        # a waiting request older than this is lost (tissue starves)
    "retry_limit": (0, 5),           # immune retries per failed request
    "liver_cache": (0, 300),         # cache size; hit rate = cache / (cache + 100) * 0.6
    "autoscale_threshold": (0, 2000) # 0 = off; else add 50% capacity next tick when the queue is longer than this
}


def load(path):
    cfg = json.load(open(path))
    for k, (lo, hi) in KNOBS.items():
        v = cfg[k]
        if not lo <= v <= hi:
            raise SystemExit(f"{k}={v} out of range [{lo}, {hi}]")
    return cfg


def simulate(cfg, verbose=False):
    queue = []          # (born_tick, attempt)
    delivered_total = demand_total = lost_total = 0
    cost_total = 0.0
    ratios = []
    boost = 0
    retry_next = []
    hit_rate = cfg["liver_cache"] / (cfg["liver_cache"] + 100) * 0.6
    for t in range(TICKS):
        demand = int(BASE_DEMAND * (2.5 if t in INFECTION else 1))
        err = 0.25 if t in INFECTION else 0.02
        demand_total += demand
        cached = int(demand * hit_rate)
        arrivals = [(t, 0)] * (demand - cached) + retry_next
        retry_next = []

        cap = cfg["heart_capacity"] + boost
        if t in INJURY:
            cap //= 2
        cost_total += cfg["heart_capacity"] + boost + 0.3 * cfg["liver_cache"]

        queue.extend(arrivals)
        fresh = [r for r in queue if t - r[0] < cfg["timeout_ticks"]]
        lost = len(queue) - len(fresh)
        queue = fresh
        work, queue = queue[:cap], queue[cap:]
        if len(queue) > cfg["vessel_queue"]:
            lost += len(queue) - cfg["vessel_queue"]
            queue = queue[:cfg["vessel_queue"]]

        ok = 0.0
        for i, (born, attempt) in enumerate(work):
            failed = (i * 7919 + t * 104729) % 1000 < err * 1000   # deterministic "random"
            if not failed:
                ok += OXYGEN_VALUE[min(t - born, 3)]   # late oxygen is worth less
            elif attempt < cfg["retry_limit"]:
                retry_next.append((born, attempt + 1))
            else:
                lost += 1
        delivered = ok + cached
        delivered_total += delivered
        lost_total += lost
        ratios.append(min(1.0, delivered / demand))
        th = cfg["autoscale_threshold"]
        boost = cfg["heart_capacity"] // 2 if th and len(queue) > th else 0
        if verbose:
            print(f"t={t:2d} demand={demand:3d} cached={cached:3d} cap={cap:3d} delivered={delivered:5.1f} queue={len(queue):4d} lost={lost:3d}")

    health = delivered_total / demand_total
    cost = cost_total / (BUDGET * TICKS)
    stability = 1 - statistics.pstdev(ratios)
    score = 100 * (0.5 * health + 0.25 * max(0.0, 1 - cost) + 0.25 * stability)
    return {"health": round(health, 3), "cost_vs_budget": round(cost, 3), "stability": round(stability, 3),
            "lost": lost_total, "score": round(score, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="body.json")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    print(json.dumps(simulate(load(a.config), a.verbose), indent=2))
