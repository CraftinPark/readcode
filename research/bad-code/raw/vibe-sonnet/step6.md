Student: "now python app.py doesnt even start, it says  File "app.py", line 168     CREATE TABLE IF NOT EXI..."

This is a quick fix. The cause is that some SQL ended up pasted straight into your Python file. Python only understands Python, so when it reaches `CREATE TABLE ...` it stops with a SyntaxError.

Look at the code you pasted:

```python
def dashboard():
    return render_template("dashboard.html")


CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ...
```

`CREATE TABLE` is SQL. It belongs inside a Python string, or in a separate `.sql` file. It can't sit loose in `app.py`.

## Fix option 1 (fastest): put it inside a string

Find where the rest of your tables get created. That's probably a function like `init_db()`, or a `schema.sql` file. If it's a function, the bookings table should go in the same place as the others, like this:

```python
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
```

Three things to check:

1. The SQL has to be inside triple quotes `""" ... """`. The `--` comments are fine inside the string, because SQLite understands them. They would be a problem outside it, since Python comments use `#`.
2. Delete the loose `CREATE TABLE` block from where it is now, after `dashboard()`. If you leave it, you'll get the same error.
3. Paste the whole statement, up to and including the closing `);`. In your message the block cuts off after `booking_date`, so I can't see the rest. Don't leave out any columns your code uses. Also make sure the last column has no trailing comma before the closing `)`. SQL doesn't allow that.

## Fix option 2: if you already have a schema.sql

If your project loads its tables from a `schema.sql` file, move that bookings block into `schema.sql` and remove it from `app.py`. Then `app.py` doesn't need any change.

## After you fix it

1. Save the file and run `python app.py` again.
2. If your database file already exists, the new `bookings` table may not be there yet. Calling `init_db()` again will create it, because of `IF NOT EXISTS`. Or you can delete the `.db` file and let it rebuild, as long as you don't mind losing the test data.
3. If you get another error, paste the new message and the code around the line it names. Each error is usually a small fix like this one.

If you paste the part of `app.py` where your other tables are created (the `users` and `rooms` tables), I can show you exactly where the bookings table goes. You've got time to finish this.
