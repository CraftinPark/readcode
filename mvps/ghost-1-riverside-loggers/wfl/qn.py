import struct

J = 65280


def _u(h):
    return struct.unpack(">HIHB", bytes.fromhex(h)[:9])


def receive(conn, p):
    h = p.get("hex")
    if not h or len(h) < 18:
        raise ValueError("pkt")
    k, t, c, flag = _u(h)
    if (flag >> 6) & 1:
        return
    r = conn.execute("select m from mt where k=?", ("%04x" % k,)).fetchone()
    if r is None:
        raise ValueError("hw %04x" % k)
    m = r[0]
    x = conn.execute("select c from st where m=?", (m,)).fetchone()
    conn.execute("insert or replace into st values (?,?)", (m, c))
    if x is None:
        conn.commit()
        return
    x_old = x[0]
    tmp2 = c - x_old
    if tmp2 < 0:
        tmp2 = tmp2 + 65536 if x_old > J else c
    conn.execute("insert or ignore into rd values (?,?,?)", (m, t, tmp2))
    conn.commit()
