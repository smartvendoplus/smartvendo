#!/usr/bin/env python3
"""
SmartVendo+ - Raspberry Pi Flask Server
Main application serving both user (7" display) and admin interfaces
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import threading
import serial
import time

# Configuration
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'smartvendo+_secret_key_2025'
app.config['DATABASE'] = 'database/smartvendo.db'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ADMIN_EMAIL'] = 'admin.smartvendo@gmail.com'
app.config['ADMIN_PASSWORD'] = 'Admin@2025'  # In production, use environment variables

socketio = SocketIO(app, cors_allowed_origins="*")

# RFID Reader Thread
rfid_thread = None
rfid_active = True
current_rfid_uid = None

# Database Helper Functions
def get_db():
    """Get database connection"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with tables"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfid_uid TEXT UNIQUE NOT NULL,
                student_id TEXT,
                email TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiration_date TIMESTAMP,
                balance REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT 1,
                last_login TIMESTAMP
            )
        ''')
        
        # Deposit history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_type TEXT NOT NULL,
                points_earned INTEGER,
                status TEXT DEFAULT 'pending',
                validation_result TEXT,
                deposit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Rewards (items)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                image_filename TEXT,
                cost INTEGER NOT NULL,
                stock INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Redeem history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS redeems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reward_id INTEGER,
                points_spent INTEGER,
                redeem_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (reward_id) REFERENCES rewards (id)
            )
        ''')
        
        # System logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default rewards if not exists
        default_rewards = [
            ('pencil', 'Pencil', 'pencil.png', 100, 50),
            ('eraser', 'Eraser', 'eraser.png', 150, 30),
            ('ballpen', 'Ballpen', 'ballpen.png', 100, 40)
        ]
        
        for reward in default_rewards:
            cursor.execute('''
                INSERT OR IGNORE INTO rewards (name, display_name, image_filename, cost, stock)
                VALUES (?, ?, ?, ?, ?)
            ''', reward)
        
        db.commit()
        print("Database initialized successfully")

def log_event(event_type, event_data):
    """Log system events"""
    db = get_db()
    db.execute('INSERT INTO system_logs (event_type, event_data) VALUES (?, ?)',
               (event_type, json.dumps(event_data)))
    db.commit()

# RFID Reader Function (Simulated or Real)
def read_rfid():
    """RFID reader thread function"""
    global current_rfid_uid
    
    # This is a simulation - in real implementation, use python-periphery or similar
    # For actual RFID reader connected via USB/serial
    print("RFID Reader thread started...")
    
    while rfid_active:
        try:
            # Simulate RFID reading - replace with actual RFID reading code
            # Example for USB RFID reader:
            # ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
            # rfid_data = ser.readline().decode().strip()
            
            # For now, we'll simulate with keyboard input for testing
            # In production, remove this and use actual RFID hardware
            time.sleep(0.1)
            
        except Exception as e:
            print(f"RFID Reader error: {e}")
            time.sleep(1)

# Start RFID reader thread
def start_rfid_reader():
    """Start RFID reader in background thread"""
    global rfid_thread
    if rfid_thread is None or not rfid_thread.is_alive():
        rfid_thread = threading.Thread(target=read_rfid, daemon=True)
        rfid_thread.start()
        print("RFID Reader thread started")

# User Routes
@app.route('/')
def index():
    """Main entry point - shows on 7" display"""
    return render_template('user/index.html')

@app.route('/welcome')
def welcome():
    """Welcome screen with login/signup options"""
    return render_template('user/welcome.html')

@app.route('/id-login')
def id_login():
    """RFID login page"""
    return render_template('user/id-login.html')

@app.route('/signup')
def signup():
    """User agreement/signup"""
    return render_template('user/signup.html')

@app.route('/signup-rfid')
def signup_rfid():
    """RFID registration page"""
    return render_template('user/signup-rfid.html')

@app.route('/signup-complete')
def signup_complete():
    """Registration completion"""
    return render_template('user/signup-complete.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('id_login'))
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if user is None:
        return redirect(url_for('id_login'))
    
    return render_template('user/dashboard.html', user=user)

# Admin Routes
@app.route('/admin')
def admin_login():
    """Admin login page"""
    return render_template('admin/admin-welcome.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    db = get_db()
    
    # Get statistics
    stats = {
        'total_users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'active_users': db.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0],
        'total_deposits': db.execute('SELECT COUNT(*) FROM deposits').fetchone()[0],
        'total_redeems': db.execute('SELECT COUNT(*) FROM redeems').fetchone()[0],
        'total_points': db.execute('SELECT SUM(balance) FROM users').fetchone()[0] or 0
    }
    
    # Get recent activities
    recent_deposits = db.execute('''
        SELECT d.*, u.rfid_uid FROM deposits d
        JOIN users u ON d.user_id = u.id
        ORDER BY d.deposit_date DESC LIMIT 10
    ''').fetchall()
    
    recent_redeems = db.execute('''
        SELECT r.*, u.rfid_uid, rew.name as reward_name FROM redeems r
        JOIN users u ON r.user_id = u.id
        JOIN rewards rew ON r.reward_id = rew.id
        ORDER BY r.redeem_date DESC LIMIT 10
    ''').fetchall()
    
    return render_template('admin/admin-dashboard.html', 
                         stats=stats, 
                         recent_deposits=recent_deposits,
                         recent_redeems=recent_redeems)

# API Routes
@app.route('/api/rfid/read', methods=['POST'])
def api_rfid_read():
    """API endpoint for RFID reading"""
    data = request.json
    rfid_uid = data.get('uid')
    
    if not rfid_uid:
        return jsonify({'success': False, 'message': 'No RFID UID provided'})
    
    db = get_db()
    
    # Check if RFID exists
    user = db.execute('SELECT * FROM users WHERE rfid_uid = ?', (rfid_uid,)).fetchone()
    
    if user:
        # Existing user - login
        session['user_id'] = user['id']
        
        # Update last login
        db.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
        db.commit()
        
        log_event('user_login', {'user_id': user['id'], 'rfid_uid': rfid_uid})
        
        return jsonify({
            'success': True,
            'action': 'login',
            'user': dict(user),
            'message': 'Welcome back!'
        })
    else:
        # New user - registration
        return jsonify({
            'success': True,
            'action': 'register',
            'rfid_uid': rfid_uid,
            'message': 'New RFID detected. Please complete registration.'
        })

@app.route('/api/user/register', methods=['POST'])
def api_user_register():
    """Register new user with RFID"""
    data = request.json
    rfid_uid = data.get('rfid_uid')
    student_id = data.get('student_id')
    email = data.get('email')
    
    if not rfid_uid:
        return jsonify({'success': False, 'message': 'RFID UID required'})
    
    db = get_db()
    
    # Check if RFID already registered
    existing = db.execute('SELECT id FROM users WHERE rfid_uid = ?', (rfid_uid,)).fetchone()
    if existing:
        return jsonify({'success': False, 'message': 'RFID already registered'})
    
    # Set expiration date (2 months from now)
    expiration_date = datetime.now() + timedelta(days=60)
    
    # Insert new user
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO users (rfid_uid, student_id, email, expiration_date, balance, is_active)
        VALUES (?, ?, ?, ?, 0.0, 1)
    ''', (rfid_uid, student_id, email, expiration_date))
    
    user_id = cursor.lastrowid
    db.commit()
    
    log_event('user_register', {'user_id': user_id, 'rfid_uid': rfid_uid})
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'message': 'Registration successful'
    })

@app.route('/api/user/deposit', methods=['POST'])
def api_user_deposit():
    """Handle item deposit"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.json
    item_type = data.get('item_type')  # 'paper' or 'plastic'
    
    if item_type not in ['paper', 'plastic']:
        return jsonify({'success': False, 'message': 'Invalid item type'})
    
    db = get_db()
    
    # Calculate points (from config)
    points = 5 if item_type == 'paper' else 10
    
    # Get current user balance
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Update balance
    new_balance = user['balance'] + points
    db.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, session['user_id']))
    
    # Record deposit
    db.execute('''
        INSERT INTO deposits (user_id, item_type, points_earned, status, validation_result)
        VALUES (?, ?, ?, 'completed', 'valid')
    ''', (session['user_id'], item_type, points))
    
    db.commit()
    
    log_event('item_deposit', {
        'user_id': session['user_id'],
        'item_type': item_type,
        'points': points,
        'new_balance': new_balance
    })
    
    return jsonify({
        'success': True,
        'points_earned': points,
        'new_balance': new_balance,
        'message': f'Successfully deposited {item_type}. Earned {points} points.'
    })

@app.route('/api/user/redeem', methods=['POST'])
def api_user_redeem():
    """Handle reward redemption"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.json
    reward_name = data.get('reward_name')
    
    db = get_db()
    
    # Get reward details
    reward = db.execute('SELECT * FROM rewards WHERE name = ? AND is_active = 1', (reward_name,)).fetchone()
    
    if not reward:
        return jsonify({'success': False, 'message': 'Reward not available'})
    
    if reward['stock'] <= 0:
        return jsonify({'success': False, 'message': 'Reward out of stock'})
    
    # Get user details
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if user['balance'] < reward['cost']:
        return jsonify({'success': False, 'message': 'Insufficient points'})
    
    # Process redemption
    new_balance = user['balance'] - reward['cost']
    new_stock = reward['stock'] - 1
    
    # Update database
    cursor = db.cursor()
    
    # Update user balance
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, session['user_id']))
    
    # Update reward stock
    cursor.execute('UPDATE rewards SET stock = ? WHERE id = ?', (new_stock, reward['id']))
    
    # Record redemption
    cursor.execute('''
        INSERT INTO redeems (user_id, reward_id, points_spent)
        VALUES (?, ?, ?)
    ''', (session['user_id'], reward['id'], reward['cost']))
    
    db.commit()
    
    log_event('reward_redeem', {
        'user_id': session['user_id'],
        'reward_id': reward['id'],
        'reward_name': reward['name'],
        'points_spent': reward['cost'],
        'new_balance': new_balance,
        'new_stock': new_stock
    })
    
    return jsonify({
        'success': True,
        'reward_name': reward['display_name'],
        'points_spent': reward['cost'],
        'new_balance': new_balance,
        'message': f'Successfully redeemed {reward["display_name"]}'
    })

# Admin API Routes
@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    """Admin login endpoint"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if email == app.config['ADMIN_EMAIL'] and password == app.config['ADMIN_PASSWORD']:
        session['admin_logged_in'] = True
        log_event('admin_login', {'email': email})
        return jsonify({'success': True, 'redirect': '/admin/dashboard'})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/api/admin/rewards', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_admin_rewards():
    """CRUD operations for rewards"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    db = get_db()
    
    if request.method == 'GET':
        # Get all rewards
        rewards = db.execute('SELECT * FROM rewards ORDER BY name').fetchall()
        return jsonify({'success': True, 'rewards': [dict(r) for r in rewards]})
    
    elif request.method == 'POST':
        # Create new reward
        data = request.json
        name = data.get('name')
        display_name = data.get('display_name', name)
        image_filename = data.get('image_filename', f'{name}.png')
        cost = data.get('cost', 0)
        stock = data.get('stock', 0)
        
        if not name:
            return jsonify({'success': False, 'message': 'Reward name required'})
        
        try:
            db.execute('''
                INSERT INTO rewards (name, display_name, image_filename, cost, stock)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, display_name, image_filename, cost, stock))
            db.commit()
            
            log_event('reward_create', data)
            return jsonify({'success': True, 'message': 'Reward created successfully'})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Reward name already exists'})
    
    elif request.method == 'PUT':
        # Update reward
        data = request.json
        reward_id = data.get('id')
        
        if not reward_id:
            return jsonify({'success': False, 'message': 'Reward ID required'})
        
        # Build update query dynamically
        updates = []
        params = []
        
        if 'display_name' in data:
            updates.append('display_name = ?')
            params.append(data['display_name'])
        
        if 'image_filename' in data:
            updates.append('image_filename = ?')
            params.append(data['image_filename'])
        
        if 'cost' in data:
            updates.append('cost = ?')
            params.append(data['cost'])
        
        if 'stock' in data:
            updates.append('stock = ?')
            params.append(data['stock'])
        
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(data['is_active'])
        
        if not updates:
            return jsonify({'success': False, 'message': 'No fields to update'})
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(reward_id)
        
        query = f'UPDATE rewards SET {", ".join(updates)} WHERE id = ?'
        
        db.execute(query, params)
        db.commit()
        
        log_event('reward_update', data)
        return jsonify({'success': True, 'message': 'Reward updated successfully'})
    
    elif request.method == 'DELETE':
        # Delete reward (soft delete by setting inactive)
        data = request.json
        reward_id = data.get('id')
        
        if not reward_id:
            return jsonify({'success': False, 'message': 'Reward ID required'})
        
        db.execute('UPDATE rewards SET is_active = 0 WHERE id = ?', (reward_id,))
        db.commit()
        
        log_event('reward_delete', {'reward_id': reward_id})
        return jsonify({'success': True, 'message': 'Reward deleted successfully'})

@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    """Get all users for admin"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    db = get_db()
    users = db.execute('''
        SELECT u.*, 
               COUNT(d.id) as deposit_count,
               COUNT(r.id) as redeem_count,
               SUM(d.points_earned) as total_points_earned
        FROM users u
        LEFT JOIN deposits d ON u.id = d.user_id
        LEFT JOIN redeems r ON u.id = r.user_id
        GROUP BY u.id
        ORDER BY u.registration_date DESC
    ''').fetchall()
    
    return jsonify({'success': True, 'users': [dict(u) for u in users]})

@app.route('/api/admin/stats', methods=['GET'])
def api_admin_stats():
    """Get detailed statistics for admin dashboard"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    db = get_db()
    
    # Get daily deposits for last 7 days
    daily_deposits = db.execute('''
        SELECT DATE(deposit_date) as date, 
               COUNT(*) as count,
               SUM(points_earned) as total_points
        FROM deposits
        WHERE deposit_date >= date('now', '-7 days')
        GROUP BY DATE(deposit_date)
        ORDER BY date
    ''').fetchall()
    
    # Get deposit by type
    deposit_by_type = db.execute('''
        SELECT item_type, COUNT(*) as count, SUM(points_earned) as total_points
        FROM deposits
        GROUP BY item_type
    ''').fetchall()
    
    # Get redeem by reward
    redeem_by_reward = db.execute('''
        SELECT r.name, rew.display_name, COUNT(*) as count, SUM(rew.cost) as total_points
        FROM redeems r
        JOIN rewards rew ON r.reward_id = rew.id
        GROUP BY r.reward_id
        ORDER BY count DESC
    ''').fetchall()
    
    return jsonify({
        'success': True,
        'daily_deposits': [dict(d) for d in daily_deposits],
        'deposit_by_type': [dict(d) for d in deposit_by_type],
        'redeem_by_reward': [dict(r) for r in redeem_by_reward]
    })

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('rfid_detected')
def handle_rfid_detected(data):
    """Handle RFID detection via WebSocket"""
    rfid_uid = data.get('uid')
    emit('rfid_status', {'uid': rfid_uid, 'status': 'processing'})
    
    # Process RFID
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE rfid_uid = ?', (rfid_uid,)).fetchone()
    
    if user:
        emit('rfid_result', {
            'action': 'login',
            'user': dict(user),
            'message': f'Welcome back! Balance: {user["balance"]} points'
        })
    else:
        emit('rfid_result', {
            'action': 'register',
            'rfid_uid': rfid_uid,
            'message': 'New RFID detected. Please register.'
        })

# File upload for admin
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/api/admin/upload', methods=['POST'])
def upload_file():
    """Upload reward images"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return jsonify({'success': True, 'filename': filename, 'message': 'File uploaded successfully'})
    
    return jsonify({'success': False, 'message': 'File type not allowed'})

# Initialization
@app.before_first_request
def initialize():
    """Initialize database and start RFID reader"""
    print("Initializing SmartVendo+ system...")
    
    # Create directories if they don't exist
    os.makedirs('database', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    
    # Initialize database
    init_db()
    
    # Start RFID reader thread
    start_rfid_reader()
    
    print("System initialized successfully")

if __name__ == '__main__':
    # Run the Flask app with SocketIO
    print("Starting SmartVendo+ server...")
    print(f"Admin login: {app.config['ADMIN_EMAIL']}")
    print(f"Password: {app.config['ADMIN_PASSWORD']}")
    print("Open http://localhost:5000 for user interface (7\" display)")
    print("Open http://localhost:5000/admin for admin interface")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)