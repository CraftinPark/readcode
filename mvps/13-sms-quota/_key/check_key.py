"""Shipped code and the ticket's fix (client_ref on retries) fail the hidden replay; the reference passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

bad = 0
for name, code, should_pass in [("shipped", os.path.dirname(HERE), False),
                                ("dedupe", os.path.join(HERE, "dedupe"), False),
                                ("reference", os.path.join(HERE, "reference"), True)]:
    ok, stats = replay.run(code, verbose=False)
    stats = __import__('collections').Counter(stats)
    print(f"{name}: replay {'passes' if ok else 'fails'} (lost/late codes {stats['otp lost or late']}, "
          f"duplicated {stats['otp duplicated']}) expected {'pass' if should_pass else 'fail'}")
    bad += ok != should_pass
sys.exit(1 if bad else 0)
