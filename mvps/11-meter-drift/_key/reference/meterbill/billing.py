"""Time-of-use billing. The billing run calls bill() for each meter at the end of each 4-week period.
Tariff hours are UTC (the utility's whole network runs on UTC)."""
PEAK_HOURS = range(17, 21)
PEAK, OFF_PEAK = 42, 16  # cents per kWh
DAY = 86400


def price(ts):
    return PEAK if (ts % DAY) // 3600 in PEAK_HOURS else OFF_PEAK


def _cost(a, b, wh, start, end):
    """Cents for wh spread evenly over real time [a, b), clipped to [start, end), split at tariff hours."""
    total, t = 0.0, max(a, start)
    stop = min(b, end)
    while t < stop:
        nxt = min(stop, (t // 3600 + 1) * 3600)
        total += wh * (nxt - t) / (b - a) * price(int(t)) / 1000
        t = nxt
    return total


def bill(conn, meter, start, end):
    """Cents owed for meter's consumption in real time [start, end) (Unix seconds).

    Meter clocks drift. A meter's clock offset is received_at - sent_ts on its live packets; buffered packets
    (sent late after an outage) only make that bigger, so the smallest value in a day is the live offset."""
    rows = conn.execute("select ts, wh, sent_ts, received_at from readings where meter = ? and ts >= ? and ts < ?",
                        (meter, start - 2 * DAY, end + 2 * DAY)).fetchall()
    offset = {}
    for _, _, sent, received in rows:
        day = sent // DAY
        offset[day] = min(offset.get(day, 1e18), received - sent)
    total = 0.0
    for ts, wh, sent, _ in rows:
        real = ts + offset[sent // DAY]
        total += _cost(real, real + 900, wh, start, end)
    return round(total)
