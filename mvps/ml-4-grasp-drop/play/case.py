"""Play the case. Needs the case server running (see README.md).

    python case.py start                     # begin; prints the ticket
    python case.py actions                   # what you can do, and what each costs in time
    python case.py do <action> [args]        # e.g.  python case.py do dash grasp_success by site
    python case.py status                    # simulated time, actions used, damage so far
    python case.py causes                    # possible mechanisms and segments
    python case.py submit <change-id> <mechanism-letter> <segment>
                                             # e.g.  submit CH-1234 B "Osaka site"   (or the segment's number)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = os.environ.get("CASE_SERVER", "http://127.0.0.1:8791")
SESSION_FILE = HERE / ".case-session"


def call(path, **body):
    req = urllib.request.Request(SERVER + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(json.loads(e.read()).get("error", str(e)))
    except urllib.error.URLError:
        sys.exit(f"Can't reach the case server at {SERVER}. Is it running?")


def session():
    if not SESSION_FILE.is_file():
        sys.exit("No case started. Run: python case.py start")
    return SESSION_FILE.read_text().strip()


def main(argv):
    cmd, args = (argv[0] if argv else "help"), argv[1:]
    if cmd == "start":
        r = call("/start")
        SESSION_FILE.write_text(r["session"])
        print(r["intro"] + "\n\n" + r["status"] + "\n\nNext: python case.py actions")
    elif cmd == "actions":
        for name, a in call("/actions", session=session())["actions"].items():
            print(f"  {name:<18} {a['minutes']:>3} min  {a['what']}")
    elif cmd == "do":
        if not args:
            sys.exit("Usage: python case.py do <action> [args]")
        print(call("/act", session=session(), action=args[0], args=args[1:])["output"])
    elif cmd == "status":
        print(call("/status", session=session())["status"])
    elif cmd == "causes":
        r = call("/causes", session=session())
        print("Mechanisms:")
        for letter, text in r["causes"].items():
            print(f"  {letter}. {text}")
        print("Segments:")
        for i, s in enumerate(r["segments"], 1):
            print(f"  {i}. {s}")
    elif cmd == "submit":
        if len(args) < 3:
            sys.exit('Usage: python case.py submit <change-id> <mechanism-letter> <segment>   e.g. submit CH-1234 B "Osaka site"')
        answer = {"change": args[0], "mechanism": args[1], "segment": " ".join(args[2:])}
        print(report_text(call("/submit", session=session(), answer=answer)["report"]))
    else:
        print(__doc__)


def report_text(r):
    ok = lambda b: "yes" if b else "no"
    lines = [f"CASE CLOSED. Score: {r['score']}/100", ""]
    lines += [f"  {k:<34} {v}" for k, v in r["parts"].items()]
    d = r["diagnosis"]
    lines += ["", f"Your answer: {r['answer']['change']}, {r['answer']['mechanism']}, {r['answer']['segment']}",
              f"  correct: {r['correct']['change']}, {r['correct']['mechanism']}, {r['correct']['segment']}"
              f"  (points: change {d['change']}/8, mechanism {d['mechanism']}/15, segment {d['segment']}/7)",
              f"  {r['correct']['mechanism']}: {r['mechanism_text']}", "",
              f"Declared resolved: {r['declared'] or 'never'}. Fix held to 17:00: {ok(r['held'])}"
              + (f" (first SLO breach {r['first_breach']})" if r["first_breach"] else ""),
              "Replay from the declaration (or your last action) to 17:00:"]
    lines += ["  " + e for e in r["events"]]
    hdr = ["time", "fleet", "worst group (model)", "paused", "SLO"]
    rows = r["replay"]
    w = [max(len(str(x[i])) for x in [hdr, *rows]) for i in range(len(hdr))]
    lines += ["  " + "  ".join(str(c).ljust(n) for c, n in zip(row, w)) for row in [hdr, *rows]]
    lines += ["", f"Failed grasps today: {r['failed_grasps']:,}" + (f" (+{r['lost_picks']:,} picks lost to pauses)" if r["lost_picks"] else ""),
              f"  avoidable: {r['excess']:,} (an expert path: about {r['expert_excess']:,})",
              f"GPU spent: ${r['compute']:,}",
              "Judgement penalties: " + ("none" if not r["penalties"] else ""),
              *["  - " + p for p in r["penalties"]],
              "", "Your path:"]
    lines += [f"  {a['at']}  {a['action']} {' '.join(a['args'])}" for a in r["actions"]]
    return "\n".join(lines)


if __name__ == "__main__":
    main(sys.argv[1:])
