import sqlite3
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template_string,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template_string, request, session, redirect, url_for
from datetime import date as Date
from flask import Flask, g, render_template_string, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-to-a-long-random-string"  # needed for sessions and flash messages
DATABASE = "users.db"


# ---------- database helpers ----------

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

# ---------- auth helpers ----------

def login_required(view):
    """Redirect to the login page if nobody is logged in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- HTML templates (kept inside the file for simplicity) ----------

PAGE_STYLE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 400px; margin: 40px auto; padding: 0 16px; }
  input { display: block; width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }
  button { padding: 8px 16px; cursor: pointer; }
  .msg { color: #b00020; }
</style>
"""

REGISTER_HTML = PAGE_STYLE + """
<h2>Register</h2>
{% for m in get_flashed_messages() %}<p class="msg">{{ m }}</p>{% endfor %}
<form method="post">
  <input name="username" placeholder="Username" required>
  <input name="password" type="password" placeholder="Password" required>
  <button type="submit">Register</button>
</form>
<p><a href="{{ url_for('login') }}">Already have an account? Log in</a></p>
"""

LOGIN_HTML = PAGE_STYLE + """
<h2>Log in</h2>
{% for m in get_flashed_messages() %}<p class="msg">{{ m }}</p>{% endfor %}
<form method="post">
  <input name="username" placeholder="Username" required>
  <input name="password" type="password" placeholder="Password" required>
  <button type="submit">Log in</button>
</form>
<p><a href="{{ url_for('register') }}">No account yet? Register</a></p>
"""

DASHBOARD_HTML = PAGE_STYLE + """
<h2>Welcome, {{ username }}!</h2>
{% for m in get_flashed_messages() %}<p class="msg">{{ m }}</p>{% endfor %}
<p>This page is only visible when logged in.</p>
<a href="{{ url_for('logout') }}">Log out</a>
"""


# ---------- routes ----------

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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            flash("That username is already taken.")
            return redirect(url_for("register"))

        # Never store the raw password, only a salted hash.
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
        flash("Account created! You can log in now.")
        return redirect(url_for("login"))

    return render_template_string(REGISTER_HTML)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template_string(LOGIN_HTML)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML, username=session["username"])


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


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


init_db()


CANCEL_PAGE = """


<h1>Cancel a booking</h1>


{% if message %}<p>{{ message }}</p>{% endif %}


<form method="post">
  <label>Booking ID <input type="text" name="booking_id" required></label>
  <button type="submit">Cancel</button>


</form>


"""


@app.route("/bookings/cancel", methods=["GET", "POST"])
def cancel_booking():
    if "user_id" not in session:
        return redirect(url_for("login"))

    message = None
    if request.method == "POST":
        booking_id = request.form.get("booking_id", "").strip()

        if not booking_id.isdigit():
            message = "Please enter a valid booking ID (numbers only)."
        else:
            db = get_db()
            cur = db.execute(
                "UPDATE bookings SET status = 'cancelled' "
                "WHERE id = ? AND user_id = ? AND status != 'cancelled'",
                (int(booking_id), session["user_id"]),
            )
            db.commit()

            if cur.rowcount == 1:
                message = f"Booking {booking_id} has been cancelled."
            else:
                message = "No active booking with that ID was found on your account."

    return render_template_string(CANCEL_PAGE, message=message)


app = Flask(__name__)


DATABASE = "rooms.db"


HOURS = list(range(9, 19))  # 9, 10, ..., 18 (each column is the slot starting at that hour)


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


# run once in a python shell inside the project folder


db = sqlite3.connect("rooms.db")


db.execute("INSERT INTO rooms (name) VALUES ('Room A'), ('Room B')")


db.execute("INSERT INTO bookings (room_id, date, start_hour, end_hour) VALUES (1, '2026-10-27', 10, 12)")


db.commit()


db = sqlite3.connect("your_database_file.db")  # use your app's real file name


print(db.execute("PRAGMA table_info(bookings)").fetchall())


db = sqlite3.connect("your_database_file.db")


db.execute("ALTER TABLE bookings ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")


db.commit()


db.close()


SCHEMA = """


CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    -- your other columns here
    status TEXT NOT NULL DEFAULT 'active'
);


"""


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
