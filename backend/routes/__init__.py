"""
Routes package for API endpoints
"""

from .auth_routes import auth_bp
from .camera_routes import camera_bp
from .detection_routes import detection_bp
from .alert_routes import alert_bp
from .ai_routes import ai_bp

__all__ = ['auth_bp', 'camera_bp', 'detection_bp', 'alert_bp', 'ai_bp']
