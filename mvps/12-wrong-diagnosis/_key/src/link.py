import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
_K = 0x5EED12C0FFEE
BUDGET = 5
MAX_ROWS = 40


def _stream(n):
    x = _K
    out = bytearray()
    while len(out) < n:
        x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        out += (x >> 24).to_bytes(5, "little")
    return bytes(out[:n])


def _open():
    raw = open(os.path.join(HERE, "snapshot.bin"), "rb").read()
    data = bytes(a ^ b for a, b in zip(raw, _stream(len(raw))))
    conn = sqlite3.connect(":memory:")
    conn.deserialize(data)
    conn.execute("pragma query_only = on")
    return conn


def query(sql):
    used_path = os.path.join(HERE, ".queries_used")
    used = int(open(used_path).read()) if os.path.exists(used_path) else 0
    if used >= BUDGET:
        return f"production query budget used up ({BUDGET}/{BUDGET})."
    open(used_path, "w").write(str(used + 1))
    try:
        cur = _open().execute(sql)
    except sqlite3.Error as e:
        return f"error: {e}  (query {used + 1}/{BUDGET} used)"
    cols = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(MAX_ROWS + 1)
    lines = ["\t".join(cols)] + ["\t".join("" if v is None else str(v) for v in row) for row in rows[:MAX_ROWS]]
    if len(rows) > MAX_ROWS:
        lines.append(f"... (truncated at {MAX_ROWS} rows)")
    lines.append(f"(query {used + 1}/{BUDGET} used)")
    return "\n".join(lines)
