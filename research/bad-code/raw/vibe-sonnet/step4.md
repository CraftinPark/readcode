Student: "thanks that worked. can u add a page to cancel a booking? the user types the boo..."

Glad it worked! Here's a cancel page. I had to guess your table and column names, so check these against your schema: I assumed a `bookings` table with columns `id` and `user_id`. If yours are different, change them in the SQL.

```python
from flask import render_template, request, session, redirect, url_for, flash

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
```

And the template, `templates/cancel.html`:

```python
{% with messages = get_flashed_messages() %}
  {% for m in messages %}<p>{{ m }}</p>{% endfor %}
{% endwith %}

<form method="post">
  <label>Booking ID:
    <input type="text" name="booking_id" required>
  </label>
  <button type="submit">Cancel</button>
</form>
```

(That template is HTML, not Python. I just put it in a code block so it's easy to copy.)

A few things worth knowing about why I wrote it this way:

- **It checks `user_id` in the DELETE.** The `AND user_id = ?` part matters. Without it, any logged-in user could type someone else's booking ID and cancel it. With it, you can only cancel your own bookings.
- **It uses `?` placeholders** instead of putting the ID into the SQL string, so nobody can inject SQL through the box.
- **It's a POST, not a link.** Cancelling changes data, so it shouldn't be something a GET request (like a link or a browser prefetch) can trigger.
- **`rowcount` tells you if anything happened.** If it's 0, the booking either doesn't exist or isn't theirs. I give the same message in both cases so people can't use it to probe which IDs exist.
- **`flash` needs `app.secret_key` to be set.** You almost certainly have it already since you use `session`.

If you'd rather keep a record of cancelled bookings instead of deleting them, change the query to `UPDATE bookings SET status = 'cancelled' WHERE id = ? AND user_id = ?` (you'd need a `status` column). Want me to do that version, or add a "my bookings" list so users don't have to remember their ID?
