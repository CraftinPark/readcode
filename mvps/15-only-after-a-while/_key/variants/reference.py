"""Talks to the pricing service. Prices are integer pence everywhere in the shop."""
import json
import os
import urllib.parse
import urllib.request


def base_url():
    return os.environ.get("PRICING_URL", "http://127.0.0.1:8765")


def _fetch(sku):
    url = f"{base_url()}/price?sku={urllib.parse.quote(sku)}"
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.load(r)


from decimal import Decimal


def unit_price_pence(sku):
    """catalogue-v2 sends pounds; the warm-start snapshot sends pence."""
    body = _fetch(sku)
    if body.get("source") == "catalogue-v2":
        return int(Decimal(str(body["price"])) * 100)
    return int(body["price"])
