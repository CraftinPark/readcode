"""The playground must let a candidate reproduce each ticket with the shipped code."""
import pytest
from fastapi.testclient import TestClient

from playground import create_playground_app

ACME = {"Authorization": "Bearer sk_test_acme"}
ALICE = {"Authorization": "Bearer sk_alice"}
STAFF = {"Authorization": "Bearer sk_admin_ops"}
CHARGE = {"amount": 2500, "currency": "usd", "payment_method": "pm_card_visa"}


def session(example):
    client = TestClient(create_playground_app())
    r = client.post(f"/api/playground/{example}/sessions")
    assert r.status_code == 200, r.text
    sid = r.json()["session"]

    def request(path, headers, body=None, method="POST"):
        r = client.post(f"/api/playground/sessions/{sid}/request", json={"method": method, "path": path, "headers": headers, "body": body})
        assert r.status_code == 200, r.text
        return r.json()

    def act(action, value=None):
        r = client.post(f"/api/playground/sessions/{sid}/act", json={"action": action, "value": value})
        assert r.status_code == 200, r.text
        return r.json()
    return request, act


def panel(state, pid):
    return next(p for p in state["panels"] if p["id"] == pid)["rows"]


def controls(state):
    return [i for g in state["controls"] for i in g["items"]]


# ---- readcode-003 (payments engine)

def test_003_double_charge_reproduces_after_a_timeout():
    request, act = session("readcode-003")
    act("fault:timeout_after_charge", True)
    h = {**ACME, "Idempotency-Key": "order-88231"}
    assert request("/charges", h, CHARGE)["response"]["status"] == 503
    s = request("/charges", h, CHARGE)
    assert s["response"]["status"] == 200
    assert len(panel(s, "charges")) == 1 and len(panel(s, "card")) == 2


def test_003_a_404_reply_drops_the_webhook():
    request, act = session("readcode-003")
    request("/charges", {**ACME, "Idempotency-Key": "k3"}, CHARGE)
    act("deliver:404")
    act("clock:3600")
    s = act("deliver:200")
    assert len(panel(s, "webhooks")) == 1                              # never retried


# ---- marketplace engine

def place(request, items, promo=None):
    s = request("/orders", ALICE, {"restaurant_id": "res_dragon", "promo_code": promo, "items": [{"item_id": i} for i in items]})
    assert s["response"]["status"] == 200, s["response"]
    return s["response"]["body"]["id"]


def test_011_late_payment_event_revives_a_refunded_order():
    request, act = session("readcode-011")
    oid = place(request, ["itm_noodles"])
    s = request(f"/orders/{oid}/cancel", ALICE)
    refund_btn = next(c["id"] for c in controls(s) if "refund.succeeded" in c["label"])
    pay_btn = next(c["id"] for c in controls(s) if "payment.succeeded" in c["label"])
    act(refund_btn)
    s = act(pay_btn)                                                   # delivered last
    order = next(o for o in panel(s, "orders") if o["id"] == oid)
    assert order["payment_status"] == "paid"                           # the bug: refunded was overwritten
    assert any(n["kind"] == "new_order" and n["order_id"] == oid for n in panel(s, "notifications"))


def test_008_restaurant_open_before_opening_after_the_clock_change():
    request, act = session("readcode-008")
    act("set_clock", "2026-11-03T15:30:00Z")                           # 10:30 in Toronto
    names = [r["name"] for r in request("/restaurants?open_now=true", {}, method="GET")["response"]["body"]]
    assert "Dragon Noodle House" in names                              # the bug: open before 11:00


def test_010_cancelled_assigned_orders_keep_couriers_busy():
    request, act = session("readcode-010")
    for _ in range(2):
        oid = place(request, ["itm_noodles"])
        act("deliver_all")
        for step in ("accept", "dispatch"):
            request(f"/admin/orders/{oid}/{step}", STAFF)
        s = request(f"/orders/{oid}/cancel", ALICE)
    assert sum(c["active_jobs"] for c in panel(s, "couriers")) == 2     # the bug: phantom jobs


def test_unknown_example_and_session_are_404():
    client = TestClient(create_playground_app())
    assert client.post("/api/playground/readcode-999/sessions").status_code == 404
    assert client.post("/api/playground/readcode-004/sessions").status_code == 404   # no playground declared
    assert client.get("/api/playground/sessions/nope").status_code == 404
