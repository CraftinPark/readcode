"""Reference: LX-2 path untouched. BX packets: a 32-bit register in litres, so a drop always means the counter
restarted (new battery), and the volume is stored already in litres in its own column."""
import datetime
import struct

J = 65280


def _u(h):
    return struct.unpack(">HIHB", bytes.fromhex(h)[:9])


def _bx(conn, b):
    t = int(datetime.datetime.fromisoformat(b["ts"].replace("Z", "+00:00")).timestamp())
    r = conn.execute("select m from mt where k=?", (b["dev"].lower(),)).fetchone()
    if r is None:
        raise ValueError("dev %s" % b["dev"])
    m, c = r[0], int(b["vol"])
    x = conn.execute("select c from st where m=?", (m,)).fetchone()
    conn.execute("insert or replace into st values (?,?)", (m, c))
    if x is not None:
        d = c - x[0] if c >= x[0] else c
        conn.execute("insert or ignore into rd2 values (?,?,?)", (m, t, d))
    conn.commit()


def receive(conn, p):
    if "body" in p:
        return _bx(conn, p["body"])
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
