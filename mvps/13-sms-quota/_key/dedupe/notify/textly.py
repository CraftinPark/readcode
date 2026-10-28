"""Thin client for Textly's REST API (https://api.textly.example/v2). Production builds one TextlyClient at startup
and passes it to otp.send_otp and scheduler.tick.

    client.send(to, body, client_ref=None) -> {"id": "msg_...", "status": "queued", "headers": {...}}

client_ref is an optional idempotency key: Textly ignores a repeat of the same client_ref within 24 h and returns
the original message id. Errors are raised as client.Timeout (no answer within 5 s; the message may or may not
have been accepted) and client.RateLimited (HTTP 429; .headers has the response headers).
"""
import json
import urllib.error
import urllib.request


class Timeout(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, headers):
        super().__init__("429 Too Many Requests")
        self.headers = headers


class TextlyClient:
    Timeout = Timeout
    RateLimited = RateLimited

    def __init__(self, api_key, base="https://api.textly.example/v2"):
        self.api_key, self.base = api_key, base

    def send(self, to, body, client_ref=None):
        payload = {"to": to, "body": body, "sender": "Shopwell"}
        if client_ref:
            payload["client_ref"] = client_ref
        req = urllib.request.Request(self.base + "/messages", data=json.dumps(payload).encode(),
                                     headers={"Authorization": "Bearer " + self.api_key,
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return dict(json.load(resp), headers=dict(resp.headers))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimited(dict(e.headers))
            raise
        except TimeoutError:
            raise Timeout("read timeout after 5s")
