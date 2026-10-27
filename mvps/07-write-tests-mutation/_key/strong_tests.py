"""Reference test file: catches all 8 mutants."""
from datetime import date

from promo import discount

D = date(2026, 11, 1)


def test_welcome_first_order():
    assert discount(3000, "WELCOME10", D, 0, 0) == 300


def test_min_subtotal_is_inclusive():
    assert discount(2000, "WELCOME10", D, 0, 0) == 200
    assert discount(1999, "WELCOME10", D, 0, 0) == 0


def test_last_valid_day_and_day_after():
    assert discount(3000, "WELCOME10", date(2026, 12, 31), 0, 0) == 300
    assert discount(3000, "WELCOME10", date(2027, 1, 1), 0, 0) == 0


def test_max_uses():
    assert discount(5000, "VIP25", D, 49, 3) == 1250
    assert discount(5000, "VIP25", D, 50, 3) == 0


def test_first_order_only():
    assert discount(3000, "WELCOME10", D, 0, 1) == 0


def test_rounds_half_up():
    assert discount(2005, "WELCOME10", D, 0, 0) == 201   # 200.5 -> 201


def test_flat_never_exceeds_subtotal():
    assert discount(300, "FLAT5", D, 0, 0) == 300


def test_code_is_case_and_space_insensitive():
    assert discount(3000, "welcome10", D, 0, 0) == 300
    assert discount(3000, " WELCOME10 ", D, 0, 0) == 300
