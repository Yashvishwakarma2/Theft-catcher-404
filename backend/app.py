from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_cors import CORS
import os
import sys
import sqlite3
from datetime import datetime
import json

# Add backend directory to path to import config and backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import config, ai_config, app_config
from routes import auth_bp, camera_bp, detection_bp, alert_bp, ai_bp
from routes.auth_routes import init_users_table
from routes.camera_routes import init_detection_history_table
from routes.detection_routes import init_detection_tables
from routes.alert_routes import init_alert_tables
from middleware.error_handler import register_error_handlers
from utils.logger import setup_logging
from database.db import ensure_database, execute_script, get_database_path
from models.user_model import UserModel
from models.detection_model import DetectionModel
from models.alert_model import AlertModel

# Get the project root directory and frontend directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

app = Flask(__name__,
            template_folder=FRONTEND_DIR,
            static_folder=FRONTEND_DIR,
            static_url_path='')

# Apply configuration
app.config.from_object(config)

# Enable CORS (Cross-Origin Resource Sharing) for API requests
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Setup logging and error handling
setup_logging(log_level=config.DEBUG and 'DEBUG' or 'INFO')
register_error_handlers(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(camera_bp)
app.register_blueprint(detection_bp)
app.register_blueprint(alert_bp)
app.register_blueprint(ai_bp)

# Initialize tables for authentication, camera, detection, alerts, and AI storage
init_users_table()
init_detection_history_table()
init_detection_tables()
init_alert_tables()
UserModel.initialize_table()
DetectionModel.initialize_tables()
AlertModel.initialize_tables()

# Database connection helper
def get_db_connection():
    db_path = os.path.join(PROJECT_ROOT, 'classes.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database if it doesn't exist
def init_db():
    db_path = ensure_database()
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
    if os.path.exists(schema_path):
        try:
            with open(schema_path, 'r', encoding='utf-8') as schema_file:
                execute_script(schema_file.read())
        except Exception:
            pass
    return db_path

@app.route('/')
def index():
    """Redirect the root URL to the login page"""
    return redirect(url_for('login'))

@app.route('/index.html')
def index_html():
    return render_template('index.html')

@app.route('/object')
def object_detection():
    """Serve the object detection page"""
    return render_template('object.html')

@app.route('/object.html')
def object_html():
    return render_template('object.html')

@app.route('/weapon')
def weapon_detection():
    """Serve the weapon detection page"""
    return render_template('weapon.html')

@app.route('/weapon.html')
def weapon_html():
    return render_template('weapon.html')

@app.route('/mask')
def mask_detection():
    """Serve the mask detection page"""
    return render_template('mask.html')

@app.route('/mask.html')
def mask_html():
    return render_template('mask.html')

@app.route('/login')
def login():
    """Serve the login page"""
    return render_template('login.html')

@app.route('/login.html')
def login_html():
    return render_template('login.html')

@app.route('/api/target-classes/<mode>')
def get_target_classes(mode):
    """API endpoint to get target classes for a specific detection mode"""
    try:
        conn = get_db_connection()
        classes = conn.execute('SELECT class_name FROM target_classes WHERE mode = ?',
                              (mode,)).fetchall()
        conn.close()

        class_list = [row['class_name'] for row in classes]
        return jsonify({'success': True, 'classes': class_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/detection-history', methods=['GET', 'POST'])
def detection_history():
    """API endpoint to get or store detection history"""
    if request.method == 'GET':
        # Return recent detection history (in a real app, this would be stored in DB)
        # For now, return mock data
        mock_history = [
            {'class': 'person', 'confidence': 0.92, 'timestamp': '11:05:00 AM'},
            {'class': 'person', 'confidence': 0.88, 'timestamp': '11:05:12 AM'},
            {'class': 'knife', 'confidence': 0.75, 'timestamp': '11:06:00 AM'}
        ]
        return jsonify({'success': True, 'history': mock_history})

    elif request.method == 'POST':
        # Store detection data
        try:
            data = request.get_json()
            # In a real implementation, you'd store this in a database
            # For now, just log it
            print(f"Detection recorded: {data}")

            # You could add a detections table to store this
            # conn = get_db_connection()
            # conn.execute('INSERT INTO detections (class_name, confidence, timestamp) VALUES (?, ?, ?)',
            #             (data['class'], data['confidence'], datetime.now().isoformat()))
            # conn.commit()
            # conn.close()

            return jsonify({'success': True, 'message': 'Detection recorded'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/modals')
def get_modals():
    """API endpoint to get modal HTML (alternative to client-side modals)"""
    try:
        from modals import get_modals_html
        return get_modals_html()
    except ImportError:
        return "Modal module not available", 500

@app.route('/api/system-status')
def system_status():
    """API endpoint to get system status"""
    return jsonify({
        'success': True,
        'status': 'active',
        'timestamp': datetime.now().isoformat(),
        'version': app_config.VERSION,
        'name': app_config.APP_NAME
    })

@app.route('/models/<path:filename>')
def serve_models(filename):
    """Serve model files"""
    return send_from_directory('models', filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend directory"""
    return send_from_directory(FRONTEND_DIR, filename)

@app.errorhandler(404)
def page_not_found(e):
    """Redirect unknown URLs to the login page"""
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Initialize database on startup
    init_db()

    # Run the Flask app
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )