import os
import sqlite3
from functools import wraps

from flask import (Flask, g, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, session, redirect, url_for, render_template, flash
from flask import render_template, request, session, redirect, url_for, flash
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request

app = Flask(__name__)
# In production, set SECRET_KEY as an environment variable instead.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
DATABASE = os.path.join(os.path.dirname(__file__), "app.db")


# ---------- Database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # access columns by name
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect("database.db")   # use whatever your file already uses
    cur = conn.cursor()

    # ... your existing CREATE TABLE statements stay here ...

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            room_id INTEGER NOT NULL REFERENCES rooms(id),
            booking_date TEXT NOT NULL      -- 'YYYY-MM-DD'
            -- put the rest of your columns here
        )
    """)

    conn.commit()
    conn.close()

# ---------- Auth helpers ----------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def load_current_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, username, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()


# ---------- Routes ----------
@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not username or not email or not password:
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                error = "That username or email is already registered."
            else:
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))

        flash(error, "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            next_url = request.args.get("next")
            # Only allow local redirects (prevents open-redirect attacks)
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


def dashboard():
    return render_template("dashboard.html")



db.execute("INSERT OR IGNORE INTO rooms (name, capacity) VALUES ('Room A', 30)")


db.execute("INSERT OR IGNORE INTO rooms (name, capacity) VALUES ('Room B', 60)")


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
                """
                SELECT 1 FROM bookings
                WHERE room_id = ? AND booking_date = ?
                  AND start_time < ? AND end_time > ?
                """,
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
        """
        SELECT bookings.*, rooms.name AS room_name
        FROM bookings JOIN rooms ON rooms.id = bookings.room_id
        WHERE bookings.user_id = ?
        ORDER BY booking_date, start_time
        """,
        (session["user_id"],),
    ).fetchall()
    db.close()
    return render_template("my_bookings.html", bookings=bookings)


conn = sqlite3.connect("your_database.db")  # use the SAME filename your app uses


conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )


""")


conn.commit()


conn.close()


conn = sqlite3.connect("your_database.db")


print(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())


@app.route('/cancel', methods=['GET', 'POST'])
def cancel_booking():
    # must be logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        booking_id = request.form.get('booking_id', '').strip()

        if not booking_id.isdigit():
            flash('Please enter a valid booking ID (numbers only).')
            return redirect(url_for('cancel_booking'))

        db = get_db()
        # only delete if the booking belongs to the logged-in user
        cur = db.execute(
            'DELETE FROM bookings WHERE id = ? AND user_id = ?',
            (int(booking_id), session['user_id'])
        )
        db.commit()

        if cur.rowcount == 0:
            flash('No booking with that ID was found on your account.')
        else:
            flash('Booking cancelled.')
        return redirect(url_for('cancel_booking'))

    return render_template('cancel.html')


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




if __name__ == "__main__":
    init_db()
    app.run(debug=True)  # turn debug off when deploying
