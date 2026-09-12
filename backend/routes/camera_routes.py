"""
Camera Routes
Handles camera initialization, streaming, recording, and detection history for the AI Surveillance Dashboard
"""

from flask import Blueprint, request, jsonify, current_app, Response

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

import os
import sqlite3
from datetime import datetime, timedelta
import threading
import json
from functools import wraps

CAMERA_ERROR_MESSAGE = 'OpenCV is not installed. Camera routes are unavailable.'

def require_cv2(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if cv2 is None:
            return jsonify({
                'success': False,
                'error': CAMERA_ERROR_MESSAGE
            }), 503
        return f(*args, **kwargs)
    return wrapper

# Create blueprint
camera_bp = Blueprint('camera', __name__, url_prefix='/api/camera')

# Global variables for camera management
camera_manager = {
    'cameras': {},
    'active_camera': None,
    'recording': False,
    'recording_writer': None,
    'lock': threading.Lock()
}

# Database helper functions
def get_db_connection():
    """Get a database connection"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(project_root, 'classes.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_detection_history_table():
    """Initialize detection history table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                detection_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                x INTEGER,
                y INTEGER,
                width INTEGER,
                height INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT,
                user_id INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS camera_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                user_id INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                recording_file TEXT,
                detections_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


# Initialize tables on module load
init_detection_history_table()


def scan_available_cameras():
    """Scan for available cameras on the system"""
    available_cameras = []
    if cv2 is None:
        return available_cameras
    # Try to find up to 10 cameras
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                camera_info = {
                    'id': i,
                    'name': f'Camera {i}',
                    'available': True,
                    'resolution': {
                        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    },
                    'fps': int(cap.get(cv2.CAP_PROP_FPS))
                }
                available_cameras.append(camera_info)
            cap.release()
    return available_cameras


def get_frame_from_camera(camera_id):
    """Get a single frame from the specified camera"""
    if cv2 is None:
        return None
    if camera_id not in camera_manager['cameras']:
        return None
    
    camera = camera_manager['cameras'][camera_id]
    ret, frame = camera.read()
    if ret:
        return frame
    return None


# Routes

@camera_bp.route('/list', methods=['GET'])
@require_cv2
def list_cameras():
    """
    Get list of available cameras
    
    Response:
    {
        "success": true,
        "cameras": [
            {
                "id": 0,
                "name": "Camera 0",
                "available": true,
                "resolution": {"width": 640, "height": 480},
                "fps": 30
            }
        ]
    }
    """
    try:
        available_cameras = scan_available_cameras()
        
        return jsonify({
            'success': True,
            'cameras': available_cameras,
            'count': len(available_cameras)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to scan cameras: {str(e)}'
        }), 500


@camera_bp.route('/initialize/<int:camera_id>', methods=['POST'])
@require_cv2
def initialize_camera(camera_id):
    """
    Initialize a camera for use
    
    Expected JSON:
    {
        "width": 640,
        "height": 480,
        "fps": 30
    }
    
    Response:
    {
        "success": true,
        "camera_id": 0,
        "message": "Camera initialized successfully"
    }
    """
    try:
        data = request.get_json() or {}
        width = data.get('width', 640)
        height = data.get('height', 480)
        fps = data.get('fps', 30)
        
        with camera_manager['lock']:
            # Release existing camera if open
            if camera_id in camera_manager['cameras']:
                camera_manager['cameras'][camera_id].release()
            
            # Initialize new camera
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                return jsonify({
                    'success': False,
                    'error': f'Failed to open camera {camera_id}'
                }), 400
            
            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            
            camera_manager['cameras'][camera_id] = cap
            camera_manager['active_camera'] = camera_id
        
        return jsonify({
            'success': True,
            'camera_id': camera_id,
            'message': 'Camera initialized successfully',
            'settings': {
                'width': width,
                'height': height,
                'fps': fps
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Camera initialization failed: {str(e)}'
        }), 500


@camera_bp.route('/release/<int:camera_id>', methods=['POST'])
def release_camera(camera_id):
    """
    Release a camera resource
    
    Response:
    {
        "success": true,
        "message": "Camera released successfully"
    }
    """
    try:
        with camera_manager['lock']:
            if camera_id in camera_manager['cameras']:
                camera_manager['cameras'][camera_id].release()
                del camera_manager['cameras'][camera_id]
                
                if camera_manager['active_camera'] == camera_id:
                    camera_manager['active_camera'] = None
        
        return jsonify({
            'success': True,
            'message': 'Camera released successfully'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to release camera: {str(e)}'
        }), 500


@camera_bp.route('/frame/<int:camera_id>', methods=['GET'])
@require_cv2
def get_frame(camera_id):
    """
    Get current frame from specified camera as JPEG
    
    Response: JPEG image data
    """
    try:
        if camera_id not in camera_manager['cameras']:
            return jsonify({
                'success': False,
                'error': f'Camera {camera_id} not initialized'
            }), 400
        
        frame = get_frame_from_camera(camera_id)
        
        if frame is None:
            return jsonify({
                'success': False,
                'error': 'Failed to capture frame'
            }), 400
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return jsonify({
                'success': False,
                'error': 'Failed to encode frame'
            }), 500
        
        return Response(
            buffer.tobytes(),
            mimetype='image/jpeg'
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get frame: {str(e)}'
        }), 500


@camera_bp.route('/stream/<int:camera_id>', methods=['GET'])
@require_cv2
def stream_camera(camera_id):
    """
    Get continuous video stream from specified camera (Motion JPEG)
    
    Response: Motion JPEG stream with frames
    """
    def generate():
        try:
            if camera_id not in camera_manager['cameras']:
                yield b''
                return
            
            while True:
                frame = get_frame_from_camera(camera_id)
                if frame is None:
                    break
                
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                
                # Yield frame in MJPEG format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(buffer)).encode() + b'\r\n\r\n' 
                       + buffer.tobytes() + b'\r\n')
        
        except Exception as e:
            print(f"Stream error: {str(e)}")
    
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@camera_bp.route('/save-detection', methods=['POST'])
def save_detection():
    """
    Save detection record to database
    
    Expected JSON:
    {
        "camera_id": 0,
        "class": "person",
        "confidence": 0.95,
        "bbox": {"x": 100, "y": 150, "width": 50, "height": 100},
        "image_path": "path/to/saved/image.jpg",
        "user_id": 1
    }
    
    Response:
    {
        "success": true,
        "detection_id": 1
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('class'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            bbox = data.get('bbox', {})
            cursor.execute('''
                INSERT INTO detection_history 
                (camera_id, detection_class, confidence, x, y, width, height, image_path, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('camera_id', 0),
                data.get('class'),
                data.get('confidence', 0.0),
                bbox.get('x'),
                bbox.get('y'),
                bbox.get('width'),
                bbox.get('height'),
                data.get('image_path'),
                data.get('user_id')
            ))
            conn.commit()
            
            detection_id = cursor.lastrowid
            
            return jsonify({
                'success': True,
                'detection_id': detection_id,
                'message': 'Detection saved successfully'
            }), 201
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to save detection: {str(e)}'
        }), 500


@camera_bp.route('/history', methods=['GET'])
def get_detection_history():
    """
    Get detection history with optional filters
    
    Query Parameters:
    - limit: number of records (default: 100)
    - camera_id: filter by camera (optional)
    - class: filter by detection class (optional)
    - hours: get records from last N hours (default: 24)
    
    Response:
    {
        "success": true,
        "detections": [
            {
                "id": 1,
                "camera_id": 0,
                "class": "person",
                "confidence": 0.95,
                "timestamp": "2024-01-20 14:30:00"
            }
        ],
        "count": 10
    }
    """
    try:
        limit = request.args.get('limit', default=100, type=int)
        camera_id = request.args.get('camera_id', type=int)
        detection_class = request.args.get('class')
        hours = request.args.get('hours', default=24, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = 'SELECT * FROM detection_history WHERE timestamp > datetime(\'now\', ?)'
        params = [f'-{hours} hours']
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        if detection_class:
            query += ' AND detection_class = ?'
            params.append(detection_class)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        detections = cursor.fetchall()
        
        conn.close()
        
        detection_list = [
            {
                'id': d['id'],
                'camera_id': d['camera_id'],
                'class': d['detection_class'],
                'confidence': d['confidence'],
                'bbox': {
                    'x': d['x'],
                    'y': d['y'],
                    'width': d['width'],
                    'height': d['height']
                } if d['x'] is not None else None,
                'timestamp': d['timestamp'],
                'image_path': d['image_path']
            }
            for d in detections
        ]
        
        return jsonify({
            'success': True,
            'detections': detection_list,
            'count': len(detection_list)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve history: {str(e)}'
        }), 500


@camera_bp.route('/history/stats', methods=['GET'])
def get_history_stats():
    """
    Get detection statistics
    
    Query Parameters:
    - hours: time period in hours (default: 24)
    - camera_id: filter by camera (optional)
    
    Response:
    {
        "success": true,
        "stats": {
            "total_detections": 42,
            "unique_classes": 5,
            "classes": {"person": 25, "car": 12, ...},
            "avg_confidence": 0.87,
            "time_period_hours": 24
        }
    }
    """
    try:
        hours = request.args.get('hours', default=24, type=int)
        camera_id = request.args.get('camera_id', type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = 'SELECT * FROM detection_history WHERE timestamp > datetime(\'now\', ?)'
        params = [f'-{hours} hours']
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        cursor.execute(query, params)
        detections = cursor.fetchall()
        
        conn.close()
        
        # Calculate stats
        total = len(detections)
        classes_count = {}
        confidences = []
        
        for d in detections:
            cls = d['detection_class']
            classes_count[cls] = classes_count.get(cls, 0) + 1
            confidences.append(d['confidence'])
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_detections': total,
                'unique_classes': len(classes_count),
                'classes': classes_count,
                'avg_confidence': round(avg_confidence, 3),
                'time_period_hours': hours
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve stats: {str(e)}'
        }), 500


@camera_bp.route('/status', methods=['GET'])
def camera_status():
    """
    Get current camera status
    
    Response:
    {
        "success": true,
        "active_camera": 0,
        "cameras_initialized": [0, 1],
        "recording": false,
        "status": "running"
    }
    """
    try:
        with camera_manager['lock']:
            cameras_init = list(camera_manager['cameras'].keys())
            active = camera_manager['active_camera']
            recording = camera_manager['recording']
        
        return jsonify({
            'success': True,
            'active_camera': active,
            'cameras_initialized': cameras_init,
            'recording': recording,
            'status': 'running'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get status: {str(e)}'
        }), 500


@camera_bp.route('/settings/<int:camera_id>', methods=['GET', 'POST'])
@require_cv2
def camera_settings(camera_id):
    """
    Get or update camera settings
    
    GET Response:
    {
        "success": true,
        "settings": {
            "width": 640,
            "height": 480,
            "fps": 30,
            "brightness": 0,
            "contrast": 0,
            "saturation": 64
        }
    }
    
    POST Expected JSON:
    {
        "brightness": 0,
        "contrast": 0,
        "saturation": 64,
        "fps": 30
    }
    """
    try:
        if camera_id not in camera_manager['cameras']:
            return jsonify({
                'success': False,
                'error': f'Camera {camera_id} not initialized'
            }), 400
        
        cap = camera_manager['cameras'][camera_id]
        
        if request.method == 'GET':
            settings = {
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': int(cap.get(cv2.CAP_PROP_FPS)),
                'brightness': int(cap.get(cv2.CAP_PROP_BRIGHTNESS)),
                'contrast': int(cap.get(cv2.CAP_PROP_CONTRAST)),
                'saturation': int(cap.get(cv2.CAP_PROP_SATURATION))
            }
            
            return jsonify({
                'success': True,
                'settings': settings
            }), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Apply settings
            if 'brightness' in data:
                cap.set(cv2.CAP_PROP_BRIGHTNESS, data['brightness'])
            if 'contrast' in data:
                cap.set(cv2.CAP_PROP_CONTRAST, data['contrast'])
            if 'saturation' in data:
                cap.set(cv2.CAP_PROP_SATURATION, data['saturation'])
            if 'fps' in data:
                cap.set(cv2.CAP_PROP_FPS, data['fps'])
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully'
            }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to manage settings: {str(e)}'
        }), 500


@camera_bp.route('/record/start', methods=['POST'])
@require_cv2
def start_recording():
    """
    Start recording video from active camera
    
    Expected JSON:
    {
        "camera_id": 0,
        "filename": "recording.mp4"
    }
    
    Response:
    {
        "success": true,
        "message": "Recording started"
    }
    """
    try:
        data = request.get_json()
        camera_id = data.get('camera_id', camera_manager['active_camera'])
        filename = data.get('filename', f'recording_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4')
        
        if camera_id is None or camera_id not in camera_manager['cameras']:
            return jsonify({
                'success': False,
                'error': 'No active camera'
            }), 400
        
        with camera_manager['lock']:
            if camera_manager['recording']:
                return jsonify({
                    'success': False,
                    'error': 'Already recording'
                }), 400
            
            cap = camera_manager['cameras'][camera_id]
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'recordings')
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, filename)
            
            # Define codec and create VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            camera_manager['recording'] = True
            camera_manager['recording_writer'] = out
        
        return jsonify({
            'success': True,
            'message': 'Recording started',
            'filename': filename,
            'path': output_path
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start recording: {str(e)}'
        }), 500


@camera_bp.route('/record/stop', methods=['POST'])
@require_cv2
def stop_recording():
    """
    Stop recording video
    
    Response:
    {
        "success": true,
        "message": "Recording stopped"
    }
    """
    try:
        with camera_manager['lock']:
            if not camera_manager['recording']:
                return jsonify({
                    'success': False,
                    'error': 'Not currently recording'
                }), 400
            
            camera_manager['recording_writer'].release()
            camera_manager['recording'] = False
            camera_manager['recording_writer'] = None
        
        return jsonify({
            'success': True,
            'message': 'Recording stopped'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to stop recording: {str(e)}'
        }), 500


# Error handlers
@camera_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'success': False, 'error': 'Bad request'}), 400


@camera_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404


@camera_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
