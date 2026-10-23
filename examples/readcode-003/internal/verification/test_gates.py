"""Gate tests for readcode-003. $READCODE_ROOT is the folder holding the payments
package under test (the baseline or the shipped code).

t0 must pass on both. Each B# test must pass on the baseline and fail on the
shipped code. B1 and B3 inject faults (a network timeout after the card was
charged, a server dying mid-request, a 4xx from the merchant's endpoint).
"""
import os
import sys

sys.path.insert(0, os.environ["READCODE_ROOT"])

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from payments import db, webhooks  # noqa: E402
from payments.app import create_app  # noqa: E402
from payments.card_network import CardNetworkTimeout, FakeCardNetwork  # noqa: E402

ACME = {"Authorization": "Bearer sk_test_acme"}
GLOBEX = {"Authorization": "Bearer sk_test_globex"}
VISA = {"amount": 2500, "currency": "usd", "payment_method": "pm_card_visa"}


class Clock:
    def __init__(self):
        self.t = 1_760_000_000.0

    def __call__(self):
        return self.t


class FlakyNetwork(FakeCardNetwork):
    """Charges the card, then fails before the answer reaches us."""

    def __init__(self, fail_with):
        super().__init__()
        self.fail_with = fail_with

    def authorize(self, *args):
        auth = super().authorize(*args)
        if self.fail_with is not None:
            err, self.fail_with = self.fail_with, None
            raise err
        return auth


def make(tmp_path, network=None):
    path = str(tmp_path / "payments.db")
    db.init(path,
            accounts=[{"id": "acct_acme", "name": "Acme", "secret_key": "sk_test_acme"},
                      {"id": "acct_globex", "name": "Globex", "secret_key": "sk_test_globex"}],
            endpoints=[{"id": "we_a", "account_id": "acct_acme", "url": "https://acme.example/hooks", "secret": "a"},
                       {"id": "we_g", "account_id": "acct_globex", "url": "https://globex.example/hooks", "secret": "g"}])
    network = network or FakeCardNetwork()
    clock = Clock()
    client = TestClient(create_app(path, network, clock), raise_server_exceptions=False)
    return client, network, clock, db.connect(path)


def charges_in_db(conn):
    return conn.execute("SELECT COUNT(*) FROM charges").fetchone()[0]


def test_t0_ordinary_flow(tmp_path):
    client, network, clock, conn = make(tmp_path)
    assert client.get("/charges").status_code == 401
    first = client.post("/charges", headers={**ACME, "Idempotency-Key": "k1"}, json=VISA)
    assert first.status_code == 200
    assert client.post("/charges", headers={**ACME, "Idempotency-Key": "k1"}, json=VISA).json()["id"] == first.json()["id"]
    assert client.post("/charges", headers={**ACME, "Idempotency-Key": "k1"}, json={**VISA, "amount": 1}).status_code == 409
    assert client.post("/charges", headers=ACME, json={**VISA, "payment_method": "pm_card_declined"}).status_code == 402
    cid = first.json()["id"]
    assert client.post(f"/charges/{cid}/refunds", headers=ACME, json={"amount": 1000}).status_code == 200
    assert client.post(f"/charges/{cid}/refunds", headers=ACME, json={"amount": 2000}).status_code == 400
    assert client.get(f"/charges/{cid}", headers=GLOBEX).status_code == 404
    assert len(client.get("/charges", headers=ACME).json()["data"]) == 2
    sent = []
    assert webhooks.deliver_due(conn, lambda u, b, h: sent.append(u) or 200, db.now_ms(clock)) == 3
    assert set(sent) == {"https://acme.example/hooks"}


def test_B1_retry_after_a_failure_does_not_charge_the_card_twice(tmp_path):
    # The network charges the card but times out before answering; the client retries.
    client, network, clock, conn = make(tmp_path, FlakyNetwork(CardNetworkTimeout()))
    h = {**ACME, "Idempotency-Key": "order-7"}
    assert client.post("/charges", headers=h, json=VISA).status_code == 503
    assert client.post("/charges", headers=h, json=VISA).status_code == 200
    assert network.total_authorized() == VISA["amount"]

    # The server dies after the card was charged; a retry a minute later takes the key over.
    (tmp_path / "crash").mkdir()
    client, network, clock, conn = make(tmp_path / "crash", FlakyNetwork(RuntimeError("server killed")))
    h = {**ACME, "Idempotency-Key": "order-8"}
    assert client.post("/charges", headers=h, json=VISA).status_code == 500
    clock.t += 61
    assert client.post("/charges", headers=h, json=VISA).status_code == 200
    assert network.total_authorized() == VISA["amount"]


def test_B2_a_key_is_kept_for_24_hours(tmp_path):
    client, network, clock, conn = make(tmp_path)
    h = {**ACME, "Idempotency-Key": "nightly-42"}
    first = client.post("/charges", headers=h, json=VISA).json()
    clock.t += 10 * 60                                   # a retry job runs ten minutes later
    assert client.post("/charges", headers=h, json=VISA).json()["id"] == first["id"]
    assert charges_in_db(conn) == 1


def test_B3_a_4xx_from_the_endpoint_is_retried(tmp_path):
    client, network, clock, conn = make(tmp_path)
    client.post("/charges", headers=ACME, json=VISA)
    replies = iter([400, 200])
    sent = []
    post = lambda u, b, h: sent.append(u) or next(replies)  # noqa: E731
    assert webhooks.deliver_due(conn, post, db.now_ms(clock)) == 0
    clock.t += 3600
    assert webhooks.deliver_due(conn, post, db.now_ms(clock)) == 1
    assert len(sent) == 2


def test_B4_events_go_to_their_own_accounts_endpoint(tmp_path):
    client, network, clock, conn = make(tmp_path)
    client.post("/charges", headers=ACME, json=VISA)
    clock.t += 1
    client.post("/charges", headers=GLOBEX, json=VISA)
    sent = []
    webhooks.deliver_due(conn, lambda u, b, h: sent.append(u) or 200, db.now_ms(clock))
    assert sent == ["https://acme.example/hooks", "https://globex.example/hooks"]
