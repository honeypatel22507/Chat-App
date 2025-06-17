from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import random
import string
import os
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active rooms with their participants
rooms = {}

# WhatsApp-like colors for usernames
USER_COLORS = [
    '#FF6B6B', '#4ECDC4', '#f7e705', 
    '#A06CD5', '#79D45E', '#f79605'
    # '#F86624', '#43AA8B', '#277DA1', '#577590',
    # '#4D908E', '#F94144', '#F3722C', '#90BE6D',
    # '#DC2F02', '#9D4EDD', '#ff006e', '#3a86ff'
]

def generate_unique_code():
    """Generate a unique 6-digit code that isn't already in use."""
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        if code not in rooms:
            return code

def get_user_color(username):
    """Generate a consistent color for a username."""
    # Create a hash of the username
    hash_value = int(hashlib.md5(username.encode()).hexdigest(), 16)
    # Use the hash to select a color
    return USER_COLORS[hash_value % len(USER_COLORS)]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        join = request.form.get('join', False)
        create = request.form.get('create', False)
        
        if not name:
            return render_template('index.html', error="Please enter a name.", code=code)
        
        if join and not code:
            return render_template('index.html', error="Please enter a room code.", name=name)
        
        # Store the room code and user name in session
        session['room'] = code
        session['name'] = name
        
        # Create a new room
        if create:
            room_code = generate_unique_code()
            rooms[room_code] = {"members": 0, "messages": []}
            session['room'] = room_code
            return redirect(url_for('room'))
        
        # Join an existing room
        if code not in rooms:
            return render_template('index.html', error="Room does not exist.", name=name)
        
        return redirect(url_for('room'))
    
    return render_template('index.html')

@app.route('/room')
def room():
    room = session.get('room')
    name = session.get('name')
    
    if not room or not name or room not in rooms:
        return redirect(url_for('index'))
    
    # Pass the get_user_color function to the template
    return render_template('room.html', room=room, name=name, messages=rooms[room]["messages"], get_user_color=get_user_color)

@socketio.on('connect')
def handle_connect():
    room = session.get('room')
    name = session.get('name')
    
    if not room or not name:
        return
    
    if room not in rooms:
        rooms[room] = {"members": 0, "messages": []}
    
    join_room(room)
    rooms[room]["members"] += 1
    
    # Send join notification to room
    send({
        "name": name,
        "message": "has entered the room"
    }, to=room)
    
    print(f"{name} joined room {room}")

@socketio.on('disconnect')
def handle_disconnect():
    room = session.get('room')
    name = session.get('name')
    
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        else:
            # Send leave notification to room
            leave_room(room)
            send({
                "name": name,
                "message": "has left the room"
            }, to=room)
    
    print(f"{name} left room {room}")

@socketio.on('message')
def handle_message(data):
    room = session.get('room')
    name = session.get('name')
    
    if room not in rooms:
        return
    
    message_content = {
        "name": name,
        "message": data["message"]
    }
    
    # Store the message in room history
    rooms[room]["messages"].append(message_content)
    # Limit message history
    if len(rooms[room]["messages"]) > 100:
        rooms[room]["messages"] = rooms[room]["messages"][-100:]
    
    # Send the message to room
    send(message_content, to=room)

if __name__ == '__main__':
    # socketio.run(app, debug=True)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)