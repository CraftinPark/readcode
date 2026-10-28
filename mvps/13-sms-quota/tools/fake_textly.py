"""A local stand-in for Textly, for tests: accepts everything, honours client_ref, and can be told to time out
after accepting (which is what Textly does under load: the message goes out, the answer doesn't come back)."""
import itertools

from notify.textly import RateLimited, Timeout


class FakeTextly:
    Timeout = Timeout
    RateLimited = RateLimited

    def __init__(self, timeout_after_accept=()):
        self.timeout_after_accept = set(timeout_after_accept)  # phone numbers whose first send times out
        self.sent = []
        self.refs = {}
        self.ids = itertools.count(1)

    def send(self, to, body, client_ref=None):
        if client_ref is not None and client_ref in self.refs:
            return {"id": self.refs[client_ref], "status": "queued", "headers": {}}
        mid = f"msg_{next(self.ids):06d}"
        self.sent.append((to, body))
        if client_ref is not None:
            self.refs[client_ref] = mid
        if to in self.timeout_after_accept:
            self.timeout_after_accept.discard(to)
            raise Timeout("read timeout after 5s")
        return {"id": mid, "status": "queued", "headers": {"X-Request-Id": "fake-" + mid}}
