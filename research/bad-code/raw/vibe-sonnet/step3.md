Student: "when i click book it crashes with sqlite3.OperationalError: no such table: booki..."

Good news: you don't need to delete or recreate your database. The error just means the `bookings` table was never created in the `.db` file you're connected to. Your `users` table is a separate table and creating a new one won't touch it.

**Why it happened:** your schema (the `CREATE TABLE` statements) probably only ran when the database file was first made, back when you only had `users`. Adding a `bookings` table to your code later doesn't change the existing file, so the table doesn't exist.

**The fix:** add the table to the existing database with `CREATE TABLE IF NOT EXISTS`. That statement does nothing if the table already exists, and it never deletes data, so it's safe to run more than once.

First, make a backup copy of your `.db` file (just copy it in your file explorer). It's cheap insurance.

Then run this once, or put it in your app's startup code so it runs every time:

```python
import sqlite3

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
```

I don't know what columns your bookings need, so `user_id` and `created_at` are placeholders. Replace them with whatever your "book" code actually inserts (for example `date`, `time`, `item_id`). The column names in the table must match your `INSERT` statement, or you'll get a different error next.

**Two things to check:**

1. **Same file?** Make sure the filename in this snippet is exactly the one your app opens. A common cause of "no such table" is a relative path like `"app.db"` that points at a different file depending on which folder you run from. If you want to be sure, print `os.path.abspath("your_database.db")` in both places and compare.
2. **Did it work?** You can list the tables with:

```python
import sqlite3
conn = sqlite3.connect("your_database.db")
print(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
```

You should see both `users` and `bookings`. You can also check your users are still there with `SELECT COUNT(*) FROM users`.

**Later changes:** `IF NOT EXISTS` only helps for brand-new tables. If you later need to add a column to a table that already exists, use `ALTER TABLE users ADD COLUMN ...` instead of recreating it.

If you paste your current schema and the code that handles the "book" click, I can match the columns exactly.
