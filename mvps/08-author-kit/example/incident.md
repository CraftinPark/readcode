# INC-2291: Duplicate payouts to couriers (FleetRunner)

Reported by priya.n@acmedelivery.com in #payouts-oncall. Courier payouts ran twice for the week of
2026-03-02 on payout-worker-3.acme.corp (10.42.7.19). See https://grafana.internal.acmedelivery.com/d/payouts.
AcmePay's ledger shows two batches with different batch ids. The PayoutBatcher retries the whole batch when
the AcmePay API returns 502, without checking whether the first batch landed.
