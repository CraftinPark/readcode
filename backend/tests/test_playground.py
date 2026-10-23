"""The playground must let a candidate reproduce 003's tickets with the shipped code."""
import pytest
from fastapi.testclient import TestClient

from playground import create_playground_app

ACME = {"Authorization": "Bearer sk_test_acme"}
CHARGE = {"amount": 2500, "currency": "usd", "payment_method": "pm_card_visa"}


@pytest.fixture
def pg():
    client = TestClient(create_playground_app())
    sid = client.post("/api/playground/readcode-003/sessions").json()["session"]

    def call(action, **body):
        url = f"/api/playground/sessions/{sid}" + ("" if action == "state" else f"/{action}")
        r = client.get(url) if action == "state" else client.post(url, json=body)
        assert r.status_code == 200, r.text
        return r.json()
    return call


def charge(pg, key="order-88231"):
    return pg("request", path="/charges", headers={**ACME, "Idempotency-Key": key}, body=CHARGE)


def test_ticket_5120_double_charge_reproduces_after_a_timeout(pg):
    pg("faults", timeout_after_charge=True)
    assert charge(pg)["response"]["status"] == 503
    s = charge(pg)
    assert s["response"]["status"] == 200
    assert len(s["tables"]["charges"]) == 1                      # our dashboard: one charge
    assert s["card_network"]["total_authorized"] == 5000         # the bank: two authorizations
    assert any("timed out before answering" in line for line in s["logs"])


def test_crash_then_retry_is_blocked_until_the_claim_times_out(pg):
    pg("faults", crash_after_charge=True)
    assert charge(pg, "k2")["response"]["status"] == 500
    assert charge(pg, "k2")["response"]["status"] == 409          # still in progress
    pg("clock", seconds=61)
    s = charge(pg, "k2")
    assert s["response"]["status"] == 200 and s["card_network"]["total_authorized"] == 5000


def test_ticket_5141_a_4xx_reply_drops_the_webhook(pg):
    charge(pg, "k3")
    s = pg("webhooks/deliver", reply_status=404)
    assert s["webhooks"][0]["reply"] == 404
    pg("clock", seconds=3600)
    s = pg("webhooks/deliver", reply_status=200)
    assert len(s["webhooks"]) == 1                                # never retried


def test_unknown_example_and_session_are_404():
    client = TestClient(create_playground_app())
    assert client.post("/api/playground/readcode-999/sessions").status_code == 404
    assert client.get("/api/playground/sessions/nope").status_code == 404
