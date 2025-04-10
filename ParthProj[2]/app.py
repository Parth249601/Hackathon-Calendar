from flask import Flask, render_template, jsonify, send_file, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from scrape import fetch_hackathons
from scrape_cf import fetch_contests
import json
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Replace with a strong, persistent secret key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' # Using SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to /login if @login_required fails
socketio = SocketIO(app) # Initialize SocketIO

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    saved_events = db.relationship('SavedEvent', backref='user', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SavedEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_platform = db.Column(db.String(50), nullable=False)
    event_title = db.Column(db.String(200), nullable=False)
    # Using string for start time for simplicity, ensure consistent format
    event_start_time = db.Column(db.String(50), nullable=False) 
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Add a unique constraint for user_id and the event identifier tuple
    __table_args__ = (db.UniqueConstraint('user_id', 'event_platform', 'event_title', 'event_start_time', name='uq_user_event'),)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Optional: Link message to a specific event
    event_platform = db.Column(db.String(50))
    event_title = db.Column(db.String(200))
    event_start_time = db.Column(db.String(50))
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    # Optional: Foreign key constraint linking to SavedEvent if needed
    # event_id = db.Column(db.Integer, db.ForeignKey('saved_event.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.route('/')
def index():
    """print(f"Current working directory: {os.getcwd()}")
    print(f"Flask app root path: {app.root_path}")
    print("Attempting to render index1.html...")"""
    return render_template('index1.html')

@app.route('/api/hackathons')
def get_hackathons():
    url = 'https://devpost.com/hackathons'
    hackathons = fetch_hackathons(url)
    
    # Convert hackathons to calendar events format
    events = []
    for hackathon in hackathons:
        if hackathon.registration_start and hackathon.registration_end:
            event = {
                'title': hackathon.name,
                'start': hackathon.registration_start.isoformat(),
                'end': hackathon.registration_end.isoformat(),
                'location': hackathon.location,
                'prize': hackathon.prize,
                'participants': hackathon.participants,
                'registration_link': hackathon.registration_link,
                'platform': 'Devpost',
                'type': 'hackathon'
            }
            events.append(event)
    
    return jsonify(events)

@app.route('/api/contests')
def get_contests():
    url = 'https://codeforces.com/contests'
    contests = fetch_contests(url)
    
    # Convert contests to calendar events format
    events = []
    for contest in contests:
        if contest.start_date and contest.end_date:
            event = {
                'title': contest.name,
                'start': contest.start_date.isoformat() if contest.start_date else None,
                'end': contest.end_date.isoformat() if contest.end_date else None,
                'registration_start': contest.registration_start.isoformat() if contest.registration_start else None,
                'registration_end': contest.registration_end.isoformat() if contest.registration_end else None,
                'location': contest.location,
                'prize': contest.prize,
                'participants': contest.participants,
                'registration_link': contest.registration_link,
                'duration': contest.duration,
                'platform': 'Codeforces',
                'type': 'contest'
            }
            events.append(event)
    
    return jsonify(events)

@app.route('/api/all-events')
def get_all_events():
    # Still need this endpoint to fetch all events initially
    url_hackathons = 'https://devpost.com/hackathons'
    url_contests = 'https://codeforces.com/contests'
    
    hackathons = fetch_hackathons(url_hackathons)
    contests = fetch_contests(url_contests)
    
    # Convert hackathons to calendar events format
    events = []
    
    # Add hackathon events
    for hackathon in hackathons:
        if hackathon.registration_start and hackathon.registration_end:
            event = {
                'title': hackathon.name,
                'start': hackathon.registration_start.isoformat(),
                'end': hackathon.registration_end.isoformat(),
                'location': hackathon.location,
                'prize': hackathon.prize,
                'participants': hackathon.participants,
                'registration_link': hackathon.registration_link,
                'platform': 'Devpost',
                'type': 'hackathon'
            }
            events.append(event)
    
    # Add contest events
    for contest in contests:
        if contest.start_date and contest.end_date:
            event = {
                'title': contest.name,
                'start': contest.start_date.isoformat() if contest.start_date else None,
                'end': contest.end_date.isoformat() if contest.end_date else None,
                'registration_start': contest.registration_start.isoformat() if contest.registration_start else None,
                'registration_end': contest.registration_end.isoformat() if contest.registration_end else None,
                'location': contest.location,
                'prize': contest.prize,
                'participants': contest.participants,
                'registration_link': contest.registration_link,
                'duration': contest.duration,
                'platform': 'Codeforces',
                'type': 'contest'
            }
            events.append(event)
    
    return jsonify(events)

@app.route('/download/hackathons')
def download_hackathons():
    hackathons = fetch_hackathons('https://devpost.com/hackathons')
    
    # Create ICS file content
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Hackathon Calendar//EN\n"
    
    for hackathon in hackathons:
        if hackathon.registration_start and hackathon.registration_end:
            ics_content += f"BEGIN:VEVENT\n"
            ics_content += f"SUMMARY:{hackathon.name}\n"
            ics_content += f"DTSTART:{hackathon.registration_start.strftime('%Y%m%dT%H%M%S')}\n"
            ics_content += f"DTEND:{hackathon.registration_end.strftime('%Y%m%dT%H%M%S')}\n"
            ics_content += f"LOCATION:{hackathon.location}\n"
            ics_content += f"DESCRIPTION:Platform: Devpost\\nPrize: {hackathon.prize}\\nParticipants: {hackathon.participants}\\nRegistration Link: {hackathon.registration_link}\n"
            ics_content += f"END:VEVENT\n"
    
    ics_content += "END:VCALENDAR"
    
    # Save to temporary file
    with open('hackathons.ics', 'w') as f:
        f.write(ics_content)
    
    return send_file('hackathons.ics',
                    mimetype='text/calendar',
                    as_attachment=True,
                    download_name='hackathons.ics')

@app.route('/download/contests')
def download_contests():
    contests = fetch_contests('https://codeforces.com/contests')
    
    # Create ICS file content
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//CP Contest Calendar//EN\n"
    
    for contest in contests:
        if contest.start_date and contest.end_date:
            ics_content += f"BEGIN:VEVENT\n"
            ics_content += f"SUMMARY:{contest.name}\n"
            ics_content += f"DTSTART:{contest.start_date.strftime('%Y%m%dT%H%M%S')}\n"
            ics_content += f"DTEND:{contest.end_date.strftime('%Y%m%dT%H%M%S')}\n"
            ics_content += f"LOCATION:{contest.location}\n"
            ics_content += f"DESCRIPTION:Platform: Codeforces\\nPrize: {contest.prize}\\nParticipants: {contest.participants}\\nRegistration Start: {contest.registration_start}\\nRegistration End: {contest.registration_end}\\nDuration: {contest.duration}\\nRegistration Link: {contest.registration_link}\n"
            ics_content += f"END:VEVENT\n"
    
    ics_content += "END:VCALENDAR"
    
    # Save to temporary file
    with open('contests.ics', 'w') as f:
        f.write(ics_content)
    
    return send_file('contests.ics',
                    mimetype='text/calendar',
                    as_attachment=True,
                    download_name='contests.ics')

# This route is no longer needed since we removed the All Events tab
# @app.route('/download/all-events')
# def download_all_events():
#     hackathons = fetch_hackathons('https://devpost.com/hackathons')
#     contests = fetch_contests('https://codeforces.com/contests')
#     
#     # Create ICS file content
#     ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Event Calendar//EN\n"
#     
#     # Add hackathons
#     for hackathon in hackathons:
#         if hackathon.registration_start and hackathon.registration_end:
#             ics_content += f"BEGIN:VEVENT\n"
#             ics_content += f"SUMMARY:[Hackathon] {hackathon.name}\n"
#             ics_content += f"DTSTART:{hackathon.registration_start.strftime('%Y%m%dT%H%M%S')}\n"
#             ics_content += f"DTEND:{hackathon.registration_end.strftime('%Y%m%dT%H%M%S')}\n"
#             ics_content += f"LOCATION:{hackathon.location}\n"
#             ics_content += f"DESCRIPTION:Platform: Devpost\\nPrize: {hackathon.prize}\\nParticipants: {hackathon.participants}\\nRegistration Link: {hackathon.registration_link}\n"
#             ics_content += f"END:VEVENT\n"
#     
#     # Add contests
#     for contest in contests:
#         if contest.start_date and contest.end_date:
#             ics_content += f"BEGIN:VEVENT\n"
#             ics_content += f"SUMMARY:[CP] {contest.name}\n"
#             ics_content += f"DTSTART:{contest.start_date.strftime('%Y%m%dT%H%M%S')}\n"
#             ics_content += f"DTEND:{contest.end_date.strftime('%Y%m%dT%H%M%S')}\n"
#             ics_content += f"LOCATION:{contest.location}\n"
#             ics_content += f"DESCRIPTION:Platform: Codeforces\\nPrize: {contest.prize}\\nParticipants: {contest.participants}\\nRegistration Start: {contest.registration_start}\\nRegistration End: {contest.registration_end}\\nDuration: {contest.duration}\\nRegistration Link: {contest.registration_link}\n"
#             ics_content += f"END:VEVENT\n"
#     
#     ics_content += "END:VCALENDAR"
#     
#     # Save to temporary file
#     with open('all_events.ics', 'w') as f:
#         f.write(ics_content)
#     
#     return send_file('all_events.ics',
#                     mimetype='text/calendar',
#                     as_attachment=True,
#                     download_name='all_events.ics')

# --- Authentication Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('register'))
        
        if not username or not password:
             flash('Username and password are required.')
             return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html') # Need to create this template

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))
    return render_template('login.html') # Need to create this template

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

# Context processor to make unread message count available in all templates
@app.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        unread_count = Message.query.filter_by(recipient_id=current_user.id, read=False).count()
        return {'unread_message_count': unread_count}
    return {'unread_message_count': 0}

# --- Event Interaction Routes ---

@app.route('/save_event', methods=['POST'])
@login_required
def save_event():
    platform = request.form.get('platform')
    title = request.form.get('title')
    start_time = request.form.get('start') # Assuming 'start' from frontend event data

    if not platform or not title or not start_time:
        return jsonify({'success': False, 'message': 'Missing event data.'}), 400

    # Check if already saved
    existing_save = SavedEvent.query.filter_by(
        user_id=current_user.id,
        event_platform=platform,
        event_title=title,
        event_start_time=start_time
    ).first()

    if existing_save:
        return jsonify({'success': False, 'message': 'Event already saved.'}), 409 # Conflict

    try:
        new_save = SavedEvent(
            user_id=current_user.id,
            event_platform=platform,
            event_title=title,
            event_start_time=start_time
        )
        db.session.add(new_save)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Event saved successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        # Log the error e
        return jsonify({'success': False, 'message': 'Failed to save event.'}), 500

@app.route('/find_teammates')
@login_required
def find_teammates():
    platform = request.args.get('platform')
    title = request.args.get('title')
    start_time = request.args.get('start')

    if not platform or not title or not start_time:
        return jsonify({'success': False, 'teammates': [], 'message': 'Missing event data.'}), 400

    try:
        # Find all saves for this specific event
        event_saves = SavedEvent.query.filter_by(
            event_platform=platform,
            event_title=title,
            event_start_time=start_time
        ).all()

        # Get the user IDs, excluding the current user
        potential_teammate_ids = [save.user_id for save in event_saves if save.user_id != current_user.id]
        
        # Fetch the usernames
        potential_teammates = User.query.filter(User.id.in_(potential_teammate_ids)).all()
        teammate_usernames = [user.username for user in potential_teammates]

        return jsonify({'success': True, 'teammates': teammate_usernames})
    except Exception as e:
        # Log the error e
        return jsonify({'success': False, 'teammates': [], 'message': 'Failed to fetch potential teammates.'}), 500

# --- Messaging Routes ---

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    recipient_username = request.form.get('recipient_username')
    body = request.form.get('body')
    event_platform = request.form.get('event_platform') # Optional
    event_title = request.form.get('event_title')       # Optional
    event_start_time = request.form.get('event_start') # Optional

    if not recipient_username or not body:
        return jsonify({'success': False, 'message': 'Recipient and message body are required.'}), 400

    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({'success': False, 'message': 'Recipient user not found.'}), 404

    if recipient.id == current_user.id:
         return jsonify({'success': False, 'message': 'Cannot send message to yourself.'}), 400

    try:
        msg = Message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            body=body,
            event_platform=event_platform, 
            event_title=event_title, 
            event_start_time=event_start_time
        )
        db.session.add(msg)
        db.session.commit()
        
        # Emit a new message event to the recipient
        msg_data = {
            'id': msg.id,
            'sender': current_user.username,
            'sender_id': current_user.id,
            'body': msg.body,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
            'event_platform': msg.event_platform,
            'event_title': msg.event_title,
            'event_start_time': msg.event_start_time
        }
        socketio.emit('new_message', msg_data, room=f'user_{recipient.id}')
        
        return jsonify({'success': True, 'message': 'Message sent successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        # Log the error e
        return jsonify({'success': False, 'message': 'Failed to send message.'}), 500

@app.route('/messages')
@login_required
def messages():
    received_msgs = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.timestamp.desc()).all()
    sent_msgs = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
    
    # Mark messages as read
    for msg in received_msgs:
        if not msg.read:
            msg.read = True
    
    # Commit changes if any messages were marked as read
    if any(not msg.read for msg in received_msgs):
        db.session.commit()
    
    # You might want to group messages by sender or conversation thread in a real app
    return render_template('messages.html', 
                          received_messages=received_msgs, 
                          sent_messages=sent_msgs,
                          users=User.query.all())

@app.route('/mark_message_read', methods=['POST'])
@login_required
def mark_message_read():
    message_id = request.form.get('message_id')
    
    if not message_id:
        return jsonify({'success': False, 'message': 'Message ID is required.'}), 400
    
    try:
        message = Message.query.get(message_id)
        
        if not message:
            return jsonify({'success': False, 'message': 'Message not found.'}), 404
        
        # Ensure the user is the recipient of the message
        if message.recipient_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized.'}), 403
        
        message.read = True
        db.session.commit()
        
        # Update the unread count for the badge
        unread_count = Message.query.filter_by(recipient_id=current_user.id, read=False).count()
        
        return jsonify({
            'success': True, 
            'message': 'Message marked as read.',
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to mark message as read.'}), 500

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # Join a room specific to this user
        join_room(f'user_{current_user.id}')
        print(f"User {current_user.username} connected and joined room user_{current_user.id}")

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        # Leave the user-specific room
        leave_room(f'user_{current_user.id}')
        print(f"User {current_user.username} disconnected")

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
    # Use socketio.run instead of app.run
    socketio.run(app, debug=True, port=5001)