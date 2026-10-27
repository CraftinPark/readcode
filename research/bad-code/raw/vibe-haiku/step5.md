Student: "last thing for my project: i need a page where you pick a date and it shows a ta..."

Here's a single-file Flask app. It uses `get_db()` with sqlite3, the `rooms` and `bookings` tables, and a date picker that shows a rooms-by-hours grid for 9:00 to 18:00.

I assumed this `bookings` layout: a room, a date, and a start and end hour (end is exclusive). If your table has different column names, change the SQL to match.

```python
import sqlite3
from datetime import date as Date

from flask import Flask, g, render_template_string, request

app = Flask(__name__)
DATABASE = "rooms.db"
HOURS = list(range(9, 19))  # 9, 10, ..., 18 (each column is the slot starting at that hour)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS rooms (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id         INTEGER PRIMARY KEY,
            room_id    INTEGER NOT NULL REFERENCES rooms(id),
            date       TEXT NOT NULL,      -- YYYY-MM-DD
            start_hour INTEGER NOT NULL,   -- e.g. 10
            end_hour   INTEGER NOT NULL    -- exclusive, e.g. 12 means busy 10:00-12:00
        );
    """)
    db.commit()


TEMPLATE = """
<!doctype html>
<title>Room availability</title>
<h1>Room availability</h1>
<form method="get">
  <input type="date" name="date" value="{{ day }}">
  <button type="submit">Show</button>
</form>
<table border="1" cellpadding="6">
  <tr>
    <th>Room</th>
    {% for h in hours %}<th>{{ "%02d:00" | format(h) }}</th>{% endfor %}
  </tr>
  {% for row in rows %}
  <tr>
    <th>{{ row.name }}</th>
    {% for busy in row.cells %}
      <td style="background: {{ '#f8b4b4' if busy else '#b4f8c8' }}">
        {{ 'busy' if busy else 'free' }}
      </td>
    {% endfor %}
  </tr>
  {% endfor %}
</table>
"""


@app.route("/")
def index():
    day = request.args.get("date") or Date.today().isoformat()
    try:
        Date.fromisoformat(day)
    except ValueError:
        day = Date.today().isoformat()

    db = get_db()
    rooms = db.execute("SELECT id, name FROM rooms ORDER BY name").fetchall()
    bookings = db.execute(
        "SELECT room_id, start_hour, end_hour FROM bookings WHERE date = ?",
        (day,),
    ).fetchall()

    # Set of (room_id, hour) pairs that are busy
    busy = set()
    for b in bookings:
        for h in range(b["start_hour"], b["end_hour"]):
            busy.add((b["room_id"], h))

    rows = [
        {"name": r["name"], "cells": [(r["id"], h) in busy for h in HOURS]}
        for r in rooms
    ]
    return render_template_string(TEMPLATE, day=day, hours=HOURS, rows=rows)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
```

How it works:
- `get_db()` opens one connection per request and stores it on `g`. `teardown_appcontext` closes it.
- The date comes from the query string (`?date=2026-10-27`). If it is missing or invalid, it defaults to today.
- A booking covers every hour `h` where `start_hour <= h < end_hour`. The set `busy` holds those `(room_id, hour)` pairs, so the table lookup is fast.
- Rows are rooms and columns are hours 9 to 18. Each cell is green when free and red when busy.

To test it, add a few rows by hand, for example:

```python
# run once in a python shell inside the project folder
import sqlite3
db = sqlite3.connect("rooms.db")
db.execute("INSERT INTO rooms (name) VALUES ('Room A'), ('Room B')")
db.execute("INSERT INTO bookings (room_id, date, start_hour, end_hour) VALUES (1, '2026-10-27', 10, 12)")
db.commit()
```

Then open http://127.0.0.1:5000/?date=2026-10-27 to see Room A busy at 10:00 and 11:00.
