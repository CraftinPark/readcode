"""The starter tests catch none of the slips, and the reference tests catch all 8."""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import grade  # noqa: E402

bad = 0
for name, path, want in [("starter", os.path.join(HERE, "..", "test_promo.py"), 0), ("strong", os.path.join(HERE, "strong_tests.py"), 8)]:
    with contextlib.redirect_stdout(io.StringIO()):
        got = grade.grade(path)
    print(f"{name}: {got}/8 caught (expected {want})")
    bad += got != want
sys.exit(1 if bad else 0)
