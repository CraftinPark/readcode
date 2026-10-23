"""Gate tests for readcode-002. The unit under test is the file in $READCODE_UNIT.

t0 checks ordinary behaviour and must pass on both the baseline and the shipped
code. Each B# test checks one business rule: it must pass on the baseline and
fail on the shipped code (run_gates.py enforces both).
"""
import importlib.util
import os
import sys

import pytest
from fastapi.testclient import TestClient

_spec = importlib.util.spec_from_file_location("unit", os.environ["READCODE_UNIT"])
unit = importlib.util.module_from_spec(_spec)
sys.modules["unit"] = unit                      # dataclasses and pydantic look the module up by name
_spec.loader.exec_module(unit)

A = {"Authorization": "Bearer sk_test_acme"}
B = {"Authorization": "Bearer sk_test_globex"}


@pytest.fixture
def client():
    store = unit.Store([unit.Account("acct_acme", "Acme", "sk_test_acme"),
                        unit.Account("acct_globex", "Globex", "sk_test_globex")])
    return TestClient(unit.create_app(store))


def charge(client, headers, amount=1000, key=None, **extra):
    h = dict(headers, **({"Idempotency-Key": key} if key else {}))
    return client.post("/charges", headers=h, json={"amount": amount, "currency": "usd",
                                                    "payment_method": "pm_card_visa", **extra})


def test_t0_ordinary_flow(client):
    assert client.get("/charges", headers={}).status_code == 401
    c = charge(client, A, 2000, key="order-1").json()
    assert c["status"] == "succeeded" and c["amount"] == 2000
    assert charge(client, A, 2000, key="order-1").json()["id"] == c["id"]          # replay
    assert charge(client, A, 999, key="order-1").status_code == 409                 # same key, new body
    assert client.post("/charges", headers=A, json={"amount": 500, "currency": "usd",
                                                    "payment_method": "pm_card_declined"}).status_code == 402
    assert client.get(f"/charges/{c['id']}", headers=A).json()["id"] == c["id"]
    r = client.post(f"/charges/{c['id']}/refunds", headers=A, json={"amount": 500})
    assert r.status_code == 200 and r.json()["amount"] == 500
    assert client.post(f"/charges/{c['id']}/refunds", headers=A, json={}).json()["amount"] == 1500
    assert client.get(f"/charges/{c['id']}", headers=A).json()["refunded"] is True
    assert len(client.get("/charges", headers=A).json()["data"]) == 2


def test_B1_cannot_read_another_accounts_charge(client):
    theirs = charge(client, B, 4200).json()
    assert client.get(f"/charges/{theirs['id']}", headers=A).status_code == 404
    assert client.post(f"/charges/{theirs['id']}/refunds", headers=A, json={}).status_code == 404


def test_B2_partial_refunds_cannot_exceed_the_charge(client):
    c = charge(client, A, 1000).json()
    assert client.post(f"/charges/{c['id']}/refunds", headers=A, json={"amount": 700}).status_code == 200
    second = client.post(f"/charges/{c['id']}/refunds", headers=A, json={"amount": 700})
    assert second.status_code == 400
    assert client.get(f"/charges/{c['id']}", headers=A).json()["amount_refunded"] == 700


def test_B3_idempotency_keys_are_per_account(client):
    theirs = charge(client, B, 1000, key="order-1").json()
    mine = charge(client, A, 1000, key="order-1")
    assert mine.status_code == 200
    assert mine.json()["id"] != theirs["id"]
    assert client.get(f"/charges/{mine.json()['id']}", headers=A).status_code == 200


def test_B4_pages_do_not_repeat_or_skip(client):
    created = [charge(client, A, 100 + i).json()["id"] for i in range(5)]
    seen, after = [], None
    while True:
        params = {"limit": 2, **({"starting_after": after} if after else {})}
        page = client.get("/charges", headers=A, params=params).json()
        seen += [c["id"] for c in page["data"]]
        if not page["has_more"]:
            break
        after = page["data"][-1]["id"]
        assert len(seen) <= 10, "pagination never ends"
    assert seen == list(reversed(created))
