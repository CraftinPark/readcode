"""Time-of-use billing. The billing run calls bill() for each meter at the end of each 4-week period.
Tariff hours are UTC (the utility's whole network runs on UTC)."""
PEAK_HOURS = range(17, 21)
PEAK, OFF_PEAK = 42, 16  # cents per kWh


def price(ts):
    return PEAK if (ts % 86400) // 3600 in PEAK_HOURS else OFF_PEAK


def bill(conn, meter, start, end):
    """Cents owed for meter's consumption in [start, end) (Unix seconds)."""
    rows = conn.execute("select ts, wh from readings where meter = ? and ts >= ? and ts < ?", (meter, start, end))
    return round(sum(wh * price(ts) / 1000 for ts, wh in rows))
