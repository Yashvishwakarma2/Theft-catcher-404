"""
Authentication Routes
Handles user login, registration, and token verification for the AI Surveillance Dashboard
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Database helper functions
def get_db_connection():
    """Get a database connection"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(project_root, 'classes.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_users_table():
    """Initialize users table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def token_required(f):
    """Decorator to check if valid JWT token is provided"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


# Routes

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Expected JSON:
    {
        "username": "string",
        "password": "string",
        "email": "string (optional)",
        "full_name": "string (optional)"
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Username and password are required'}), 400
        
        username = data.get('username').strip()
        password = data.get('password').strip()
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        
        # Validate username length
        if len(username) < 3:
            return jsonify({'message': 'Username must be at least 3 characters long'}), 400
        
        # Validate password length
        if len(password) < 6:
            return jsonify({'message': 'Password must be at least 6 characters long'}), 400
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (username, password, email, full_name)
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, email if email else None, full_name if full_name else None))
            conn.commit()
            
            user_id = cursor.lastrowid
            
            return jsonify({
                'message': 'User registered successfully',
                'user_id': user_id,
                'username': username
            }), 201
        
        except sqlite3.IntegrityError:
            return jsonify({'message': 'Username or email already exists'}), 409
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token
    
    Expected JSON:
    {
        "username": "string",
        "password": "string"
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Username and password are required'}), 400
        
        username = data.get('username').strip()
        password = data.get('password').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, username, password, is_active FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'message': 'Invalid username or password'}), 401
            
            if not user['is_active']:
                return jsonify({'message': 'User account is inactive'}), 403
            
            # Check password
            if not check_password_hash(user['password'], password):
                return jsonify({'message': 'Invalid username or password'}), 401
            
            # Update last login
            cursor.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user['id'],)
            )
            conn.commit()
            
            # Generate JWT token
            token = jwt.encode(
                {
                    'user_id': user['id'],
                    'username': user['username'],
                    'exp': datetime.utcnow() + timedelta(hours=24)
                },
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            return jsonify({
                'message': 'Login successful',
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username']
                }
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500


@auth_bp.route('/verify-token', methods=['GET'])
@token_required
def verify_token(current_user):
    """
    Verify if the provided token is valid
    
    Requires: Authorization header with Bearer token
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, username, email, full_name FROM users WHERE id = ?', (current_user,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'message': 'User not found'}), 404
            
            return jsonify({
                'message': 'Token is valid',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name']
                }
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({'message': f'Verification failed: {str(e)}'}), 500


@auth_bp.route('/refresh-token', methods=['POST'])
@token_required
def refresh_token(current_user):
    """
    Generate a new JWT token for valid authenticated user
    
    Requires: Authorization header with Bearer token
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, username FROM users WHERE id = ?', (current_user,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'message': 'User not found'}), 404
            
            # Generate new JWT token
            token = jwt.encode(
                {
                    'user_id': user['id'],
                    'username': user['username'],
                    'exp': datetime.utcnow() + timedelta(hours=24)
                },
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            return jsonify({
                'message': 'Token refreshed successfully',
                'token': token
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({'message': f'Token refresh failed: {str(e)}'}), 500


@auth_bp.route('/user-info', methods=['GET'])
@token_required
def get_user_info(current_user):
    """
    Get current authenticated user's information
    
    Requires: Authorization header with Bearer token
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, full_name, created_at, last_login, is_active
                FROM users WHERE id = ?
            ''', (current_user,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'message': 'User not found'}), 404
            
            return jsonify({
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'created_at': user['created_at'],
                    'last_login': user['last_login'],
                    'is_active': user['is_active']
                }
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve user info: {str(e)}'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """
    Change password for current authenticated user
    
    Expected JSON:
    {
        "old_password": "string",
        "new_password": "string"
    }
    
    Requires: Authorization header with Bearer token
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('old_password') or not data.get('new_password'):
            return jsonify({'message': 'Old password and new password are required'}), 400
        
        old_password = data.get('old_password').strip()
        new_password = data.get('new_password').strip()
        
        # Validate new password length
        if len(new_password) < 6:
            return jsonify({'message': 'New password must be at least 6 characters long'}), 400
        
        # Ensure old and new passwords are different
        if old_password == new_password:
            return jsonify({'message': 'New password must be different from old password'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT password FROM users WHERE id = ?', (current_user,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'message': 'User not found'}), 404
            
            # Verify old password
            if not check_password_hash(user['password'], old_password):
                return jsonify({'message': 'Incorrect old password'}), 401
            
            # Hash new password
            hashed_new_password = generate_password_hash(new_password)
            
            # Update password
            cursor.execute(
                'UPDATE users SET password = ? WHERE id = ?',
                (hashed_new_password, current_user)
            )
            conn.commit()
            
            return jsonify({'message': 'Password changed successfully'}), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({'message': f'Password change failed: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """
    Logout user (token invalidation is handled client-side)
    
    Requires: Authorization header with Bearer token
    """
    return jsonify({'message': 'Logged out successfully'}), 200


# Error handlers
@auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'message': 'Bad request'}), 400


@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'message': 'Unauthorized'}), 401


@auth_bp.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404


@auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500
