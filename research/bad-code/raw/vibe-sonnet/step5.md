Student: "last thing for my project: i need a page where you pick a date and it shows a table of which ro..."

Here's a full version. I don't know your exact column names, so I assumed this schema. Change the names in the query if yours differ:

- `rooms(id, name)`
- `bookings(id, room_id, start_time, end_time)`, where times are text like `2025-03-14 10:00` (ISO format)

**Route (app.py)**

```python
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request

app = Flask(__name__)

HOURS = list(range(9, 18))  # 9..17 = the nine slots 9:00-18:00


@app.route("/availability")
def availability():
    # Date from the date picker; default to today. Bad input falls back to today.
    day_str = request.args.get("date", date.today().isoformat())
    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        day = date.today()

    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    db = get_db()
    rooms = db.execute("SELECT id, name FROM rooms ORDER BY name").fetchall()

    # Any booking that overlaps this day (parameterised query, no string formatting)
    bookings = db.execute(
        """
        SELECT room_id, start_time, end_time
        FROM bookings
        WHERE start_time < ? AND end_time > ?
        """,
        (day_end.strftime("%Y-%m-%d %H:%M"), day_start.strftime("%Y-%m-%d %H:%M")),
    ).fetchall()

    # busy[room_id] = set of hours that are taken
    busy = {room["id"]: set() for room in rooms}
    for b in bookings:
        start = datetime.strptime(b["start_time"], "%Y-%m-%d %H:%M")
        end = datetime.strptime(b["end_time"], "%Y-%m-%d %H:%M")
        for h in HOURS:
            slot_start = day_start + timedelta(hours=h)
            slot_end = slot_start + timedelta(hours=1)
            # overlap test: booking starts before the slot ends AND ends after it starts
            if start < slot_end and end > slot_start and b["room_id"] in busy:
                busy[b["room_id"]].add(h)

    return render_template(
        "availability.html", day=day.isoformat(), rooms=rooms, hours=HOURS, busy=busy
    )
```

(This assumes `row["col"]` access works, i.e. your `get_db()` sets `db.row_factory = sqlite3.Row`. If it doesn't, add that line.)

**Template (templates/availability.html)**

```html
<!doctype html>
<title>Room availability</title>
<style>
  table { border-collapse: collapse; }
  th, td { border: 1px solid #999; padding: 6px 10px; text-align: center; }
  td.busy { background: #e57373; }
  td.free { background: #a5d6a7; }
</style>

<h1>Room availability</h1>

<form method="get">
  <input type="date" name="date" value="{{ day }}">
  <button type="submit">Show</button>
</form>

<table>
  <tr>
    <th>Room</th>
    {% for h in hours %}
      <th>{{ h }}:00</th>
    {% endfor %}
  </tr>
  {% for room in rooms %}
  <tr>
    <th>{{ room["name"] }}</th>
    {% for h in hours %}
      {% if h in busy[room["id"]] %}
        <td class="busy">Busy</td>
      {% else %}
        <td class="free">Free</td>
      {% endif %}
    {% endfor %}
  </tr>
  {% endfor %}
</table>
```

**How it works**

1. The date picker is a plain GET form, so the chosen date goes in the URL (`/availability?date=2025-03-14`). You can bookmark or share it.
2. One query fetches all bookings overlapping that day. I do the per-hour logic in Python rather than running rooms x hours queries, which would be slow and messy.
3. A booking blocks an hour if it starts before the hour ends and ends after the hour starts. So a 10:00-11:30 booking marks both the 10 and 11 columns, and a booking ending exactly at 11:00 does not block the 11 column.
4. Columns are 9 to 17, meaning the slots 9:00-10:00 up to 17:00-18:00. If you want an extra column starting at 18:00, change `range` to `list(range(9, 19))`.

**Things to check against your project**

- If your bookings store a separate date and hour (e.g. `date`, `start_hour`, `end_hour`), tell me and I'll adjust the query and overlap logic. It gets simpler.
- If your datetimes use a `T` (`2025-03-14T10:00`), change the format strings to match.
- Rooms with no bookings show all green, since each room starts with an empty set.

Nice work getting to the last piece. If something errors, paste the traceback and I'll help.
