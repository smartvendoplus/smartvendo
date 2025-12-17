import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smartvendo-secret-key-2025'
    
    # Database Configuration
    DATABASE_PATH = 'database/smartvendo.db'
    
    # Admin Credentials
    ADMIN_EMAIL = 'admin.smartvendo@gmail.com'
    ADMIN_PASSWORD = 'Admin@2025'  # Change in production!
    
    # RFID Configuration
    RFID_PORT = '/dev/ttyUSB0'  # Change based on your RFID reader
    RFID_BAUDRATE = 9600
    
    # Points Configuration
    POINTS_PER_PAPER = 5
    POINTS_PER_PLASTIC = 10
    
    # Reward Configuration
    DEFAULT_REWARDS = {
        'pencil': {'cost': 100, 'stock': 50, 'image': 'pencil.png'},
        'eraser': {'cost': 150, 'stock': 30, 'image': 'eraser.png'},
        'ballpen': {'cost': 100, 'stock': 40, 'image': 'ballpen.png'},
        'marker': {'cost': 200, 'stock': 20, 'image': 'marker.png'}
    }
    
    # File Upload
    UPLOAD_FOLDER = 'static/images'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Logging
    LOG_FILE = 'smartvendo.log'
    
    @staticmethod
    def init_app(app):
        # Create necessary directories
        os.makedirs('database', exist_ok=True)
        os.makedirs('static/images', exist_ok=True)
        os.makedirs('logs', exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # In production, use environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}