import csv
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "meters.csv")


def init(conn):
    conn.execute("create table if not exists mt (k text primary key, m text, z text)")
    conn.execute("create table if not exists st (m text primary key, c integer)")
    conn.execute("create table if not exists rd (m text, t integer, l integer, primary key (m, t))")
    # rd holds LX-2 pulses (1 pulse = lf litres); rd2 holds BX litres.
    conn.execute("create table if not exists rd2 (m text, t integer, l integer, primary key (m, t))")
    with open(P, newline="") as f:
        for r in csv.DictReader(f):
            conn.execute("insert or replace into mt values (?,?,?)", (r["hw"].lower(), r["meter"], r["zone"]))
    conn.commit()
