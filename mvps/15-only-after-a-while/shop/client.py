"""Talks to the pricing service. Prices are integer pence everywhere in the shop."""
import json
import os
import urllib.parse
import urllib.request


def base_url():
    return os.environ.get("PRICING_URL", "http://127.0.0.1:8765")


def unit_price_pence(sku):
    url = f"{base_url()}/price?sku={urllib.parse.quote(sku)}"
    with urllib.request.urlopen(url, timeout=5) as r:
        body = json.load(r)
    return int(body["price"])
