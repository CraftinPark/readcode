"""POST /webhooks/paylane. Paylane retries any delivery that doesn't get a 2xx, so we store first and
reconcile later (see reconcile.py)."""
import datetime
import json
import uuid


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def handle(headers, body, store, now=None):
    """headers: dict of the HTTP request headers. body: the raw request body (bytes). Returns the HTTP status."""
    ts = now or _now()
    request_id = headers.get("X-Request-Id") or "r_" + uuid.uuid4().hex[:12]
    try:
        event = json.loads(body)
    except ValueError:
        status = 400
    else:
        store.append({"request_id": request_id, "received_at": ts, "event": event})
        status = 200
    store.log_gateway(f"{ts} INFO gw req={request_id} POST /webhooks/paylane {status} headers={json.dumps(headers)}")
    return status
