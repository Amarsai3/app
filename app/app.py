from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    pin = db.Column(db.String(10))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100))
    username = db.Column(db.String(150))
    content = db.Column(db.String(500))

# Auth decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("Login required.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

# Routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session['username'], joined_room=session.get('joined_room'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
        else:
            db.session.add(User(username=username, password=password))
            db.session.commit()
            flash('Registered successfully.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    name = request.form['room_name']
    pin = request.form['pin']
    if ChatRoom.query.filter_by(name=name).first():
        flash("Room already exists.")
    else:
        db.session.add(ChatRoom(name=name, pin=pin))
        db.session.commit()
        flash("Room created.")
    return redirect(url_for('index'))

@app.route('/join_room', methods=['POST'])
@login_required
def join_room_route():
    name = request.form['room_name']
    pin = request.form['pin']
    room = ChatRoom.query.filter_by(name=name, pin=pin).first()
    if room:
        session['joined_room'] = name
        flash(f"Joined room {name}.")
    else:
        flash("Invalid room or pin.")
    return redirect(url_for('index'))

@app.route('/delete_room', methods=['POST'])
@login_required
def delete_room():
    name = request.form['room_name']
    pin = request.form['pin']
    room = ChatRoom.query.filter_by(name=name, pin=pin).first()
    if room:
        Message.query.filter_by(room=name).delete()
        db.session.delete(room)
        db.session.commit()
        flash(f"Room '{name}' deleted.")
        if session.get('joined_room') == name:
            session.pop('joined_room')
    else:
        flash("Incorrect room name or PIN.")
    return redirect(url_for('index'))

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    msg = Message(username=data['username'], room=room, content=data['message'])
    db.session.add(msg)
    db.session.commit()
    emit('receive_message', data, to=room)

@socketio.on('join')
def handle_join(data):
    join_room(data['room'])
    messages = Message.query.filter_by(room=data['room']).all()
    for msg in messages:
        emit('receive_message', {
            'username': msg.username,
            'message': msg.content,
            'room': msg.room
        }, room=request.sid)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
