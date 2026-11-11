import sys, os, time, json, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import lqr
from _sim import robot
import deploy.runner as dr

USE_LQR = os.environ.get("LQR", "1") == "1"
K = lqr.gains()
def lqr_policy(obs):
    return np.tanh(-(obs @ K))
if USE_LQR:
    dr.load_policy = lambda: lqr_policy

def factory(cfg, n):
    return dr.Runner(cfg, n)

def ev(cfg, n=40, seed=0, params=None):
    r = robot.run(factory, n, seed, cfg, params=params or {})
    o = r["outcome"]
    return dict(ok=(o == 0).mean(), fell=(o == 1).mean(), left=(o == 2).mean(), trip=(o == 3).mean(),
                ov=(r["overruns"] / np.maximum(r["ticks"], 1)).mean(), dtau=r["dtau_rms"].mean(),
                pitch=r["pitch_rms"].mean(), d2=r["d2"].mean(), trms=r["tau_rms"].mean())

def job(a):
    cfg, n, params = a
    return cfg, ev(cfg, n, 0, params)

if __name__ == "__main__":
    from multiprocessing import Pool
    params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    grid = json.loads(sys.argv[2]) if len(sys.argv) > 2 else dict(hz=[100, 200, 250, 300], tau=[0.2, 0.5, 2.0], ema=[0.0, 0.5])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    jobs = [(dict(control_hz=h, tilt_filter_tau_s=t, action_smoothing=e), n, params)
            for h in grid["hz"] for t in grid["tau"] for e in grid["ema"]]
    with Pool(12) as pool:
        for cfg, r in pool.imap(job, jobs):
            print(f"hz {cfg['control_hz']:4} tau {cfg['tilt_filter_tau_s']:4} ema {cfg['action_smoothing']:4}: ok {r['ok']:.2f} fell {r['fell']:.2f} trip {r['trip']:.2f} left {r['left']:.2f} ov {r['ov']:.3f} dtau {r['dtau']:6.1f} pitch {r['pitch']:.3f} d2 {r["d2"]:.4f} trms {r["trms"]:.3f}", flush=True)
