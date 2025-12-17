#!/usr/bin/env python3
"""
RFID Reader Script for SmartVendo+
Reads RFID cards directly connected to Raspberry Pi via USB
"""

import serial
import time
import requests
import json
from datetime import datetime

class RFIDReader:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.api_url = 'http://localhost:5000/api/rfid/read'
        
    def connect(self):
        """Connect to RFID reader"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Connected to RFID reader on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to RFID reader: {e}")
            return False
    
    def read_rfid(self):
        """Read RFID UID from serial port"""
        if not self.ser or not self.ser.is_open:
            print("RFID reader not connected")
            return None
        
        try:
            # Read data from serial port
            data = self.ser.readline().decode('utf-8').strip()
            
            if data:
                # Parse RFID UID (format may vary by reader)
                # Common formats: "4F:31:10:E8" or "4F3110E8"
                uid = self.parse_uid(data)
                if uid:
                    print(f"[{datetime.now()}] RFID Detected: {uid}")
                    return uid
        except Exception as e:
            print(f"Error reading RFID: {e}")
        
        return None
    
    def parse_uid(self, data):
        """Parse RFID UID from reader output"""
        # Remove any non-hex characters and format
        clean_data = ''.join(c for c in data if c.isalnum())
        
        if len(clean_data) >= 8:
            # Format as hex pairs: "4F3110E8" -> "4F:31:10:E8"
            uid_parts = [clean_data[i:i+2] for i in range(0, len(clean_data), 2)]
            return ':'.join(uid_parts[:4])  # Typically 4 bytes for UID
        
        return None
    
    def send_to_server(self, uid):
        """Send RFID UID to Flask server"""
        try:
            payload = {'uid': uid}
            response = requests.post(self.api_url, json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Server response: {result}")
                return result
            else:
                print(f"Server error: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"Failed to send to server: {e}")
            return None
    
    def run(self):
        """Main loop to read and process RFID tags"""
        if not self.connect():
            return
        
        print("RFID Reader started. Waiting for cards...")
        
        last_uid = None
        last_read_time = 0
        
        try:
            while True:
                uid = self.read_rfid()
                
                if uid and uid != last_uid:
                    current_time = time.time()
                    
                    # Prevent rapid repeated reads of same card
                    if current_time - last_read_time > 2:
                        print(f"Processing RFID: {uid}")
                        result = self.send_to_server(uid)
                        
                        if result and result.get('success'):
                            if result.get('action') == 'login':
                                print(f"User logged in: {result.get('user', {}).get('rfid_uid')}")
                            elif result.get('action') == 'register':
                                print(f"New RFID for registration: {uid}")
                        
                        last_uid = uid
                        last_read_time = current_time
                
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
        except KeyboardInterrupt:
            print("\nRFID Reader stopped by user")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("RFID reader disconnected")

# Alternative: Simulated RFID reader for testing without hardware
class SimulatedRFIDReader(RFIDReader):
    def __init__(self):
        super().__init__()
        self.test_uids = [
            "4F:31:10:E8",
            "AB:CD:12:34",
            "DE:AD:BE:EF",
            "CA:FE:BA:BE"
        ]
        self.current_index = 0
    
    def connect(self):
        print("Using simulated RFID reader (for testing)")
        return True
    
    def read_rfid(self):
        # Simulate reading by cycling through test UIDs
        # In real use, press Enter to simulate card tap
        input("\nPress Enter to simulate RFID card tap...")
        
        uid = self.test_uids[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.test_uids)
        
        print(f"[SIMULATED] RFID Detected: {uid}")
        return uid

if __name__ == '__main__':
    # Use real RFID reader if available, otherwise use simulation
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--simulate':
        reader = SimulatedRFIDReader()
    else:
        reader = RFIDReader()
    
    reader.run()