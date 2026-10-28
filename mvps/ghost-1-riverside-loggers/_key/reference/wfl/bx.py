lf = 1.062  # LX-2 litres per pulse
pr = 0.00285


def round_up(v):
    return int(v)


def bill(conn, m, a, b):
    q = "select coalesce(sum(l), 0) from %s where m=? and t>=? and t<?"
    pulses = conn.execute(q % "rd", (m, a, b)).fetchone()[0]
    litres = conn.execute(q % "rd2", (m, a, b)).fetchone()[0]
    l = round_up(pulses * lf) + litres
    return {"meter": m, "litres": l, "eur": round(l * pr, 2)}
