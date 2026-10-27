"""Write your tests here. Plain asserts in test_* functions (pytest-style). Run: python grade.py"""
from datetime import date

from promo import discount


def test_welcome_code_on_a_first_order():
    assert discount(3000, "WELCOME10", date(2026, 11, 1), 0, 0) == 300
