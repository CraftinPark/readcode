"""Design tool: true acceptance rate (1000 replay episodes) for configs given on the command line as
hz,tau,smoothing triples."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay

if __name__ == "__main__":
    for s in sys.argv[1:]:
        h, t, a = s.split(",")
        r = replay.evaluate(cfg=dict(control_hz=int(h), tilt_filter_tau_s=float(t), action_smoothing=float(a)), procs=12)
        print(replay.report(r), flush=True)
