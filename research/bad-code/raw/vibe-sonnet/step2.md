Student: "ok it works!! now i want logged in users to be able to book a lecture room. a booking has a room, a date, start t..."

Nice, glad it works! Your schema is already close. What's missing:

1. A `date` column. Your table only has `start_time` and `end_time`, but you want a date too.
2. A way to stop double bookings. Two people shouldn't be able to book the same room at overlapping times.
3. The routes: list rooms, make a booking, see your bookings.

**Database change**

Add a `booking_date` column to the bookings table:

```python
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    booking_date TEXT NOT NULL,      -- 'YYYY-MM-DD'
    start_time TEXT NOT NULL,        -- 'HH:MM'
    end_time TEXT NOT NULL,          -- 'HH:MM'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Keep dates and times as zero-padded text like `2025-03-14` and `09:00`. That way they sort and compare correctly as strings.

Because you use `CREATE TABLE IF NOT EXISTS`, this won't change a table that already exists. While you're developing, the easiest fix is to delete your `.db` file and let `init_db()` recreate it.

You'll also want some rooms to exist. Add this inside `init_db()` after the script runs:

```python
db.execute("INSERT OR IGNORE INTO rooms (name, capacity) VALUES ('Room A', 30)")
db.execute("INSERT OR IGNORE INTO rooms (name, capacity) VALUES ('Room B', 60)")
```

**Booking route**

I'm assuming you're using Flask and store the logged-in user's id in `session["user_id"]`. Change that if yours is different.

```python
from flask import Flask, request, session, redirect, url_for, render_template, flash

@app.route("/book", methods=["GET", "POST"])
def book():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    if request.method == "POST":
        room_id = request.form["room_id"]
        booking_date = request.form["booking_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

        if start_time >= end_time:
            flash("End time must be after start time.")
        else:
            # overlap check: an existing booking overlaps if it starts before
            # the new one ends AND ends after the new one starts
            clash = db.execute(
                \"\"\"
                SELECT 1 FROM bookings
                WHERE room_id = ? AND booking_date = ?
                  AND start_time < ? AND end_time > ?
                \"\"\",
                (room_id, booking_date, end_time, start_time),
            ).fetchone()

            if clash:
                flash("That room is already booked at that time.")
            else:
                db.execute(
                    "INSERT INTO bookings (user_id, room_id, booking_date, start_time, end_time) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (session["user_id"], room_id, booking_date, start_time, end_time),
                )
                db.commit()
                flash("Room booked!")
                db.close()
                return redirect(url_for("my_bookings"))

    rooms = db.execute("SELECT id, name, capacity FROM rooms").fetchall()
    db.close()
    return render_template("book.html", rooms=rooms)


@app.route("/my-bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    bookings = db.execute(
        \"\"\"
        SELECT bookings.*, rooms.name AS room_name
        FROM bookings JOIN rooms ON rooms.id = bookings.room_id
        WHERE bookings.user_id = ?
        ORDER BY booking_date, start_time
        \"\"\",
        (session["user_id"],),
    ).fetchall()
    db.close()
    return render_template("my_bookings.html", bookings=bookings)
```

**Template (`templates/book.html`)**

```python
<form method="post">
  <select name="room_id" required>
    {% for room in rooms %}
      <option value="{{ room.id }}">{{ room.name }} (seats {{ room.capacity }})</option>
    {% endfor %}
  </select>
  <input type="date" name="booking_date" required>
  <input type="time" name="start_time" required>
  <input type="time" name="end_time" required>
  <button type="submit">Book</button>
</form>
```

(That block is HTML, not Python. Save it as `templates/book.html`.)

**Notes**

- The overlap check is the important part. Two bookings overlap when `existing.start < new.end` and `existing.end > new.start`. That also means back-to-back bookings (10:00 to 11:00, then 11:00 to 12:00) are allowed.
- Always use `?` placeholders as above, never f-strings in SQL.
- Try it: book Room A on one date from 09:00 to 10:00, then try 09:30 to 10:30 in the same room. The second should be rejected.

Next steps could be cancelling your own bookings, or checking the date isn't in the past. Tell me which you want.
