from app import app,db
from flask import render_template,flash,redirect, request, url_for
from app.forms import *
from app.models import *
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
import sqlite3
from datetime import datetime,date

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods = ['GET','POST'])
def login():
    if current_user.is_authenticated:
            return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user,remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html',title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data,\
                fullname = form.fullname.data, position= form.position.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/book',methods = ['GET','POST'])
@login_required
def book():
    form = BookingForm()
    if form.validate_on_submit():
        booker = current_user
        room = Room.query.filter_by(id = form.rooms.data).first()
        booking = Booking(purpose=form.purpose.data,roomID=room.id,bookerID=booker.id,date=form.date.data,startTime=form.startTime.data,endTime=form.endTime.data)
        db.session.add(booking)
        db.session.commit()
        flash('Booking Successful')
        return redirect(url_for('index'))
    return render_template('booking.html',title='Booking',form=form)

@app.route('/cancelbooking',methods = ['POST', 'GET'])
@login_required
def cancel_booking():
    form = CancelBookingForm()
    if form.validate_on_submit():
        booking = Booking.query.filter_by(id=form.ids.data).first()

        if booking.date<=datetime.now():
            flash("Past Booking, unable to cancel")
            return redirect(url_for('cancel_booking'))

        db.session.delete(booking)
        db.session.commit()
        flash("Booking deleted successfully")
        return redirect(url_for('index'))
    return render_template('cancelbooking.html',title="Cancel Booking", form=form)

@app.route('/roomoccupation',methods = ['GET','POST'])
def room_occupation():
    form = RoomOccupationForm()
    if form.validate_on_submit():
        bookings = Booking.query.filter_by(date=datetime.combine(form.date.data,datetime.min.time())).filter_by(roomID = 1).all()
        print(bookings)
        room_occ_list = []
        times = range(9,19)
        rooms = Room.query.all()
        allrooms = []
        for room in rooms:
            room_oc = dict()
            room_oc['roomNum'] = room.roomNum
            room_oc['roomhours'] = [False]*14
            for hour in times:
                bookings  = Booking.query.filter_by(date=datetime.combine(form.date.data,datetime.min.time())).filter_by(roomID=room.id).all()
                print(datetime.combine(form.date.data,datetime.min.time()))
                for booking in bookings:
                    if hour + 0.5 < booking.endTime and hour +0.5 > booking.startTime:
                        print("idhar")
                        room_oc['roomhours'][hour-9] = True
            room_occ_list.append(room_oc)            
            allrooms.append({'roomNum':room.roomNum,'ac':room.ac,'projector':room.projector})
        return render_template('roomocclist.html',title='Room Occupancy',room_occ_list=room_occ_list, date=form.date.data,hours=[str(hour) for hour in times],allrooms=allrooms)
    return render_template('roomoccupation.html',title='Check Room Occupation',form=form)


