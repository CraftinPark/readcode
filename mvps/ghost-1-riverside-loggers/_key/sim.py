"""The world behind ghost-1 (never shown to the player).

24 water meters in two zones. 16 have the old LX-2 logger: a 16-bit pulse counter, one pulse per 1.062 litres
(LF). That calibration is the real reason for `lf = 1.062` in wfl/bx.py. 8 meters in the new Riverside
development (zone E, from Mon 5 Oct 2026) have the BX logger: a 32-bit register in whole litres. Both send one
reading per hour. Loggers get new batteries now and then; the counter restarts at 0.

Truth: the litres each customer really used, attributed to the hourly reading that closes the hour. A logger's
first reading is sent the moment it is installed (nothing used yet).
"""
import datetime as _dt
import random

LF = 1.062
H = 3600
DAY = 86400
T0 = 1780272000            # Mon 1 Jun 2026 00:00 UTC, first reading in data/
RIVERSIDE = 1791158400     # Mon 5 Oct 2026 00:00 UTC, BX loggers installed, water on
T_DATA = 1793145600        # Wed 28 Oct 2026 00:00 UTC, "today": data/ holds readings before this
T_END = 1809129600 + DAY   # replay runs to Sun 2 May 2027


def ts(s):
    return int(_dt.datetime.fromisoformat(s).replace(tzinfo=_dt.timezone.utc).timestamp())


# Hourly shape of household use (UTC; the town is UTC+1/+2, close enough for a shape).
SHAPE_HOME = [1, 1, 1, 1, 2, 6, 10, 9, 6, 4, 3, 3, 4, 3, 3, 3, 4, 7, 9, 8, 6, 4, 3, 2]
SHAPE_SHOP = [0, 0, 0, 0, 0, 0, 2, 6, 8, 9, 9, 9, 9, 9, 9, 9, 8, 7, 5, 2, 1, 0, 0, 0]


class Meter:
    def __init__(self, mid, zone, model, hw, since, per_day, shape, swaps, seed):
        self.id, self.zone, self.model, self.hw, self.since = mid, zone, model, hw, since
        self.per_day, self.shape, self.swaps = per_day, shape, sorted(swaps)
        self.rng = random.Random(seed)
        self.start_counter = self.rng.randrange(0, 60000) if model == "LX-2" else 0

    def hourly(self, t):
        """True litres used in the hour [t, t+H)."""
        wd = _dt.datetime.fromtimestamp(t, _dt.timezone.utc).weekday()
        shape = self.shape
        w = shape[(t // H) % 24] / sum(shape)
        mean = self.per_day * w * (1.15 if wd >= 5 and shape is SHAPE_HOME else 1.0)
        mean *= 0.85 if wd == 6 and shape is SHAPE_SHOP else 1.0
        v = self.rng.gauss(mean, mean * 0.35 + 1)
        return max(0, int(round(v)))


def meters():
    m = []
    seed = 11
    w_days = [210, 260, 330, 380, 420, 300, 510, 240, 360, 290]
    for i, pd in enumerate(w_days):
        m.append(Meter(f"W-{101 + i:04d}", "W", "LX-2", f"{0x2a31 + 7 * i:04x}", T0, pd, SHAPE_HOME,
                       [], seed + i))
    m[3].swaps = [ts("2026-08-19T10:00")]
    m[6].swaps = [ts("2027-01-12T09:00")]
    m.append(Meter("W-0111", "W", "LX-2", "3b07", T0, 1100, SHAPE_SHOP, [ts("2026-12-03T14:00")], 31))
    e_days = [280, 350, 410, 230, 470]
    for i, pd in enumerate(e_days):
        m.append(Meter(f"E-{201 + i:04d}", "E", "LX-2", f"{0x4c10 + 5 * i:04x}", T0, pd, SHAPE_HOME,
                       [], 41 + i))
    m[13].swaps = [ts("2026-09-28T11:00"), ts("2027-03-09T15:00")]
    rv = [("R-0301", 380, SHAPE_HOME, ["2027-04-13T10:00"]),
          ("R-0302", 290, SHAPE_HOME, []),
          ("R-0303", 450, SHAPE_HOME, ["2026-10-19T09:00"]),
          ("R-0304", 330, SHAPE_HOME, []),
          ("R-0305", 520, SHAPE_HOME, ["2027-04-20T08:00"]),
          ("R-0306", 260, SHAPE_HOME, []),
          ("R-0307", 1900, SHAPE_SHOP, ["2027-02-16T13:00"]),   # cafe
          ("R-0308", 4200, SHAPE_SHOP, ["2027-01-19T10:00"])]   # launderette
    for i, (mid, pd, shape, sw) in enumerate(rv):
        m.append(Meter(mid, "E", "BX", f"BX-77A{i + 1:02d}", RIVERSIDE, pd, shape, [ts(s) for s in sw], 61 + i))
    return m


def run(t_end=T_END):
    """Returns (meters, packets, truth, bulk).
    packets: [rx, packet] in arrival order. truth: {meter: [(reading_ts, litres)]}. bulk: {(zone, hour): litres}."""
    ms = meters()
    packets, truth, bulk = [], {}, {}
    prng = random.Random(5)
    tests = {ts("2026-07-14T10:00"): "2a46", ts("2026-09-02T13:00"): "4c19", ts("2027-02-03T11:00"): "2a38"}
    for m in ms:
        cum = 0.0          # litres since the counter last restarted
        swaps = list(m.swaps)
        tr = truth.setdefault(m.id, [])
        t = m.since
        if m.model == "LX-2":
            cum = m.start_counter * LF
        while t < t_end:
            # reading at t closes the hour [t-H, t)
            if t > m.since:
                used = m.hourly(t - H)
                cum += used
                bulk[(m.zone, t - H)] = bulk.get((m.zone, t - H), 0) + used
                tr.append((t, used))
            if m.model == "LX-2":
                c = int(cum / LF) % 65536
                rx = t + prng.randint(2, 25)
                pk = {"gw": f"lw-{ord(m.hw[0]) % 4 + 1:02d}", "rx": rx,
                      "hex": f"{int(m.hw, 16):04x}{t:08x}{c:04x}{1 if prng.random() < 0.01 else 0:02x}"}
            else:
                c = int(cum) % (1 << 32)
                rx = t + prng.randint(5, 90)
                iso = _dt.datetime.fromtimestamp(t, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                pk = {"gw": "nb-iot", "rx": rx,
                      "body": {"dev": m.hw, "ts": iso, "vol": c, "bat": round(3.62 - (t - m.since) / 3e8, 2)}}
            packets.append([rx, pk])
            if swaps and t >= swaps[0]:
                swaps.pop(0)
                cum = 0.0
            if m.model == "LX-2" and t in tests and tests[t] == m.hw:
                fake = {"gw": "lw-01", "rx": t + 300,
                        "hex": f"{int(m.hw, 16):04x}{t + 300:08x}{0xffff:04x}{0x41:02x}"}
                packets.append([t + 300, fake])
            t += H
    packets.sort(key=lambda p: p[0])
    return ms, packets, truth, bulk


def truth_bill(truth, mid, a, b):
    """Litres really used in the hours closed by readings a <= ts < b."""
    return sum(u for t, u in truth[mid] if a <= t < b)
