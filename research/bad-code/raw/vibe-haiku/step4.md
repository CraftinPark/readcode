Student: "thanks that worked. can u add a page to cancel a booking? the user types the boo..."

Sure. Add this route next to your other routes. It checks that the user is logged in, and it only cancels a booking if that booking belongs to the logged-in user.

```python
from flask import Flask, render_template_string, request, session, redirect, url_for

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
```

Notes:

- The `WHERE ... AND user_id = ?` part is important. Without it, any logged-in user could cancel someone else's booking by typing its ID.
- The query uses `?` placeholders, so the typed text can't inject SQL.
- I assumed your `bookings` table has `id`, `user_id`, and `status` columns. If you don't have a `status` column, delete the row instead: `DELETE FROM bookings WHERE id = ? AND user_id = ?`, and check `cur.rowcount` the same way.
- If you already use Flask templates, move `CANCEL_PAGE` into `templates/cancel_booking.html` and return `render_template("cancel_booking.html", message=message)`.
- Add a link to `/bookings/cancel` somewhere in your navigation so users can find the page.
