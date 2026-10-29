"""Checkout totals. Everything is integer pence."""
from shop import client

FREE_DELIVERY_FROM = 5000
DELIVERY = 399


def quote(items):
    """items: [(sku, qty), ...] -> total to charge, in pence."""
    subtotal = sum(qty * client.unit_price_pence(sku) for sku, qty in items)
    delivery = 0 if subtotal >= FREE_DELIVERY_FROM else DELIVERY
    return subtotal + delivery
