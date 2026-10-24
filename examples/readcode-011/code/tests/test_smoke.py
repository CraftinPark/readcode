"""Happy-path tests. Run with `pytest` from this folder."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from market import db
from market.app import create_app
from market.providers import FakeProvider
from market.seed import ADMIN_KEY, SEED

ALICE = {"Authorization": "Bearer sk_alice"}
STAFF = {"Authorization": f"Bearer {ADMIN_KEY}"}
NOON_TORONTO = datetime(2026, 10, 14, 16, 0, tzinfo=timezone.utc).timestamp()   # a Wednesday


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def env(tmp_path):
    path = str(tmp_path / "market.db")
    db.init(path, SEED)
    clock = Clock(NOON_TORONTO)
    provider = FakeProvider(clock=clock)
    client = TestClient(create_app(path, provider, clock))
    return client, provider, clock


def deliver_all(client, provider):
    for event in list(provider.outbox):
        if client.post("/webhooks/provider", json=event).status_code == 200:
            provider.acknowledge(event["id"])


def test_order_is_paid_cooked_and_delivered(env):
    client, provider, _ = env
    order = client.post("/orders", headers=ALICE, json={"restaurant_id": "res_dragon",
                                                         "items": [{"item_id": "itm_noodles", "quantity": 2}]}).json()
    assert order["payment_status"] == "pending"
    deliver_all(client, provider)
    for step in ("accept", "dispatch", "picked_up", "delivered"):
        assert client.post(f"/admin/orders/{order['id']}/{step}", headers=STAFF).status_code == 200
    assert client.get(f"/orders/{order['id']}", headers=ALICE).json()["status"] == "delivered"


def test_promo_discount(env):
    client, _, _ = env
    q = client.post("/quote", headers=ALICE, json={"restaurant_id": "res_dragon", "promo_code": "save10",
                                                   "items": [{"item_id": "itm_noodles", "quantity": 1}]}).json()
    assert q["discount"] == 145 and q["total"] == 1450 - 145 + 399 + q["tax"]


def test_closed_restaurant_rejects_orders(env):
    client, _, _ = env
    r = client.post("/orders", headers=ALICE, json={"restaurant_id": "res_slice", "items": [{"item_id": "itm_pep"}]})
    assert r.status_code == 400 and "closed" in r.json()["detail"]["message"]


def test_cancel_refunds_the_order(env):
    client, provider, _ = env
    order = client.post("/orders", headers=ALICE, json={"restaurant_id": "res_dragon",
                                                         "items": [{"item_id": "itm_bao"}]}).json()
    deliver_all(client, provider)
    assert client.post(f"/orders/{order['id']}/cancel", headers=ALICE).json()["status"] == "cancelled"
    deliver_all(client, provider)
    assert client.get(f"/orders/{order['id']}", headers=ALICE).json()["payment_status"] == "refunded"


def test_weekly_payout(env):
    client, provider, clock = env
    order = client.post("/orders", headers=ALICE, json={"restaurant_id": "res_dragon",
                                                         "items": [{"item_id": "itm_noodles"}]}).json()
    deliver_all(client, provider)
    for step in ("accept", "dispatch", "picked_up", "delivered"):
        client.post(f"/admin/orders/{order['id']}/{step}", headers=STAFF)
    clock.t += 7 * 86400
    (payout,) = client.post("/admin/payouts/run", headers=STAFF).json()
    assert payout["gross"] == 1450 and payout["amount"] == 1450 - 290
