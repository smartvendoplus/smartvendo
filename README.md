# SmartVendo+ System

A smart vending machine system for recycling with RFID authentication, point-based rewards, and admin dashboard.

## Features

### User Side
- RFID card authentication
- Deposit paper/plastic for points
- Redeem points for school supplies
- Account management with 2-month validity
- Auto-logout for security

### Admin Side
- System monitoring dashboard
- Bin status monitoring
- Shredder control
- Maintenance management
- Real-time statistics

## File Structure

SMARTVENDO+/
├── app.py                    # Main Flask server (Raspberry Pi)
├── rfid_reader.py           # RFID reader script
├── database/
│   ├── init_db.py          # Initialize database
│   └── smartvendo.db       # SQLite database
├── templates/              # HTML templates
│   ├── user/
│   │   ├── index.html
│   │   ├── welcome.html
│   │   ├── id-login.html
│   │   ├── signup.html
│   │   ├── signup-rfid.html
│   │   ├── signup-complete.html
│   │   └── dashboard.html
│   └── admin/
│       ├── admin-welcome.html
│       └── admin-dashboard.html
├── static/
│   ├── css/
│   │   └── global.css
│   ├── js/
│   │   └── global.js
│   ├── images/
│   │   ├── logo1.png
│   │   ├── paper.png
│   │   ├── plastic.png
│   │   ├── pencil.png
│   │   ├── eraser.png
│   │   ├── ballpen.png
│   │   └── marker.png
│   └── uploads/            # Admin-uploaded images
├── config.py              # Configuration file
├── requirements.txt       # Python dependencies
└── README.md