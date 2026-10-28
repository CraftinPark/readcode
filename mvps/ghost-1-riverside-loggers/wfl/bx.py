lf = 1.062
pr = 0.00285


def round_up(v):
    return int(v)


def bill(conn, m, a, b):
    s = conn.execute("select coalesce(sum(l), 0) from rd where m=? and t>=? and t<?", (m, a, b)).fetchone()[0]
    l = round_up(s * lf)
    return {"meter": m, "litres": l, "eur": round(l * pr, 2)}
