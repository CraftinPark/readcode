Student: "hi, how do i make a flask app with register and login using sqlite? i want to make a website for booking lecture rooms at my uni later. pls give me the full app.py"

(Reply's app.py block, kept verbatim; prose omitted.)

```python
import sqlite3
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template_string,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-to-a-long-random-string"  # needed for sessions and flash messages
DATABASE = "users.db"


# ---------- database helpers ----------

def get_db():
    """Open one connection per request and reuse it during that request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # lets us access columns by name
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the users table if it does not exist yet."""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()


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
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
```
