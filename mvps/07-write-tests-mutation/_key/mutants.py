"""Each mutant is one realistic slip in promo.py: (id, what changed, old text, new text). Never shown to the player."""
MUTANTS = [
    ("M1", "minimum subtotal boundary: < becomes <=", "if subtotal_cents < min_subtotal:", "if subtotal_cents <= min_subtotal:"),
    ("M2", "expiry day itself rejected", "if today > expires_on:", "if today >= expires_on:"),
    ("M3", "one extra use allowed", "if times_used >= max_uses:", "if times_used > max_uses:"),
    ("M4", "first-order rule dropped", "if first_order_only and customer_order_count > 0:", "if first_order_only and customer_order_count > 1:"),
    ("M5", "rounding truncates instead of half up", "amount = (subtotal_cents * value + 50) // 100", "amount = subtotal_cents * value // 100"),
    ("M6", "no cap at the subtotal", "return min(amount, subtotal_cents)", "return amount"),
    ("M7", "codes become case-sensitive", "rule = CODES.get(code.strip().upper())", "rule = CODES.get(code.strip())"),
    ("M8", "surrounding spaces not trimmed", "rule = CODES.get(code.strip().upper())", "rule = CODES.get(code.upper())"),
]
