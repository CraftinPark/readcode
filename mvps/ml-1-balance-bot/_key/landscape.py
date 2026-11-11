"""Success map over a config grid for a given set of hidden robot parameters (design tool)."""
import sys, os, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import explore

def job(a):
    cfg, n, params, seed = a
    return cfg, explore.ev(cfg, n, seed, params)

if __name__ == "__main__":
    from multiprocessing import Pool
    params = json.loads(sys.argv[1])
    grid = json.loads(sys.argv[2])
    n = int(sys.argv[3]); out = sys.argv[4]
    jobs = [(dict(control_hz=h, tilt_filter_tau_s=t, action_smoothing=e), n, params, 1)
            for h in grid["hz"] for t in grid["tau"] for e in grid["ema"]]
    res = []
    t0 = time.time()
    with Pool(12) as pool:
        for cfg, r in pool.imap_unordered(job, jobs):
            res.append(dict(cfg=cfg, **{k: float(v) for k, v in r.items()}))
    json.dump(dict(params=params, res=res), open(out, "w"))
    print(f"{len(res)} configs in {time.time()-t0:.0f}s")
    for hz in grid["hz"]:
        print(f"hz {hz}: rows tau, cols ema {grid['ema']}")
        for t in grid["tau"]:
            row = []
            for e in grid["ema"]:
                r = [x for x in res if x["cfg"]["control_hz"] == hz and x["cfg"]["tilt_filter_tau_s"] == t and x["cfg"]["action_smoothing"] == e][0]
                tag = "T" if r["trip"] > r["left"] else "L"
                row.append(f"{int(round(r["ok"]*100)):3d}{tag if r["ok"]<0.97 else "*"}{r.get("trms",0):.2f}")
            print(f"  tau {t:4}: " + " ".join(row))
