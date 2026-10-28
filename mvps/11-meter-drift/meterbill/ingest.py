"""Called by the ingestion service once per packet, in the order packets arrive.

A packet is one hour of a meter's 15-minute readings:
    {"meter": "MTR-0115", "seq": 5521, "fw": "2.3.0", "sent_ts": 1792519202, "battery_mv": 3610, "rssi": -88,
     "readings": [{"ts": 1792515600, "wh": 212}, ... 4 readings ...]}
Timestamps are Unix seconds from the meter's clock. received_at is our server's clock.
"""
MAX_SKEW = 600  # replay protection: drop packets more than 10 minutes off our clock


def receive(conn, packet, received_at):
    if abs(received_at - packet["sent_ts"]) > MAX_SKEW:
        conn.execute("insert into rejected values (?, ?, ?, ?, ?)",
                     (packet["meter"], packet["seq"], packet["sent_ts"], received_at, "skew"))
        conn.commit()
        return False
    for r in packet["readings"]:
        conn.execute("insert or replace into readings values (?, ?, ?)", (packet["meter"], r["ts"], r["wh"]))
    conn.commit()
    return True
