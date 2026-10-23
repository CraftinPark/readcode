"""Smoke tests: the happy paths. Run with `pytest` from this folder."""
import pytest
from fastapi.testclient import TestClient

from payments import db, webhooks
from payments.app import create_app
from payments.card_network import FakeCardNetwork

ACME = {"Authorization": "Bearer sk_test_acme"}


class Clock:
    def __init__(self):
        self.t = 1_760_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def env(tmp_path):
    path = str(tmp_path / "payments.db")
    db.init(path, accounts=[{"id": "acct_acme", "name": "Acme", "secret_key": "sk_test_acme"}],
            endpoints=[{"id": "we_1", "account_id": "acct_acme", "url": "https://acme.example/hooks", "secret": "whsec_a"}])
    network, clock = FakeCardNetwork(), Clock()
    return TestClient(create_app(path, network, clock)), network, clock, db.connect(path)


def test_charge_and_retry_with_the_same_key(env):
    client, network, _, _ = env
    body = {"amount": 1500, "currency": "usd", "payment_method": "pm_card_visa"}
    first = client.post("/charges", headers={**ACME, "Idempotency-Key": "order-1"}, json=body)
    again = client.post("/charges", headers={**ACME, "Idempotency-Key": "order-1"}, json=body)
    assert first.status_code == 200 and again.json()["id"] == first.json()["id"]
    assert network.total_authorized() == 1500


def test_declined_card(env):
    client, _, _, _ = env
    r = client.post("/charges", headers=ACME, json={"amount": 500, "currency": "usd", "payment_method": "pm_card_declined"})
    assert r.status_code == 402 and r.json()["failure_code"] == "card_declined"


def test_partial_refunds(env):
    client, _, _, _ = env
    ch = client.post("/charges", headers=ACME, json={"amount": 1000, "currency": "usd", "payment_method": "pm_card_visa"}).json()
    assert client.post(f"/charges/{ch['id']}/refunds", headers=ACME, json={"amount": 600}).status_code == 200
    assert client.post(f"/charges/{ch['id']}/refunds", headers=ACME, json={"amount": 600}).status_code == 400
    assert client.post(f"/charges/{ch['id']}/refunds", headers=ACME, json={}).json()["amount"] == 400


def test_webhooks_are_delivered(env):
    client, _, clock, conn = env
    client.post("/charges", headers=ACME, json={"amount": 700, "currency": "usd", "payment_method": "pm_card_visa"})
    sent = []
    assert webhooks.deliver_due(conn, lambda url, body, headers: sent.append(url) or 200, db.now_ms(clock)) == 1
    assert sent == ["https://acme.example/hooks"]
