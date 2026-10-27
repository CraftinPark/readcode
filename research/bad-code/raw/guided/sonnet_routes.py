from datetime import datetime, date, timedelta
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.models import User, Room, Booking
from app.forms import LoginForm, RegistrationForm, BookingForm


@app.route('/')
@app.route('/index')
def index():
    # show the next 5 bookings for the logged in user
    if current_user.is_authenticated:
        bookings = Booking.query.filter_by(user_id=current_user.id).all()
    else:
        bookings = []
    return render_template('index.html', title='Home', bookings=bookings)


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
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


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
        print("logged in", user.username)
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    form = BookingForm()
    form.room.choices = [(r.id, r.name) for r in Room.query.all()]
    if form.validate_on_submit():
        room_id = form.room.data
        d = form.date.data
        start = form.start_hour.data
        end = form.end_hour.data
        print(room_id, d, start, end)

        # check that the date is not in the past
        if d < datetime.now():
            flash('You cant book a room in the past!')
            return redirect(url_for('book'))

        if end < start:
            flash('End time must be after start time')
            return redirect(url_for('book'))

        # TODO: check if the room is already booked at that time

        b = Booking(room_id=room_id, user_id=current_user.id, date=d,
                    start_hour=start, end_hour=end)
        db.session.add(b)
        db.session.commit()
        flash('Room booked!')
        return redirect(url_for('index'))
    return render_template('book.html', title='Book a room', form=form)


@app.route('/cancel/<id>')
@login_required
def cancel(id):
    booking = Booking.query.get(id)
    if booking is None:
        flash('Booking not found')
        return redirect(url_for('index'))
    # only the owner can cancel
    db.session.delete(booking)
    db.session.commit()
    flash('Booking cancelled')
    return redirect(url_for('index'))


@app.route('/occupied', methods=['GET'])
def occupied():
    dateStr = request.args.get('date')
    if dateStr:
        the_date = datetime.strptime(dateStr, '%Y-%m-%d').date()
    else:
        the_date = date.today()

    rooms = Room.query.all()
    table = {}
    for room in rooms:
        table[room.name] = {}
        # lecture rooms are open 8 to 18
        for hour in range(8, 18):
            # TODO: do this with one query instead
            count = Booking.query.filter(Booking.room_id == room.id,
                                         Booking.date == the_date,
                                         Booking.start_hour <= hour,
                                         Booking.end_hour > hour).count()
            table[room.name][hour] = count > 0

    prev_day = the_date - timedelta(days=1)
    next_day = the_date + timedelta(days=1)
    return render_template('occupied.html', title='Occupied rooms', table=table,
                           hours=range(8, 18), the_date=the_date,
                           prev_day=prev_day, next_day=next_day)


@app.route('/my_bookings')
@login_required
def myBookings():
    data = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.date).all()
    temp = []
    for x in data:
        room = Room.query.get(x.room_id)
        temp.append({'room': room.name, 'date': x.date, 'start': x.start_hour,
                     'end': x.end_hour, 'id': x.id})
    return render_template('my_bookings.html', bookings=temp)


@app.route('/admin')
@login_required
def admin():
    # only admin
    if current_user.id != 1:
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin.html', users=users)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


#@app.route('/room/<name>')
#def room(name):
#    r = Room.query.filter_by(name=name).first_or_404()
#    return render_template('room.html', room=r)
