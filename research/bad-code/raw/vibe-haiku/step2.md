Student: "ok it works!! now i want logged in users to be able to book a lecture room. a bo..."

Nice, that's a good next step. Add a second table for bookings in `init_db()`, below the users table. Each booking stores which user made it, so it needs a `user_id` that points at `users.id`.

```python
def init_db():
    """Create the users and bookings tables if they do not exist yet."""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room TEXT NOT NULL,
            booking_date TEXT NOT NULL,   -- 'YYYY-MM-DD'
            start_time TEXT NOT NULL,     -- 'HH:MM'
            end_time TEXT NOT NULL,       -- 'HH:MM'
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    db.commit()
    db.close()
```

A few notes on this:

- **Dates and times:** SQLite has no real date or time column type, so store them as text. Use zero-padded formats like `'2026-10-27'` and `'09:30'`. Those sort correctly as text, which the overlap check below relies on.
- **`booking_date` instead of `date`:** `date` is not reserved in SQLite, but a more specific name avoids confusion with the SQL function of the same name.
- **Foreign keys:** SQLite does not enforce `FOREIGN KEY` unless you turn it on for each connection with `db.execute("PRAGMA foreign_keys = ON")`.

Before inserting a booking, you need to check that the room is free. Two bookings clash when they are in the same room on the same day and one starts before the other ends:

```python
def has_conflict(db, room, booking_date, start_time, end_time):
    row = db.execute("""
        SELECT 1 FROM bookings
        WHERE room = ?
          AND booking_date = ?
          AND start_time < ?
          AND end_time > ?
        LIMIT 1
    """, (room, booking_date, end_time, start_time)).fetchone()
    return row is not None
```

Also check that `start_time < end_time` in your route before you save anything.

The booking route then uses the id of the logged-in user, which is whatever you store in the session when they log in (for example `session["user_id"]`). Never take the user id from the form, because then anyone could book as someone else.

```python
def create_booking(user_id, room, booking_date, start_time, end_time):
    db = sqlite3.connect(DATABASE)
    if start_time >= end_time:
        db.close()
        return False, "End time must be after start time."
    if has_conflict(db, room, booking_date, start_time, end_time):
        db.close()
        return False, "That room is already booked for that time."
    db.execute("""
        INSERT INTO bookings (user_id, room, booking_date, start_time, end_time)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, room, booking_date, start_time, end_time))
    db.commit()
    db.close()
    return True, "Booking saved."
```

Use `?` placeholders for every value, as shown above, and never build the SQL with f-strings. That keeps the code safe from SQL injection.
