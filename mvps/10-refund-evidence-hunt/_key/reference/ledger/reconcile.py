"""Builds the refund ledger the merchant dashboard and month-end close read: total refunded per charge, in
minor units (cents)."""


def refund_totals(store):
    seen = set()
    totals = {}
    for record in store.records():
        event = record["event"]
        if event["id"] in seen:  # Paylane redelivers on timeouts; same event id
            continue
        seen.add(event["id"])
        if event["type"] == "charge.refunded":
            data = event["data"]
            if record.get("api_version", "2024-06") >= "2025-09":  # cumulative refunded total for the charge
                totals[data["charge_id"]] = max(totals.get(data["charge_id"], 0), data["amount_refunded"])
            else:  # 2024-06: the amount of this refund
                totals[data["charge_id"]] = totals.get(data["charge_id"], 0) + data["amount_refunded"]
    return totals


def charge_totals(store):
    totals = {}
    for record in store.records():
        event = record["event"]
        if event["type"] == "charge.succeeded":
            totals[event["data"]["charge_id"]] = event["data"]["amount"]
    return totals
