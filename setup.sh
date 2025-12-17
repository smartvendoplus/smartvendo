#!/bin/bash
# SmartVendo+ Raspberry Pi Setup Script

echo "========================================="
echo "   SmartVendo+ Installation Script"
echo "========================================="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
echo "Installing Python and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install required system packages
echo "Installing system dependencies..."
sudo apt-get install -y sqlite3
sudo apt-get install -y git

# Create project directory
echo "Setting up project directory..."
mkdir -p ~/SmartVendo
cd ~/SmartVendo

# Clone repository (if using git)
# git clone <your-repo-url> .

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python database/init_db.py

# Set up systemd service
echo "Setting up system service..."
sudo tee /etc/systemd/system/smartvendo.service > /dev/null <<EOF
[Unit]
Description=SmartVendo+ Flask Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/SmartVendo
Environment="PATH=/home/pi/SmartVendo/venv/bin"
ExecStart=/home/pi/SmartVendo/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable smartvendo.service
sudo systemctl start smartvendo.service

# Set up autostart for kiosk mode (7" display)
echo "Setting up kiosk mode..."
sudo apt-get install -y chromium-browser unclutter

# Create kiosk startup script
sudo tee /home/pi/kiosk.sh > /dev/null <<EOF
#!/bin/bash
# Clean up in case of crash
rm -rf /home/pi/.cache/chromium
rm -rf /home/pi/.config/chromium

# Hide cursor
unclutter -idle 0.5 -root &

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Launch Chromium in kiosk mode
chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:5000
EOF

sudo chmod +x /home/pi/kiosk.sh

# Add to autostart
sudo tee /etc/xdg/lxsession/LXDE-pi/autostart > /dev/null <<EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@xset s off
@xset -dpms
@xset s noblank
@/home/pi/kiosk.sh
EOF

# Set permissions
sudo chown -R pi:pi ~/SmartVendo

echo "========================================="
echo "   Installation Complete!"
echo "========================================="
echo ""
echo "SmartVendo+ will start automatically on boot."
echo ""
echo "Access points:"
echo "- User Interface (7\" display): Auto-starts in kiosk mode"
echo "- Admin Interface: http://localhost:5000/admin"
echo "  Username: admin.smartvendo@gmail.com"
echo "  Password: Admin@2025"
echo ""
echo "To check service status: sudo systemctl status smartvendo"
echo "To view logs: sudo journalctl -u smartvendo -f"
echo ""
echo "Reboot your Raspberry Pi to start the system."