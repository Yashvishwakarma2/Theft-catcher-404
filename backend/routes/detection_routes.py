"""
Detection Routes
Handles AI detection processing, alerts, anomalies, and detection event management
"""

from flask import Blueprint, request, jsonify, current_app
import sqlite3
import os
from datetime import datetime, timedelta
import threading
import json
from functools import wraps
from collections import deque
import base64

# Create blueprint
detection_bp = Blueprint('detection', __name__, url_prefix='/api/detection')

# Detection event manager
detection_manager = {
    'events': deque(maxlen=1000),
    'alerts': [],
    'anomalies': [],
    'alert_config': {
        'weapons_enabled': True,
        'suspicious_activity_enabled': True,
        'crowding_enabled': True,
        'loitering_enabled': True
    },
    'lock': threading.Lock()
}

# Target classes configuration
TARGET_CLASSES = {
    'person': ['person'],
    'mask': ['mask'],
    'weapon': ['knife', 'baseball bat', 'gun'],
    'object': ['car', 'bicycle', 'motorcycle', 'truck', 'bus']
}

# Database helper functions
def get_db_connection():
    """Get a database connection"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(project_root, 'classes.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_detection_tables():
    """Initialize detection-related tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Detection events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                detection_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                count INTEGER DEFAULT 1,
                bbox_data TEXT,
                frame_data BLOB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                event_type TEXT
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                detection_class TEXT,
                confidence REAL,
                message TEXT,
                image_path TEXT,
                is_resolved BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        ''')
        
        # Alert configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                alert_type TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                threshold REAL,
                cooldown_minutes INTEGER DEFAULT 5,
                user_id INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Anomaly detection table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                anomaly_type TEXT NOT NULL,
                description TEXT,
                severity TEXT DEFAULT 'low',
                data JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


# Initialize tables on module load
init_detection_tables()


def detect_anomalies(detections, camera_id):
    """Detect anomalies in detection patterns"""
    anomalies = []
    
    # Check for crowding (multiple people)
    people_count = sum(1 for d in detections if d.get('class') == 'person')
    if people_count > 10:
        anomalies.append({
            'type': 'crowding',
            'severity': 'medium',
            'description': f'Crowding detected: {people_count} people',
            'count': people_count
        })
    
    # Check for weapon detection
    weapons = [d for d in detections if d.get('class') in ['knife', 'gun', 'baseball bat']]
    if weapons:
        for weapon in weapons:
            anomalies.append({
                'type': 'weapon_detected',
                'severity': 'critical',
                'description': f'Weapon detected: {weapon.get("class")} (confidence: {weapon.get("confidence", 0):.2f})',
                'weapon': weapon.get('class'),
                'confidence': weapon.get('confidence', 0)
            })
    
    return anomalies


def check_alert_cooldown(alert_type, camera_id):
    """Check if alert is on cooldown"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT cooldown_minutes FROM alert_config 
            WHERE camera_id = ? AND alert_type = ?
        ''', (camera_id, alert_type))
        
        config = cursor.fetchone()
        cooldown = config['cooldown_minutes'] if config else 5
        
        # Check recent alerts
        cursor.execute('''
            SELECT created_at FROM detection_alerts 
            WHERE camera_id = ? AND alert_type = ? AND is_resolved = 0
            ORDER BY created_at DESC LIMIT 1
        ''', (camera_id, alert_type))
        
        last_alert = cursor.fetchone()
        if not last_alert:
            return True
        
        last_time = datetime.fromisoformat(last_alert['created_at'])
        time_since = (datetime.now() - last_time).total_seconds() / 60
        
        return time_since > cooldown
    
    finally:
        conn.close()


# Routes

@detection_bp.route('/process', methods=['POST'])
def process_detection():
    """
    Process detection results from frontend
    
    Expected JSON:
    {
        "camera_id": 0,
        "detections": [
            {
                "class": "person",
                "confidence": 0.95,
                "bbox": {"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.2}
            }
        ],
        "frame": "base64_encoded_image",
        "user_id": 1
    }
    
    Response:
    {
        "success": true,
        "alerts": [...],
        "anomalies": [...],
        "event_id": 1
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'detections' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing detections field'
            }), 400
        
        detections = data.get('detections', [])
        camera_id = data.get('camera_id', 0)
        user_id = data.get('user_id')
        frame_data = data.get('frame')
        
        # Detect anomalies
        anomalies = detect_anomalies(detections, camera_id)
        
        # Create alerts for anomalies
        alerts_created = []
        for anomaly in anomalies:
            if check_alert_cooldown(anomaly['type'], camera_id):
                alert_id = create_alert(
                    camera_id=camera_id,
                    alert_type=anomaly['type'],
                    severity=anomaly['severity'],
                    message=anomaly['description'],
                    user_id=user_id
                )
                alerts_created.append(alert_id)
        
        # Store detection event
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            bbox_json = json.dumps([d.get('bbox', {}) for d in detections])
            
            cursor.execute('''
                INSERT INTO detection_events 
                (camera_id, detection_class, confidence, count, bbox_data, frame_data, user_id, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                camera_id,
                ','.join([d['class'] for d in detections]),
                max([d.get('confidence', 0) for d in detections]) if detections else 0,
                len(detections),
                bbox_json,
                frame_data.encode() if frame_data else None,
                user_id,
                'multi' if len(detections) > 1 else 'single'
            ))
            conn.commit()
            event_id = cursor.lastrowid
        finally:
            conn.close()
        
        with detection_manager['lock']:
            detection_manager['events'].append({
                'id': event_id,
                'camera_id': camera_id,
                'detections': detections,
                'anomalies': anomalies,
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'event_id': event_id,
            'detections_count': len(detections),
            'alerts': alerts_created,
            'anomalies': anomalies,
            'message': 'Detection processed successfully'
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Detection processing failed: {str(e)}'
        }), 500


@detection_bp.route('/validate', methods=['POST'])
def validate_detection():
    """
    Validate detection results
    
    Expected JSON:
    {
        "detections": [...],
        "target_classes": ["person", "car"],
        "min_confidence": 0.5
    }
    
    Response:
    {
        "success": true,
        "valid_detections": [...],
        "filtered_count": 0
    }
    """
    try:
        data = request.get_json()
        detections = data.get('detections', [])
        target_classes = data.get('target_classes', [])
        min_confidence = data.get('min_confidence', 0.5)
        
        if not detections:
            return jsonify({
                'success': True,
                'valid_detections': [],
                'filtered_count': 0
            }), 200
        
        # Filter detections
        valid_detections = []
        filtered_count = 0
        
        for detection in detections:
            # Check confidence threshold
            if detection.get('confidence', 0) < min_confidence:
                filtered_count += 1
                continue
            
            # Check target classes
            if target_classes and detection.get('class') not in target_classes:
                filtered_count += 1
                continue
            
            valid_detections.append(detection)
        
        return jsonify({
            'success': True,
            'valid_detections': valid_detections,
            'filtered_count': filtered_count,
            'total_detections': len(detections)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }), 500


@detection_bp.route('/target-classes/<mode>', methods=['GET'])
def get_target_classes(mode):
    """
    Get target classes for a detection mode
    
    Parameters:
    - mode: 'person', 'weapon', 'object'
    
    Response:
    {
        "success": true,
        "mode": "person",
        "classes": ["person"]
    }
    """
    try:
        classes = TARGET_CLASSES.get(mode, [])
        
        if not classes:
            return jsonify({
                'success': False,
                'error': f'Unknown detection mode: {mode}'
            }), 400
        
        return jsonify({
            'success': True,
            'mode': mode,
            'classes': classes,
            'count': len(classes)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get target classes: {str(e)}'
        }), 500


def create_alert(camera_id, alert_type, severity='medium', detection_class=None, 
                 confidence=None, message=None, image_path=None, user_id=None):
    """Helper function to create an alert"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO detection_alerts 
            (camera_id, alert_type, severity, detection_class, confidence, message, image_path, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (camera_id, alert_type, severity, detection_class, confidence, message, image_path, user_id))
        
        conn.commit()
        alert_id = cursor.lastrowid
        
        with detection_manager['lock']:
            detection_manager['alerts'].append({
                'id': alert_id,
                'type': alert_type,
                'severity': severity
            })
        
        return alert_id
    finally:
        conn.close()


@detection_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Get detection alerts with optional filters
    
    Query Parameters:
    - camera_id: filter by camera
    - alert_type: filter by alert type
    - severity: filter by severity (low, medium, high, critical)
    - is_resolved: filter by resolution status (0 or 1)
    - limit: number of records (default: 50)
    - hours: get alerts from last N hours (default: 24)
    
    Response:
    {
        "success": true,
        "alerts": [...],
        "count": 10
    }
    """
    try:
        camera_id = request.args.get('camera_id', type=int)
        alert_type = request.args.get('alert_type')
        severity = request.args.get('severity')
        is_resolved = request.args.get('is_resolved', type=int)
        limit = request.args.get('limit', default=50, type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = 'SELECT * FROM detection_alerts WHERE created_at > datetime(\'now\', ?)'
        params = [f'-{hours} hours']
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        if alert_type:
            query += ' AND alert_type = ?'
            params.append(alert_type)
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        if is_resolved is not None:
            query += ' AND is_resolved = ?'
            params.append(is_resolved)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        alerts = cursor.fetchall()
        conn.close()
        
        alerts_list = [
            {
                'id': a['id'],
                'camera_id': a['camera_id'],
                'alert_type': a['alert_type'],
                'severity': a['severity'],
                'detection_class': a['detection_class'],
                'confidence': a['confidence'],
                'message': a['message'],
                'image_path': a['image_path'],
                'is_resolved': a['is_resolved'],
                'created_at': a['created_at'],
                'resolved_at': a['resolved_at']
            }
            for a in alerts
        ]
        
        return jsonify({
            'success': True,
            'alerts': alerts_list,
            'count': len(alerts_list)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve alerts: {str(e)}'
        }), 500


@detection_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """
    Mark an alert as resolved
    
    Response:
    {
        "success": true,
        "message": "Alert resolved"
    }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE detection_alerts 
                SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({
                    'success': False,
                    'error': 'Alert not found'
                }), 404
            
            return jsonify({
                'success': True,
                'message': 'Alert resolved successfully'
            }), 200
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to resolve alert: {str(e)}'
        }), 500


@detection_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    """
    Get detected anomalies
    
    Query Parameters:
    - camera_id: filter by camera
    - anomaly_type: filter by type
    - severity: filter by severity
    - limit: number of records (default: 50)
    - hours: get records from last N hours (default: 24)
    
    Response:
    {
        "success": true,
        "anomalies": [...],
        "count": 10
    }
    """
    try:
        camera_id = request.args.get('camera_id', type=int)
        anomaly_type = request.args.get('anomaly_type')
        severity = request.args.get('severity')
        limit = request.args.get('limit', default=50, type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM anomalies WHERE timestamp > datetime(\'now\', ?)'
        params = [f'-{hours} hours']
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        if anomaly_type:
            query += ' AND anomaly_type = ?'
            params.append(anomaly_type)
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        anomalies = cursor.fetchall()
        conn.close()
        
        anomalies_list = [
            {
                'id': a['id'],
                'camera_id': a['camera_id'],
                'anomaly_type': a['anomaly_type'],
                'description': a['description'],
                'severity': a['severity'],
                'data': json.loads(a['data']) if a['data'] else None,
                'timestamp': a['timestamp']
            }
            for a in anomalies
        ]
        
        return jsonify({
            'success': True,
            'anomalies': anomalies_list,
            'count': len(anomalies_list)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve anomalies: {str(e)}'
        }), 500


@detection_bp.route('/statistics', methods=['GET'])
def get_detection_statistics():
    """
    Get detection statistics
    
    Query Parameters:
    - camera_id: filter by camera
    - hours: time period in hours (default: 24)
    
    Response:
    {
        "success": true,
        "stats": {
            "total_events": 100,
            "unique_classes": 5,
            "alert_count": 10,
            "critical_alerts": 2,
            "most_detected_class": "person",
            "avg_confidence": 0.85,
            "detection_classes": {...},
            "alert_types": {...}
        }
    }
    """
    try:
        camera_id = request.args.get('camera_id', type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get detection events
        query = 'SELECT * FROM detection_events WHERE timestamp > datetime(\'now\', ?)'
        params = [f'-{hours} hours']
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        
        # Get alerts
        alert_query = 'SELECT severity FROM detection_alerts WHERE created_at > datetime(\'now\', ?)'
        alert_params = [f'-{hours} hours']
        if camera_id is not None:
            alert_query += ' AND camera_id = ?'
            alert_params.append(camera_id)
        
        cursor.execute(alert_query, alert_params)
        alerts = cursor.fetchall()
        
        conn.close()
        
        # Calculate statistics
        classes_count = {}
        confidences = []
        
        for event in events:
            classes = event['detection_class'].split(',')
            conf = event['confidence']
            
            for cls in classes:
                classes_count[cls] = classes_count.get(cls, 0) + 1
            
            if conf > 0:
                confidences.append(conf)
        
        # Count alert severities
        alert_severities = {}
        for alert in alerts:
            severity = alert['severity']
            alert_severities[severity] = alert_severities.get(severity, 0) + 1
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        most_detected = max(classes_count.items(), key=lambda x: x[1])[0] if classes_count else None
        
        return jsonify({
            'success': True,
            'stats': {
                'total_events': len(events),
                'unique_classes': len(classes_count),
                'alert_count': len(alerts),
                'critical_alerts': alert_severities.get('critical', 0),
                'high_alerts': alert_severities.get('high', 0),
                'most_detected_class': most_detected,
                'avg_confidence': round(avg_confidence, 3),
                'detection_classes': classes_count,
                'alert_severities': alert_severities,
                'time_period_hours': hours
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve statistics: {str(e)}'
        }), 500


@detection_bp.route('/events', methods=['GET'])
def get_detection_events():
    """
    Get detection events
    
    Query Parameters:
    - camera_id: filter by camera
    - event_type: 'single' or 'multi'
    - limit: number of records (default: 50)
    - hours: get events from last N hours (default: 24)
    
    Response:
    {
        "success": true,
        "events": [...],
        "count": 10
    }
    """
    try:
        camera_id = request.args.get('camera_id', type=int)
        event_type = request.args.get('event_type')
        limit = request.args.get('limit', default=50, type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM detection_events WHERE timestamp > datetime(\'now\', ?)'
        params = [f'-{hours} hours']
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        conn.close()
        
        events_list = [
            {
                'id': e['id'],
                'camera_id': e['camera_id'],
                'detection_class': e['detection_class'],
                'confidence': e['confidence'],
                'count': e['count'],
                'bbox_data': json.loads(e['bbox_data']) if e['bbox_data'] else None,
                'event_type': e['event_type'],
                'timestamp': e['timestamp']
            }
            for e in events
        ]
        
        return jsonify({
            'success': True,
            'events': events_list,
            'count': len(events_list)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve events: {str(e)}'
        }), 500


@detection_bp.route('/alert-config/<int:camera_id>', methods=['GET', 'POST'])
def manage_alert_config(camera_id):
    """
    Get or update alert configuration for a camera
    
    GET Response:
    {
        "success": true,
        "config": [...]
    }
    
    POST Expected JSON:
    {
        "alert_type": "weapon_detected",
        "enabled": true,
        "threshold": 0.8,
        "cooldown_minutes": 5
    }
    """
    try:
        if request.method == 'GET':
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT * FROM alert_config WHERE camera_id = ?
                ''', (camera_id,))
                
                configs = cursor.fetchall()
                
                config_list = [
                    {
                        'id': c['id'],
                        'alert_type': c['alert_type'],
                        'enabled': c['enabled'],
                        'threshold': c['threshold'],
                        'cooldown_minutes': c['cooldown_minutes']
                    }
                    for c in configs
                ]
                
                return jsonify({
                    'success': True,
                    'config': config_list
                }), 200
            finally:
                conn.close()
        
        elif request.method == 'POST':
            data = request.get_json()
            alert_type = data.get('alert_type')
            enabled = data.get('enabled', True)
            threshold = data.get('threshold')
            cooldown = data.get('cooldown_minutes', 5)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Check if config exists
                cursor.execute('''
                    SELECT id FROM alert_config WHERE camera_id = ? AND alert_type = ?
                ''', (camera_id, alert_type))
                
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute('''
                        UPDATE alert_config 
                        SET enabled = ?, threshold = ?, cooldown_minutes = ?
                        WHERE camera_id = ? AND alert_type = ?
                    ''', (enabled, threshold, cooldown, camera_id, alert_type))
                else:
                    cursor.execute('''
                        INSERT INTO alert_config 
                        (camera_id, alert_type, enabled, threshold, cooldown_minutes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (camera_id, alert_type, enabled, threshold, cooldown))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Alert configuration updated'
                }), 200
            finally:
                conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to manage alert config: {str(e)}'
        }), 500


@detection_bp.route('/health', methods=['GET'])
def detection_health():
    """
    Get detection system health status
    
    Response:
    {
        "success": true,
        "status": "healthy",
        "recent_events": 10,
        "recent_alerts": 2,
        "average_confidence": 0.85
    }
    """
    try:
        with detection_manager['lock']:
            recent_events = len(detection_manager['events'])
            recent_alerts = len(detection_manager['alerts'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT AVG(confidence) as avg_conf FROM detection_events 
                WHERE timestamp > datetime('now', '-1 hour')
            ''')
            result = cursor.fetchone()
            avg_confidence = result['avg_conf'] if result['avg_conf'] else 0
        finally:
            conn.close()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'recent_events': recent_events,
            'recent_alerts': recent_alerts,
            'average_confidence': round(avg_confidence, 3) if avg_confidence else 0
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Health check failed: {str(e)}'
        }), 500


# Error handlers
@detection_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'success': False, 'error': 'Bad request'}), 400


@detection_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404


@detection_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
