"""
Authentication middleware for the Flask backend.
Provides JWT token verification and user authentication utilities.
"""

import jwt
from flask import request, g, current_app, jsonify
from functools import wraps
from typing import Optional, Dict, Any


def token_required(f):
    """
    Decorator to require JWT token authentication for protected routes.

    Usage:
    @app.route('/protected')
    @token_required
    def protected_route():
        user_id = g.user_id
        # ... route logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            payload = decode_jwt_token(token)
            g.user_id = payload['user_id']
            g.username = payload.get('username')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication error: {str(e)}'}), 401

        return f(*args, **kwargs)

    return decorated_function


def get_token_from_request() -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Supports 'Bearer <token>' format.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None

    try:
        # Expected format: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            return parts[1]
    except:
        pass

    return None


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token.

    Returns payload if valid, raises exception if invalid.
    """
    secret_key = current_app.config.get('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY not configured")

    return jwt.decode(token, secret_key, algorithms=["HS256"])


def get_current_user_id() -> Optional[int]:
    """
    Get the current authenticated user ID from the request context.

    Returns None if no user is authenticated.
    """
    return getattr(g, 'user_id', None)


def get_current_username() -> Optional[str]:
    """
    Get the current authenticated username from the request context.

    Returns None if no user is authenticated.
    """
    return getattr(g, 'username', None)


def optional_token_required(f):
    """
    Decorator that optionally requires JWT token.
    If token is present and valid, sets user context.
    If not present or invalid, continues without authentication.

    Usage:
    @app.route('/public')
    @optional_token_required
    def public_route():
        user_id = get_current_user_id()  # May be None
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()

        if token:
            try:
                payload = decode_jwt_token(token)
                g.user_id = payload['user_id']
                g.username = payload.get('username')
            except:
                # Invalid token, but don't fail - just don't set user context
                pass

        return f(*args, **kwargs)

    return decorated_function


def require_admin(f):
    """
    Decorator to require admin privileges.
    Currently checks if user_id is 1 (admin user).
    Can be extended with role-based permissions.

    Usage:
    @app.route('/admin')
    @token_required
    @require_admin
    def admin_route():
        # Only admin users can access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()

        # Simple admin check - user_id == 1 is admin
        # TODO: Implement proper role-based permissions
        if user_id != 1:
            return jsonify({'error': 'Admin privileges required'}), 403

        return f(*args, **kwargs)

    return decorated_function
