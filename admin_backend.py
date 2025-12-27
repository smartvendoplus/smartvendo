#!/usr/bin/env python3
"""
SmartVendo+ Admin Backend - GitHub Deployment
"""

import os
import json
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import hashlib
import hmac

# Configuration
RASPBERRY_PI_URL = os.environ.get('RASPBERRY_PI_URL', 'http://localhost:5000')
ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'admin_secret_key_2025')
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'admin_secret_key_2025')

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = ADMIN_SECRET_KEY
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("admin_backend")

# Admin credentials (in production, use database)
ADMIN_USERS = {
    'admin@nu.edu.ph': {
        'password': 'admin123',  # In production, use hashed passwords
        'name': 'System Administrator'
    }
}

# Helper function to send commands to Raspberry Pi
def send_to_raspberry_pi(command):
    """Send command to Raspberry Pi"""
    try:
        response = requests.post(
            f'{RASPBERRY_PI_URL}/api/admin/command',
            json={
                'command': command,
                'secret': GITHUB_WEBHOOK_SECRET
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error sending command to Raspberry Pi: {e}")
        return {'error': str(e)}

# Authentication decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('admin-index.html')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = ADMIN_USERS.get(email)
        if not user or user['password'] != password:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Set session
        session['admin_logged_in'] = True
        session['admin_email'] = email
        session['admin_name'] = user['name']
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'email': email,
                'name': user['name']
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/admin/status')
@admin_required
def admin_status():
    """Get admin and system status"""
    try:
        # Check Raspberry Pi connection
        pi_status = {'connected': False}
        try:
            response = requests.get(f'{RASPBERRY_PI_URL}/api/admin/arduino-status', timeout=5)
            if response.status_code == 200:
                pi_status = response.json()
        except:
            pass
        
        return jsonify({
            'success': True,
            'admin': {
                'logged_in': True,
                'email': session.get('admin_email'),
                'name': session.get('admin_name')
            },
            'raspberry_pi': pi_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/command', methods=['POST'])
@admin_required
def send_admin_command():
    """Send admin command to Raspberry Pi"""
    try:
        data = request.get_json()
        command = data.get('command')
        
        if not command:
            return jsonify({'error': 'No command provided'}), 400
        
        # Validate command
        valid_commands = [
            'START:SHREDDING',
            'STOP:SHREDDING',
            'RELAYON',
            'RELAYOFF',
            'CLEARALLMAINTENANCE'
        ]
        
        if command not in valid_commands and not command.startswith('UPDATE_REWARD:'):
            return jsonify({'error': 'Invalid command'}), 400
        
        # Send command to Raspberry Pi
        result = send_to_raspberry_pi(command)
        
        # Log the command
        logger.info(f"Admin command sent: {command} - Result: {result}")
        
        return jsonify({
            'success': 'error' not in result,
            'message': f'Command "{command}" sent to Raspberry Pi',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/user-stats')
@admin_required
def get_admin_user_stats():
    """Get user statistics from Raspberry Pi"""
    try:
        response = requests.get(
            f'{RASPBERRY_PI_URL}/api/admin/user-stats',
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch user stats'}), 500
            
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/system-logs')
@admin_required
def get_admin_system_logs():
    """Get system logs from Raspberry Pi"""
    try:
        limit = request.args.get('limit', 100)
        log_type = request.args.get('type', 'all')
        
        response = requests.get(
            f'{RASPBERRY_PI_URL}/api/admin/system-logs',
            params={'limit': limit, 'type': log_type},
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch system logs'}), 500
            
    except Exception as e:
        logger.error(f"Error fetching system logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-reward', methods=['POST'])
@admin_required
def update_reward_admin():
    """Update reward item via Raspberry Pi"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        item_id = data.get('item_id')
        new_name = data.get('new_name')
        new_image = data.get('new_image')
        
        if not all([item_id, new_name, new_image]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Send to Raspberry Pi
        response = requests.post(
            f'{RASPBERRY_PI_URL}/api/admin/update-reward',
            json={
                'item_id': item_id,
                'new_name': new_name,
                'new_image': new_image,
                'secret': GITHUB_WEBHOOK_SECRET
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({'error': 'Failed to update reward'}), 500
            
    except Exception as e:
        logger.error(f"Error updating reward: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/rewards')
@admin_required
def get_rewards():
    """Get current rewards from Raspberry Pi"""
    try:
        # In production, this would fetch from database
        # For now, return static list
        rewards = [
            {
                'id': 1,
                'name': 'Pencil',
                'image': 'pencil.png',
                'stock': 15,
                'price': 100,
                'category': 'stationery'
            },
            {
                'id': 2,
                'name': 'Eraser',
                'image': 'eraser.png',
                'stock': 10,
                'price': 150,
                'category': 'stationery'
            },
            {
                'id': 3,
                'name': 'Ballpen',
                'image': 'ballpen.png',
                'stock': 20,
                'price': 100,
                'category': 'stationery'
            }
        ]
        
        return jsonify({
            'success': True,
            'rewards': rewards,
            'count': len(rewards)
        })
        
    except Exception as e:
        logger.error(f"Error getting rewards: {e}")
        return jsonify({'error': str(e)}), 500

# GitHub Webhook endpoint (optional)
@app.route('/webhook/github', methods=['POST'])
def github_webhook():
    """Handle GitHub webhooks"""
    try:
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return jsonify({'error': 'No signature'}), 401
        
        payload = request.data
        secret = GITHUB_WEBHOOK_SECRET.encode()
        
        expected_signature = 'sha256=' + hmac.new(
            secret, payload, hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse webhook payload
        event = request.headers.get('X-GitHub-Event')
        payload_json = request.get_json()
        
        logger.info(f"GitHub webhook received: {event}")
        
        # Handle different events
        if event == 'push':
            # Handle code push - could trigger deployments
            repo = payload_json.get('repository', {}).get('full_name', 'unknown')
            branch = payload_json.get('ref', '').split('/')[-1]
            
            logger.info(f"Code pushed to {repo} on branch {branch}")
            
            # You could add automatic deployment logic here
            
        elif event == 'pull_request':
            # Handle pull request events
            action = payload_json.get('action')
            pr_number = payload_json.get('number')
            
            logger.info(f"Pull request #{pr_number} {action}")
        
        return jsonify({'success': True, 'message': 'Webhook processed'})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("SmartVendo+ Admin Backend")
    print("=" * 60)
    print(f"Raspberry Pi URL: {RASPBERRY_PI_URL}")
    print(f"Admin Panel: http://localhost:8080")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
