from datetime import datetime, date, timedelta
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.models import User, Room, Booking
from app.email import send_password_reset_email
from app.forms import LoginForm, RegistrationForm

ROOM_OPEN_HOUR = 8
ROOM_CLOSE_HOUR = 20
DEFAULT_ROOM_ID = 3  # the big lecture room


@app.route('/')
@app.route('/index')
@login_required
def index():
    # shows the bookings for the logged in user, sorted by date
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', title='Home', bookings=bookings)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        print('new user', user.username)
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    rooms = Room.query.all()
    if request.method == 'POST':
        room_id = int(request.form.get('room_id', DEFAULT_ROOM_ID))
        date_str = request.form['date']
        start = int(request.form['start'])
        end = int(request.form['end'])
        try:
            day = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            flash('That date does not look right')
            return redirect(url_for('book'))
        if start >= end:
            flash('End time must be after start time')
            return redirect(url_for('book'))
        # TODO check the room is not already booked for that time
        b = Booking(user_id=current_user.id, room_id=room_id, date=day,
                    start_hour=start, end_hour=end)
        db.session.add(b)
        db.session.commit()
        print('booked', b.id)
        flash('Room booked')
        return redirect(url_for('index'))
    return render_template('book.html', title='Book a room', rooms=rooms)


@app.route('/cancel/<int:booking_id>')
@login_required
def cancel(booking_id):
    # if b.user_id != current_user.id: abort(403)
    try:
        b = Booking.query.get(booking_id)
        db.session.delete(b)
        db.session.commit()
        flash('Booking cancelled')
    except:
        flash('Something went wrong')
    return redirect(url_for('index'))


@app.route('/occupancy')
@login_required
def occupancy():
    day_str = request.args.get('date')
    if day_str is None:
        day = date.today()
    else:
        day = datetime.strptime(day_str, '%Y-%m-%d')
    rooms = Room.query.all()
    table = {}
    for room in rooms:
        hours = []
        # hours from open to close, one row per hour
        for h in range(ROOM_OPEN_HOUR, ROOM_CLOSE_HOUR):
            taken = Booking.query.filter(
                Booking.room_id == room.id,
                Booking.date == day,
                Booking.start_hour <= h,
                Booking.end_hour >= h).first()
            hours.append((h, taken is not None))
        table[room.name] = hours
    return render_template('occupancy.html', title='Occupancy', table=table, day=day)
