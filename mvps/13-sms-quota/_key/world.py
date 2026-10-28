"""The world behind MVP 13 (key only): Textly, our SMS provider, and our traffic.

Hidden truth: Textly caps each account at 10,000 messages per UTC day; past that it answers 429 until midnight.
Login codes (OTP) and marketing campaigns share the account. OTPs are flat (~3,000/day); the Tuesday campaign
grows 7% a week. In the 6 weeks the player sees, the cap is never hit: the only trace is the
X-RateLimit-Remaining response header we log, which sinks lower every Tuesday (to a few hundred by week 6).
From week 7-8 on, the Tuesday blast eats the quota and every login code after it fails until midnight.
Nothing in the code, docs or ticket mentions a cap.
"""
import datetime as dt
import random

DAY = 86400
WEEK = 7 * DAY
T0 = int(dt.datetime(2026, 9, 14, tzinfo=dt.timezone.utc).timestamp())  # Monday of week 1
CAP = 10000
VISIBLE_WEEKS = 6
REPLAY_WEEKS = 12
HOURLY_OTP = [1, 0.6, 0.4, 0.3, 0.3, 0.5, 1.4, 3.2, 5.0, 5.6, 5.4, 5.2, 5.6, 5.4, 5.0, 4.8, 4.9, 5.2, 5.8, 6.2,
              6.0, 5.2, 3.6, 2.0]


class Timeout(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, headers):
        super().__init__("429 Too Many Requests")
        self.headers = headers


class Textly:
    """Simulated provider. Records every delivered message in self.delivered as (t, to, body)."""
    Timeout = Timeout
    RateLimited = RateLimited

    def __init__(self, seed=3):
        self.r = random.Random(seed)
        self.day = None
        self.used = 0
        self.refs = {}
        self.delivered = []
        self.now = 0
        self.n = 0

    def _roll(self):
        d = self.now // DAY
        if d != self.day:
            self.day, self.used = d, 0

    def _headers(self):
        self.n += 1
        return {"X-Request-Id": f"tx_{self.n:08x}", "X-RateLimit-Remaining": str(max(0, CAP - self.used)),
                "X-Textly-Region": "eu-2", "Content-Type": "application/json"}

    def send(self, to, body, client_ref=None):
        self._roll()
        if client_ref is not None and client_ref in self.refs and self.now - self.refs[client_ref][1] < DAY:
            return {"id": self.refs[client_ref][0], "status": "queued", "headers": self._headers()}
        if self.used >= CAP:
            h = self._headers()
            h["Retry-After"] = str(DAY - self.now % DAY)
            raise RateLimited(h)
        roll = self.r.random()
        if roll < 0.004:  # timed out before Textly accepted it
            raise Timeout("read timeout after 5s")
        self.used += 1
        mid = f"msg_{self.r.getrandbits(40):010x}"
        if client_ref is not None:
            self.refs[client_ref] = (mid, self.now)
        self.delivered.append((self.now, to, body))
        if roll < 0.016:  # accepted and delivered, but our side timed out waiting for the answer
            raise Timeout("read timeout after 5s")
        return {"id": mid, "status": "queued", "headers": self._headers()}


def phone(r):
    return "+44 7" + "".join(str(r.randint(0, 9)) for _ in range(9))


def workload(weeks, seed=13):
    """[(t, 'otp', phone, code)] and [(t, 'campaign', name, [phones], body)], time-sorted together."""
    r = random.Random(seed)
    events = []
    for d in range(weeks * 7):
        day0 = T0 + d * DAY
        n = int(3000 * r.uniform(0.93, 1.07) * (1.08 if d % 7 >= 5 else 1))
        total = sum(HOURLY_OTP)
        for _ in range(n):
            h = r.choices(range(24), weights=HOURLY_OTP)[0]
            t = day0 + h * 3600 + r.randint(0, 3599)
            events.append((t, "otp", phone(r), f"{r.randint(0, 999999):06d}"))
        week = d // 7 + 1
        size = 4600 * 1.07 ** (week - 1)
        if d % 7 == 1:
            name, size = f"tue-w{week}", int(size)
        elif d % 7 == 3:
            name, size = f"thu-w{week}", int(size * 0.6)
        else:
            continue
        body = r.choice(["Autumn sale: 20% off everything this week.", "New in: winter collection. Shop now.",
                         "Your points expire soon - use them today.", "Free delivery this weekend only."])
        events.append((day0 + 10 * 3600, "campaign", name, [phone(r) for _ in range(size)], body))
    events.sort(key=lambda e: e[0])
    return events
