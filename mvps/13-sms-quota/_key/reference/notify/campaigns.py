"""Marketing campaigns. The campaign tool calls enqueue() at the scheduled time; scheduler.tick sends them."""


def enqueue(conn, name, phones, body, now):
    conn.executemany("insert into outbox (campaign, to_number, body, created_at) values (?, ?, ?, ?)",
                     [(name, p, body, now) for p in phones])
    conn.commit()
