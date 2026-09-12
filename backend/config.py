"""
Configuration file for AI Surveillance Dashboard
Contains all application settings, database config, and model parameters
"""

import os
from datetime import timedelta

# Get the project root directory (parent of this file's directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Flask Configuration
class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False

    # Flask app configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    # Database configuration
    DATABASE_PATH = os.path.join(PROJECT_ROOT, 'classes.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload configuration
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # API configuration
    API_PREFIX = '/api'
    API_VERSION = 'v1'

    # CORS settings (if needed for frontend integration)
    CORS_ORIGINS = ['http://localhost:5000', 'http://127.0.0.1:5000']

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries

    # Development server settings
    HOST = '0.0.0.0'
    PORT = 5000

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False

    # Production security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-production-secret-key'
    # Note: In production, you should set SECRET_KEY environment variable

    # Production database (consider using PostgreSQL or MySQL)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL

    # Production server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8000))

class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database for tests
    WTF_CSRF_ENABLED = False

# AI Model Configuration
class AIModelConfig:
    """Configuration for AI models used in the application"""

    # TensorFlow.js COCO-SSD Model
    COCO_SSD_MODEL_URL = 'https://tfhub.dev/tensorflow/tfjs-model/ssd_mobilenet_v2/1/default/1'

    # Tiny Face Detector Model
    FACE_DETECTOR_MODEL_PATH = os.path.join(PROJECT_ROOT, 'models')
    FACE_DETECTOR_INPUT_SIZE = 512
    FACE_DETECTOR_SCORE_THRESHOLD = 0.5

    # Detection parameters
    DEFAULT_CONFIDENCE_THRESHOLD = 0.5
    DETECTION_INTERVAL_MS = 120  # milliseconds between detections
    MAX_DETECTIONS = 10

    # Detection classes configuration
    DETECTION_MODES = {
        'person': ['person'],
        'weapon': ['knife', 'baseball bat'],
        'object': [
            'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird',
            'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe',
            'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis',
            'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
    }

# Security Configuration
class SecurityConfig:
    """Security-related configuration"""

    # Authentication settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL_CHARS = False

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_REQUESTS_PER_HOUR = 1000

    # File upload security
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}
    MAX_FILENAME_LENGTH = 255

# Logging Configuration
class LoggingConfig:
    """Logging configuration for the application"""

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.path.join(PROJECT_ROOT, 'logs', 'app.log')

    # Create logs directory if it doesn't exist
    LOG_DIR = os.path.dirname(LOG_FILE)
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)

# Application Configuration
class AppConfig:
    """Main application configuration"""

    APP_NAME = 'AI Surveillance Dashboard'
    VERSION = '1.0.0'
    DESCRIPTION = 'Real-time theft detection and surveillance system'

    # Supported languages/locales
    SUPPORTED_LANGUAGES = ['en', 'es', 'fr']

    # Time zone settings
    TIMEZONE = 'UTC'

    # Email configuration (for alerts/notifications)
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    EMAIL_FROM = os.environ.get('EMAIL_FROM', 'noreply@surveillance-system.com')

# Environment-based configuration selection
def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')

    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }

    return config_map.get(env, DevelopmentConfig)

# Global configuration instances
config = get_config()
ai_config = AIModelConfig()
security_config = SecurityConfig()
logging_config = LoggingConfig()
app_config = AppConfig()

# Export configurations
__all__ = [
    'config',
    'ai_config',
    'security_config',
    'logging_config',
    'app_config',
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig'
]