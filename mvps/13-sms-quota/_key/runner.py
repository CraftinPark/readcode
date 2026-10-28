"""Drives a notify/ implementation through simulated traffic, minute by minute (key only).

    python runner.py CODE_DIR WEEKS OUT_JSON [EXPORT_SENDS]
Writes {"delivered": [[t, to, body], ...], "otp": [[t, phone, code], ...], "campaign": [[t, name, n], ...]}.
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
code_dir, weeks, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
sys.path.insert(0, code_dir)
sys.path.insert(1, HERE)
import world  # noqa: E402
from notify import campaigns, db, otp, scheduler  # noqa: E402

client = world.Textly()
conn = sqlite3.connect(":memory:")
db.init(conn)
events = world.workload(weeks)
k, log_otp, log_camp = 0, [], []
end = world.T0 + weeks * world.WEEK
for minute in range(world.T0, end, 60):
    while k < len(events) and events[k][0] < minute + 60:
        e = events[k]
        k += 1
        client.now = e[0]
        if e[1] == "otp":
            log_otp.append([e[0], e[2], e[3]])
            otp.send_otp(client, conn, e[2], e[3], e[0])
        else:
            log_camp.append([e[0], e[2], len(e[3])])
            campaigns.enqueue(conn, e[2], e[3], e[4], e[0])
    client.now = minute + 59
    scheduler.tick(client, conn, minute + 59)
json.dump({"delivered": client.delivered, "otp": log_otp, "campaign": log_camp}, open(out, "w"))
if len(sys.argv) > 4:
    import gzip
    with gzip.open(sys.argv[4], "wt", encoding="utf-8", newline="\n") as f:
        for ts, kind, to, status, headers in conn.execute("select ts, kind, to_number, status, headers from sends "
                                                          "order by id"):
            masked = to[:5] + " ***** " + to[-4:]
            f.write(json.dumps({"ts": ts, "kind": kind, "to": masked, "status": status,
                                "headers": json.loads(headers) if headers else None}, separators=(",", ":")) + "\n")
