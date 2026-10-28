"""The on-call check for the ticket: five customers ask for a login code while Textly is slow (the message goes
out but the answer times out). Each must get exactly one SMS.

    python check.py
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from notify import db, otp  # noqa: E402
from tools.fake_textly import FakeTextly  # noqa: E402

phones = ["+44 7700 900101", "+44 7700 900102", "+44 7700 900103", "+44 7700 900104", "+44 7700 900105"]
client = FakeTextly(timeout_after_accept=phones[:3])
conn = sqlite3.connect(":memory:")
db.init(conn)
for i, p in enumerate(phones):
    otp.send_otp(client, conn, p, f"{481200 + i}", 1792500000 + i)
bad = 0
for p in phones:
    n = sum(1 for to, _ in client.sent if to == p)
    print(f"  {p}: {n} SMS")
    bad += n != 1
print("OK: one code each" if not bad else f"{bad} customers got the wrong number of SMS")
sys.exit(1 if bad else 0)
