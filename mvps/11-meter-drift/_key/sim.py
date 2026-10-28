"""The simulated world behind MVP 11 (key only). 20 smart meters, 15-minute readings, sent in hourly packets.

The hidden truth: meters on firmware 2.1.4 have a real-time clock that runs slow (6-9.4 s/day) and never
resyncs. Their readings are stamped by that clock, so after weeks their intervals sit tens of minutes away
from real time and the evening peak tariff is applied to the wrong quarter-hours. Meters buffer packets
during a cell outage and send them late with their original sent_ts.
"""
import datetime as dt
import random

DAY = 86400
WEEK = 7 * DAY
T0 = int(dt.datetime(2026, 8, 31, tzinfo=dt.timezone.utc).timestamp())  # Monday of week 1
BLOCK = 300
HOURLY_KW = [0.3, 0.3, 0.3, 0.3, 0.3, 0.32, 0.5, 1.1, 1.0, 0.55, 0.55, 0.55, 0.6, 0.55, 0.55, 0.6, 0.9, 2.6,
             2.4, 1.7, 1.4, 0.8, 0.6, 0.4]
DRIFT = {"MTR-0103": 6.0, "MTR-0108": 7.2, "MTR-0114": 8.0, "MTR-0119": 9.4}  # seconds lost per day
SYNC = T0 - 2 * DAY  # drifting meters were last synced at install


def week_start(w):
    return T0 + (w - 1) * WEEK


def at(w, weekday, hh, mm):
    return week_start(w) + weekday * DAY + hh * 3600 + mm * 60


OUTAGES = [  # (district, real start, real end): cell outages; meters buffer and send when back
    ("D4", at(8, 1, 17, 5), at(8, 1, 23, 10)),
    ("D2", at(12, 2, 16, 20), at(12, 2, 22, 40)),
    ("D1", at(17, 3, 15, 50), at(17, 3, 23, 30)),
    ("D4", at(22, 0, 16, 10), at(22, 0, 22, 50)),
    ("D3", at(26, 4, 16, 0), at(26, 4, 23, 0)),
    ("D5", at(30, 1, 16, 30), at(30, 1, 22, 30)),
    ("D2", at(31, 5, 15, 40), at(31, 5, 22, 0)),
]


def price(hour):  # cents per kWh
    return 42 if 17 <= hour < 21 else 16


class Meter:
    def __init__(self, i, days):
        r = random.Random(1000 + i)
        self.id = f"MTR-{101 + i:04d}"
        self.district = f"D{i // 4 + 1}"
        self.fw = "2.1.4" if self.id in DRIFT else r.choice(["2.3.0", "2.3.0", "2.2.7"])
        self.drift = DRIFT.get(self.id, 0.0)
        self.d0 = r.uniform(-3, 3)
        self.scale = round(r.uniform(0.6, 1.6), 2)
        self.origin = T0 - 2 * DAY
        self.blocks = []
        for d in range(days + 4):
            weekday = (d - 2) % 7
            f = r.uniform(0.8, 1.2) * (1.15 if weekday >= 5 else 1)
            for b in range(288):
                kw = HOURLY_KW[b // 12] * self.scale * f * r.uniform(0.85, 1.15)
                self.blocks.append(kw * 1000 * BLOCK / 3600)
        self.cum = [0.0]
        for wh in self.blocks:
            self.cum.append(self.cum[-1] + wh)

    def energy_to(self, t):
        x = (t - self.origin) / BLOCK
        i = int(x)
        return self.cum[i] + (x - i) * self.blocks[i]

    def offset(self, t):  # device clock minus real time, seconds
        return self.d0 - self.drift * (t - SYNC) / DAY

    def real(self, tau):  # real time when the device clock reads tau
        return tau - self.offset(tau)

    def truth_bill(self, start, end):
        i0, i1 = (start - self.origin) // BLOCK, (end - self.origin) // BLOCK
        return sum(self.blocks[i] * price(((self.origin + i * BLOCK) % DAY) // 3600) / 1000 for i in range(i0, i1))


def world(weeks, seed=7):
    """Returns (meters, deliveries) where deliveries = [(received_at, packet)] sorted by received_at."""
    r = random.Random(seed)
    meters = [Meter(i, weeks * 7) for i in range(20)]
    out = []
    for m in meters:
        seq = 4000 + r.randint(0, 3000)
        for h in range(weeks * 7 * 24):
            H = T0 + h * 3600
            readings = []
            for q in range(4):
                tau = H + q * 900
                readings.append({"ts": tau, "wh": round(m.energy_to(m.real(tau + 900)) - m.energy_to(m.real(tau)))})
            sent = H + 3600 + 2
            created = m.real(sent)
            received = created + 0.6 + min(r.expovariate(1 / 4), 50)
            for district, a, b in OUTAGES:
                if district == m.district and a <= created < b:
                    received = b + 20 + (created - a) / 3600 * 1.5 + r.uniform(0, 90)
            seq += 1
            out.append((round(received, 3), {"meter": m.id, "seq": seq, "fw": m.fw, "sent_ts": sent,
                                             "battery_mv": r.randint(3550, 3700), "rssi": r.randint(-108, -71),
                                             "readings": readings}))
    out.sort(key=lambda x: x[0])
    return meters, out
