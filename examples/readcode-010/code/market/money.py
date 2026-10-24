"""Money helpers. All amounts are integers in cents."""


def percent(amount: int, pct: float) -> int:
    """pct percent of amount, rounded half up to the cent."""
    return int(amount * pct / 100 + 0.5)


def allocate(total: int, weights: list[int]) -> list[int]:
    """Split total across weights in proportion. The parts always add up to total:
    each part is rounded down, and the cents left over go to the parts that lost
    the most to rounding."""
    whole = sum(weights)
    if total == 0 or whole == 0:
        return [0] * len(weights)
    exact = [total * w / whole for w in weights]
    parts = [int(x) for x in exact]
    left = total - sum(parts)
    by_loss = sorted(range(len(weights)), key=lambda i: exact[i] - parts[i], reverse=True)
    for i in by_loss[:left]:
        parts[i] += 1
    return parts


def fmt(cents: int) -> str:
    return f"${cents / 100:,.2f}"
