Student: "when i click book it crashes with sqlite3.OperationalError: no such table: booki..."

The error means the `bookings` table does not exist in the database file your app is using. Your `users` table is fine. Creating a missing table does not change or delete rows in existing tables, so your users are safe. Do not delete the .db file, because that is what would lose them.

Step 1: Make a backup copy of the database file before you change anything.

Step 2: Create the missing table once at startup. `IF NOT EXISTS` makes it safe to run every time the app starts.

```python
import sqlite3

def init_db(db_path="app.db"):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()

init_db()
```

Adjust the columns so they match what your booking code inserts. If the insert uses a column like `room` or `status`, add it to the CREATE TABLE statement.

Call `init_db()` once when the app starts, before the "book" handler runs.

Things to check if it still fails:

- The app may be using a different database file than the one you are looking at. A relative path like `app.db` depends on the folder you run the program from. Print the path with `print(os.path.abspath("app.db"))` to see which file is used.
- You can check the tables in a file with the `sqlite3` shell: run `sqlite3 app.db`, then `.tables`. You can also create the table there by pasting the CREATE TABLE statement.
- If you later need to change an existing table, use `ALTER TABLE` or a migration tool such as Alembic. Do not delete the file to start over.

If it still crashes, paste your booking handler and the code that creates your tables, and I can point to the exact line.
