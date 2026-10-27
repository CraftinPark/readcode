Student: "when i press cancel it crashes: sqlite3.OperationalError: no such column: status"...

Hi, good news: your cancel function is fine. The error means the `bookings` table in your database has no `status` column, and your UPDATE is trying to write to one. SQLite is telling you exactly that.

Why it happens: the table was created before `status` was part of your schema. `CREATE TABLE IF NOT EXISTS` does not change a table that already exists, so adding `status` to the CREATE statement later does nothing to a database file that is already on your machine.

Quick check. Open a Python shell and run this against the same database file your app uses:

```python
import sqlite3

db = sqlite3.connect("your_database_file.db")  # use your app's real file name
print(db.execute("PRAGMA table_info(bookings)").fetchall())
```

If no row in that output has `status` as its column name, that is the problem.

Fix option 1 (keeps your existing data). Add the column once:

```python
import sqlite3

db = sqlite3.connect("your_database_file.db")
db.execute("ALTER TABLE bookings ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
db.commit()
db.close()
```

The `DEFAULT 'active'` matters. Existing rows get `'active'`, so your `status != 'cancelled'` check works on them. Without a default, old rows would be NULL, and `NULL != 'cancelled'` evaluates to NULL, so those bookings would never match and could never be cancelled.

Fix option 2 (simplest, only if the data is throwaway test data). Delete the `.db` file and let the app recreate it on the next run. This wipes all existing bookings, so only do it if you don't care about them.

Either way, update the CREATE TABLE statement so brand-new databases get the column too:

```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    -- your other columns here
    status TEXT NOT NULL DEFAULT 'active'
);
"""
```

After the fix, your cancel function should work as written. Test it by cancelling a booking that belongs to the logged-in user. You should see "Booking <id> has been cancelled." If you try the same ID again, you should see "No active booking with that ID was found on your account."

When you hit a crash like this, the traceback shows the exact line that failed. Check which line of your code runs the SQL. That tells you which query is failing, and here it was the UPDATE.

You can do this. Good luck with the deadline tomorrow.
