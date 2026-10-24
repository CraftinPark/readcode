"""Gate tests for the marketplace problems. $READCODE_ROOT is the folder holding
the `market` package under test (a baseline or a shipped variant).

t0 must pass on the clean code and on every variant. Each p# test reproduces one
customer-facing symptom: it must pass on the clean code and fail on that
problem's variant.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.environ["READCODE_ROOT"])

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from market import db  # noqa: E402
from market.app import create_app  # noqa: E402
from market.providers import FakeProvider  # noqa: E402
from market.seed import ADMIN_KEY, SEED  # noqa: E402

ALICE = {"Authorization": "Bearer sk_alice"}
STAFF = {"Authorization": f"Bearer {ADMIN_KEY}"}
DAY = 86400


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc).timestamp()


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def env(tmp_path):
    path = str(tmp_path / "market.db")
    db.init(path, SEED)
    clock = Clock(utc(2026, 10, 14, 16, 0))           # Wednesday, noon in Toronto, before the clocks change
    provider = FakeProvider(clock=clock)
    return TestClient(create_app(path, provider, clock)), provider, clock, db.connect(path)


def order(client, items, promo=None, restaurant="res_dragon"):
    r = client.post("/orders", headers=ALICE, json={"restaurant_id": restaurant, "promo_code": promo,
                                                     "items": [{"item_id": i} for i in items]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def deliver(client, provider, kinds=None):
    """Deliver queued provider events, optionally only some types, in the order given."""
    for kind in kinds or [None]:
        for event in list(provider.outbox):
            if kind is None or event["type"] == kind:
                assert client.post("/webhooks/provider", json=event).status_code == 200
                provider.acknowledge(event["id"])


def staff(client, oid, *steps):
    for step in steps:
        r = client.post(f"/admin/orders/{oid}/{step}", headers=STAFF)
        assert r.status_code == 200, (step, r.text)


def test_t0_ordinary_flow(env):
    client, provider, clock, conn = env
    a = order(client, ["itm_noodles", "itm_dumplings"], promo="SAVE10")
    deliver(client, provider)
    staff(client, a, "accept", "dispatch", "picked_up", "delivered")
    b = order(client, ["itm_noodles"])
    assert client.post(f"/orders/{b}/cancel", headers=ALICE).status_code == 200        # cancelled before dispatch
    deliver(client, provider)
    assert client.get(f"/orders/{b}", headers=ALICE).json()["payment_status"] == "refunded"
    assert client.get("/admin/reconciliation", headers=STAFF).json()["mismatched"] == []
    assert [r["name"] for r in client.get("/restaurants?open_now=true").json()] == ["Dragon Noodle House"]
    assert len(client.get("/admin/couriers", headers=STAFF).json()["available"]) == 2
    clock.t += 7 * DAY
    (p,) = client.post("/admin/payouts/run", headers=STAFF).json()
    assert p["gross"] == 2545 - 255 and p["refunds"] == 0


def test_p1_promo_discount_is_fully_shared_across_lines(env):
    """Finance: some promo orders are a few cents off in reconciliation."""
    client, provider, clock, conn = env
    oid = order(client, ["itm_bao", "itm_rolls", "itm_soup"], promo="SAVE10")
    o = client.get(f"/orders/{oid}", headers=ALICE).json()
    assert sum(l["discount"] for l in o["lines"]) == o["discount"]
    assert client.get("/admin/reconciliation", headers=STAFF).json()["mismatched"] == []


def test_p2_opening_hours_follow_the_clock_change(env):
    """Restaurant: since the clocks went back, orders arrive before we open."""
    client, provider, clock, conn = env
    clock.t = utc(2026, 11, 3, 15, 30)                 # 10:30 in Toronto on the Tuesday after the change
    assert "Dragon Noodle House" not in [r["name"] for r in client.get("/restaurants?open_now=true").json()]
    clock.t = utc(2026, 11, 4, 2, 30)                  # 21:30 in Toronto, still open
    assert "Dragon Noodle House" in [r["name"] for r in client.get("/restaurants?open_now=true").json()]


def test_p3_refunds_pending_at_payout_time_are_deducted(env):
    """Finance: restaurants were paid in full for items we refunded to customers."""
    client, provider, clock, conn = env
    oid = order(client, ["itm_noodles", "itm_bao"])
    deliver(client, provider)
    staff(client, oid, "accept", "dispatch", "picked_up", "delivered")
    clock.t += 6 * DAY
    assert client.post(f"/admin/orders/{oid}/refund", headers=STAFF, json={"amount": 335}).status_code == 200
    clock.t += 1 * DAY                                 # the weekly payout runs before the provider confirms
    (week1,) = client.post("/admin/payouts/run", headers=STAFF).json()
    clock.t += 1 * DAY
    deliver(client, provider)                          # refund.succeeded arrives
    clock.t += 6 * DAY
    later = client.post("/admin/payouts/run", headers=STAFF).json()
    assert week1["refunds"] + sum(p["refunds"] for p in later) == 335


def test_p4_cancelling_an_assigned_order_frees_the_courier(env):
    """Dispatch: through the evening fewer and fewer couriers are available."""
    client, provider, clock, conn = env
    for _ in range(2):
        oid = order(client, ["itm_noodles"])
        deliver(client, provider)
        staff(client, oid, "accept", "dispatch")
        assert client.post(f"/orders/{oid}/cancel", headers=ALICE).status_code == 200
    couriers = client.get("/admin/couriers", headers=STAFF).json()
    assert all(c["active_jobs"] == 0 for c in couriers["all"])
    assert len(couriers["available"]) == 2


def test_p5_a_late_payment_event_does_not_revive_a_refunded_order(env):
    """Restaurant: we cooked an order the customer had cancelled and been refunded for."""
    client, provider, clock, conn = env
    oid = order(client, ["itm_noodles"])               # payment still processing
    assert client.post(f"/orders/{oid}/cancel", headers=ALICE).status_code == 200
    deliver(client, provider, kinds=["refund.succeeded", "payment.succeeded"])   # provider delivers out of order
    o = client.get(f"/orders/{oid}", headers=ALICE).json()
    assert o["payment_status"] == "refunded"
    kinds = [r["kind"] for r in conn.execute("SELECT kind FROM notifications WHERE order_id = ?", (oid,))]
    assert "new_order" not in kinds
