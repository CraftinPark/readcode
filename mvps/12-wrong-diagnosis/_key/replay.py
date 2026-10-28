"""Hidden replay, run AFTER the player says "resolved" (never shown to the player): November 2026 in
production. Starting from the 28 Oct snapshot, Bundlr webhooks arrive when they really arrive and the renewal job
runs every hour until 1 Dec. Every subscription whose renewal falls in November must end up with the right net charge.

    python _key/replay.py --code DIR
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world  # noqa: E402

RUNNER = r'''
import json, sqlite3, sys
from subs import billing, webhooks
sys.path.insert(0, sys.argv[1])
import world
conn, future = world.build()
k, t = 0, world.NOW
while t < world.DEC1 + 2 * 86400:
    while k < len(future) and future[k]["received_at"] <= t:
        webhooks.handle_reseller_event(conn, future[k]); k += 1
    if t < world.DEC1:
        billing.run_renewals(conn, t)
    t += 3600
net = dict(conn.execute("select sub_id, sum(case kind when 'refund' then -amount_cents else amount_cents end) "
                        "from charges where at >= ? group by sub_id", (world.NOW,)).fetchall())
print(json.dumps(net))
'''


def run(code_dir, verbose=True):
    conn, future = world.build()
    truth = world.truth(conn, future)
    scored = {sid: (st, pe) for sid, st, pe in conn.execute("select id, status, period_end from subscriptions")
              if pe < world.DEC1}
    r = subprocess.run([sys.executable, "-c", RUNNER, HERE], cwd=code_dir, capture_output=True, text=True,
                       timeout=900)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return 0, len(scored)
    net = {int(k): v for k, v in json.loads(r.stdout.strip().splitlines()[-1]).items()}
    ok, wrong = 0, {}
    for sid, (st, _) in scored.items():
        if net.get(sid, 0) == truth[sid]:
            ok += 1
        else:
            key = (st, "overcharged" if net.get(sid, 0) > truth[sid] else "not charged")
            wrong[key] = wrong.get(key, 0) + 1
    if verbose:
        for (st, how), n in sorted(wrong.items()):
            print(f"  FAIL {n:4d} '{st}' subscriptions {how}")
        print(f"replay: {ok}/{len(scored)} subscriptions billed right")
    return ok, len(scored)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    ok, total = run(ap.parse_args().code)
    sys.exit(0 if ok == total else 1)
