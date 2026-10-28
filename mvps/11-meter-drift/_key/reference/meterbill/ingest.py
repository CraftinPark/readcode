"""Called by the ingestion service once per packet, in the order packets arrive.

A packet is one hour of a meter's 15-minute readings:
    {"meter": "MTR-0115", "seq": 5521, "fw": "2.3.0", "sent_ts": 1792519202, "battery_mv": 3610, "rssi": -88,
     "readings": [{"ts": 1792515600, "wh": 212}, ... 4 readings ...]}
Timestamps are Unix seconds from the meter's clock. received_at is our server's clock.
"""


def receive(conn, packet, received_at):
    # Accept late packets (meters buffer through outages; (meter, ts) dedupes redeliveries) and keep both
    # clocks, so billing can correct for meter clocks that drift.
    for r in packet["readings"]:
        conn.execute("insert or replace into readings values (?, ?, ?, ?, ?)",
                     (packet["meter"], r["ts"], r["wh"], packet["sent_ts"], received_at))
    conn.commit()
    return True
