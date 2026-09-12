"""
Alert Routes
Handles alert management, notifications, escalation, scheduling, and reporting
"""

from flask import Blueprint, request, jsonify, current_app
import sqlite3
import os
from datetime import datetime, timedelta
import threading
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from collections import deque
import re

# Create blueprint
alert_bp = Blueprint('alert', __name__, url_prefix='/api/alert')

# Alert manager
alert_manager = {
    'queue': deque(maxlen=5000),
    'active_alerts': {},
    'acknowledged': set(),
    'escalations': [],
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


def init_alert_tables():
    """Initialize alert-related tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Alert notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                recipient TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alert escalation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_escalation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                escalation_level INTEGER DEFAULT 1,
                escalated_to TEXT,
                escalation_reason TEXT,
                escalated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        
        # Alert acknowledgment table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_acknowledgment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                acknowledged_by INTEGER,
                acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_status TEXT DEFAULT 'acknowledged',
                notes TEXT
            )
        ''')
        
        # Alert rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition TEXT NOT NULL,
                action TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                priority INTEGER DEFAULT 5,
                notification_enabled BOOLEAN DEFAULT 1,
                escalation_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        ''')
        
        # Alert templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                alert_type TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alert suppression table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_suppression (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                reason TEXT,
                suppressed_from TIMESTAMP,
                suppressed_until TIMESTAMP,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alert recipients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                webhook_url TEXT,
                notification_types TEXT,
                priority_level TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


# Initialize tables on module load
init_alert_tables()


def is_alert_suppressed(alert_type):
    """Check if alert type is currently suppressed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM alert_suppression 
            WHERE alert_type = ? 
            AND suppressed_from <= ? 
            AND suppressed_until >= ?
        ''', (alert_type, datetime.now(), datetime.now()))
        
        return cursor.fetchone() is not None
    finally:
        conn.close()


def send_email_notification(recipient_email, subject, message, alert_data):
    """Send email notification"""
    try:
        # In production, use actual email service
        # For now, log the notification
        print(f"Email notification would be sent to {recipient_email}")
        print(f"Subject: {subject}")
        print(f"Message: {message}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def send_webhook_notification(webhook_url, alert_data):
    """Send webhook notification"""
    try:
        import requests
        payload = {
            'alert_id': alert_data.get('id'),
            'alert_type': alert_data.get('type'),
            'severity': alert_data.get('severity'),
            'message': alert_data.get('message'),
            'timestamp': alert_data.get('timestamp'),
            'data': alert_data
        }
        # In production, actually make the HTTP request
        print(f"Webhook notification would be sent to {webhook_url}")
        return True
    except Exception as e:
        print(f"Failed to send webhook: {str(e)}")
        return False


# Routes

@alert_bp.route('/create', methods=['POST'])
def create_alert():
    """
    Create a new alert
    
    Expected JSON:
    {
        "type": "weapon_detected",
        "severity": "critical",
        "message": "Weapon detected in zone A",
        "camera_id": 0,
        "data": {...}
    }
    
    Response:
    {
        "success": true,
        "alert_id": 1,
        "notifications_sent": 3
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('type'):
            return jsonify({
                'success': False,
                'error': 'Alert type is required'
            }), 400
        
        alert_type = data.get('type')
        severity = data.get('severity', 'medium')
        message = data.get('message', '')
        camera_id = data.get('camera_id')
        alert_data = data.get('data', {})
        
        # Check if alert is suppressed
        if is_alert_suppressed(alert_type):
            return jsonify({
                'success': True,
                'alert_id': None,
                'message': 'Alert suppressed',
                'suppressed': True
            }), 200
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get alert template if exists
            cursor.execute('''
                SELECT subject, message as template_msg FROM alert_templates 
                WHERE alert_type = ? AND enabled = 1
            ''', (alert_type,))
            
            template = cursor.fetchone()
            final_message = message or (template['template_msg'] if template else '')
            
            # Create alert record
            cursor.execute('''
                INSERT INTO detection_alerts 
                (camera_id, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            ''', (camera_id, alert_type, severity, final_message))
            
            conn.commit()
            alert_id = cursor.lastrowid
            
            # Get recipients for this severity level
            cursor.execute('''
                SELECT * FROM alert_recipients 
                WHERE is_active = 1
                AND (priority_level IS NULL OR priority_level <= ?)
                AND notification_types LIKE ?
            ''', (severity, f'%{alert_type}%'))
            
            recipients = cursor.fetchall()
            notifications_sent = 0
            
            # Send notifications
            for recipient in recipients:
                if recipient['email']:
                    if send_email_notification(
                        recipient['email'],
                        template['subject'] if template else f"Alert: {alert_type}",
                        final_message,
                        alert_data
                    ):
                        notifications_sent += 1
                
                if recipient['webhook_url']:
                    if send_webhook_notification(recipient['webhook_url'], {
                        'id': alert_id,
                        'type': alert_type,
                        'severity': severity,
                        'message': final_message,
                        'timestamp': datetime.now().isoformat(),
                        **alert_data
                    }):
                        notifications_sent += 1
            
            # Store in manager
            with alert_manager['lock']:
                alert_manager['queue'].append({
                    'id': alert_id,
                    'type': alert_type,
                    'severity': severity,
                    'timestamp': datetime.now().isoformat()
                })
                alert_manager['active_alerts'][alert_id] = {
                    'type': alert_type,
                    'severity': severity,
                    'created_at': datetime.now()
                }
            
            return jsonify({
                'success': True,
                'alert_id': alert_id,
                'notifications_sent': notifications_sent,
                'message': 'Alert created successfully'
            }), 201
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create alert: {str(e)}'
        }), 500


@alert_bp.route('/acknowledge/<int:alert_id>', methods=['POST'])
def acknowledge_alert(alert_id):
    """
    Acknowledge an alert
    
    Expected JSON:
    {
        "user_id": 1,
        "notes": "Acknowledged and investigating"
    }
    
    Response:
    {
        "success": true,
        "message": "Alert acknowledged"
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        notes = data.get('notes', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO alert_acknowledgment (alert_id, acknowledged_by, notes)
                VALUES (?, ?, ?)
            ''', (alert_id, user_id, notes))
            
            conn.commit()
            
            with alert_manager['lock']:
                alert_manager['acknowledged'].add(alert_id)
            
            return jsonify({
                'success': True,
                'message': 'Alert acknowledged successfully'
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to acknowledge alert: {str(e)}'
        }), 500


@alert_bp.route('/escalate/<int:alert_id>', methods=['POST'])
def escalate_alert(alert_id):
    """
    Escalate an alert
    
    Expected JSON:
    {
        "escalation_level": 2,
        "escalated_to": "supervisor@company.com",
        "reason": "Alert requires immediate attention"
    }
    
    Response:
    {
        "success": true,
        "message": "Alert escalated"
    }
    """
    try:
        data = request.get_json()
        escalation_level = data.get('escalation_level', 1)
        escalated_to = data.get('escalated_to')
        reason = data.get('reason', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO alert_escalation 
                (alert_id, escalation_level, escalated_to, escalation_reason)
                VALUES (?, ?, ?, ?)
            ''', (alert_id, escalation_level, escalated_to, reason))
            
            conn.commit()
            escalation_id = cursor.lastrowid
            
            # Send escalation notification
            if escalated_to:
                send_email_notification(
                    escalated_to,
                    f"Alert Escalation - Level {escalation_level}",
                    f"Alert {alert_id} has been escalated.\nReason: {reason}",
                    {'alert_id': alert_id}
                )
            
            with alert_manager['lock']:
                alert_manager['escalations'].append({
                    'alert_id': alert_id,
                    'escalation_id': escalation_id,
                    'level': escalation_level,
                    'timestamp': datetime.now().isoformat()
                })
            
            return jsonify({
                'success': True,
                'escalation_id': escalation_id,
                'message': 'Alert escalated successfully'
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to escalate alert: {str(e)}'
        }), 500


@alert_bp.route('/close/<int:alert_id>', methods=['POST'])
def close_alert(alert_id):
    """
    Close an alert
    
    Expected JSON:
    {
        "resolution": "false_alarm",
        "notes": "No actual threat detected"
    }
    
    Response:
    {
        "success": true,
        "message": "Alert closed"
    }
    """
    try:
        data = request.get_json() or {}
        resolution = data.get('resolution', 'resolved')
        notes = data.get('notes', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE detection_alerts 
                SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            
            conn.commit()
            
            with alert_manager['lock']:
                if alert_id in alert_manager['active_alerts']:
                    del alert_manager['active_alerts'][alert_id]
            
            return jsonify({
                'success': True,
                'message': 'Alert closed successfully',
                'resolution': resolution
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to close alert: {str(e)}'
        }), 500


@alert_bp.route('/list', methods=['GET'])
def list_alerts():
    """
    Get alerts with filtering
    
    Query Parameters:
    - status: 'open', 'acknowledged', 'closed'
    - severity: 'low', 'medium', 'high', 'critical'
    - alert_type: filter by type
    - limit: number of records (default: 100)
    - offset: pagination offset (default: 0)
    - sort_by: 'severity', 'created_at', 'updated_at' (default: 'created_at')
    - sort_order: 'asc', 'desc' (default: 'desc')
    
    Response:
    {
        "success": true,
        "alerts": [...],
        "total": 10,
        "limit": 100,
        "offset": 0
    }
    """
    try:
        status = request.args.get('status')
        severity = request.args.get('severity')
        alert_type = request.args.get('alert_type')
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        sort_by = request.args.get('sort_by', default='created_at')
        sort_order = request.args.get('sort_order', default='desc').upper()
        
        # Validate sort parameters
        if sort_by not in ['severity', 'created_at', 'updated_at']:
            sort_by = 'created_at'
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'DESC'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Build query
            query = 'SELECT * FROM detection_alerts WHERE 1=1'
            params = []
            
            if status == 'open':
                query += ' AND is_resolved = 0'
            elif status == 'closed':
                query += ' AND is_resolved = 1'
            
            if severity:
                query += ' AND severity = ?'
                params.append(severity)
            
            if alert_type:
                query += ' AND alert_type = ?'
                params.append(alert_type)
            
            # Get total count
            count_query = f'SELECT COUNT(*) as count FROM ({query})'
            cursor.execute(count_query, params)
            total = cursor.fetchone()['count']
            
            # Get paginated results
            query += f' ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            alerts = cursor.fetchall()
            
            alerts_list = [
                {
                    'id': a['id'],
                    'camera_id': a['camera_id'],
                    'alert_type': a['alert_type'],
                    'severity': a['severity'],
                    'message': a['message'],
                    'is_resolved': a['is_resolved'],
                    'created_at': a['created_at'],
                    'resolved_at': a['resolved_at']
                }
                for a in alerts
            ]
            
            return jsonify({
                'success': True,
                'alerts': alerts_list,
                'total': total,
                'limit': limit,
                'offset': offset
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve alerts: {str(e)}'
        }), 500


@alert_bp.route('/detail/<int:alert_id>', methods=['GET'])
def get_alert_detail(alert_id):
    """
    Get detailed information about an alert
    
    Response:
    {
        "success": true,
        "alert": {...},
        "acknowledgments": [...],
        "escalations": [...],
        "notifications": [...]
    }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get alert
            cursor.execute('SELECT * FROM detection_alerts WHERE id = ?', (alert_id,))
            alert = cursor.fetchone()
            
            if not alert:
                return jsonify({
                    'success': False,
                    'error': 'Alert not found'
                }), 404
            
            # Get acknowledgments
            cursor.execute('''
                SELECT * FROM alert_acknowledgment WHERE alert_id = ?
                ORDER BY acknowledged_at DESC
            ''', (alert_id,))
            acknowledgments = cursor.fetchall()
            
            # Get escalations
            cursor.execute('''
                SELECT * FROM alert_escalation WHERE alert_id = ?
                ORDER BY escalated_at DESC
            ''', (alert_id,))
            escalations = cursor.fetchall()
            
            # Get notifications
            cursor.execute('''
                SELECT * FROM alert_notifications WHERE alert_id = ?
                ORDER BY created_at DESC
            ''', (alert_id,))
            notifications = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'alert': {
                    'id': alert['id'],
                    'camera_id': alert['camera_id'],
                    'alert_type': alert['alert_type'],
                    'severity': alert['severity'],
                    'message': alert['message'],
                    'is_resolved': alert['is_resolved'],
                    'created_at': alert['created_at'],
                    'resolved_at': alert['resolved_at']
                },
                'acknowledgments': [
                    {
                        'id': a['id'],
                        'acknowledged_by': a['acknowledged_by'],
                        'acknowledged_at': a['acknowledged_at'],
                        'notes': a['notes']
                    }
                    for a in acknowledgments
                ],
                'escalations': [
                    {
                        'id': e['id'],
                        'escalation_level': e['escalation_level'],
                        'escalated_to': e['escalated_to'],
                        'escalation_reason': e['escalation_reason'],
                        'escalated_at': e['escalated_at']
                    }
                    for e in escalations
                ],
                'notifications': [
                    {
                        'id': n['id'],
                        'notification_type': n['notification_type'],
                        'recipient': n['recipient'],
                        'status': n['status'],
                        'sent_at': n['sent_at']
                    }
                    for n in notifications
                ]
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve alert detail: {str(e)}'
        }), 500


@alert_bp.route('/recipient', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_recipients():
    """
    Manage alert recipients
    
    GET: List all recipients
    POST: Create new recipient
    PUT: Update recipient (requires recipient_id in JSON)
    DELETE: Delete recipient (requires recipient_id in query param)
    """
    try:
        if request.method == 'GET':
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT * FROM alert_recipients WHERE is_active = 1')
                recipients = cursor.fetchall()
                
                recipients_list = [
                    {
                        'id': r['id'],
                        'name': r['name'],
                        'email': r['email'],
                        'phone': r['phone'],
                        'webhook_url': r['webhook_url'],
                        'notification_types': r['notification_types'],
                        'priority_level': r['priority_level']
                    }
                    for r in recipients
                ]
                
                return jsonify({
                    'success': True,
                    'recipients': recipients_list,
                    'count': len(recipients_list)
                }), 200
            
            finally:
                conn.close()
        
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data or not data.get('name'):
                return jsonify({
                    'success': False,
                    'error': 'Recipient name is required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO alert_recipients 
                    (name, email, phone, webhook_url, notification_types, priority_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('name'),
                    data.get('email'),
                    data.get('phone'),
                    data.get('webhook_url'),
                    data.get('notification_types', 'all'),
                    data.get('priority_level')
                ))
                
                conn.commit()
                recipient_id = cursor.lastrowid
                
                return jsonify({
                    'success': True,
                    'recipient_id': recipient_id,
                    'message': 'Recipient created successfully'
                }), 201
            
            finally:
                conn.close()
        
        elif request.method == 'PUT':
            data = request.get_json()
            recipient_id = data.get('recipient_id')
            
            if not recipient_id:
                return jsonify({
                    'success': False,
                    'error': 'Recipient ID is required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                updates = []
                params = []
                
                if 'name' in data:
                    updates.append('name = ?')
                    params.append(data['name'])
                if 'email' in data:
                    updates.append('email = ?')
                    params.append(data['email'])
                if 'phone' in data:
                    updates.append('phone = ?')
                    params.append(data['phone'])
                if 'webhook_url' in data:
                    updates.append('webhook_url = ?')
                    params.append(data['webhook_url'])
                if 'notification_types' in data:
                    updates.append('notification_types = ?')
                    params.append(data['notification_types'])
                if 'priority_level' in data:
                    updates.append('priority_level = ?')
                    params.append(data['priority_level'])
                
                if not updates:
                    return jsonify({
                        'success': False,
                        'error': 'No fields to update'
                    }), 400
                
                query = f"UPDATE alert_recipients SET {', '.join(updates)} WHERE id = ?"
                params.append(recipient_id)
                
                cursor.execute(query, params)
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Recipient updated successfully'
                }), 200
            
            finally:
                conn.close()
        
        elif request.method == 'DELETE':
            recipient_id = request.args.get('recipient_id', type=int)
            
            if not recipient_id:
                return jsonify({
                    'success': False,
                    'error': 'Recipient ID is required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    UPDATE alert_recipients SET is_active = 0 WHERE id = ?
                ''', (recipient_id,))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Recipient deleted successfully'
                }), 200
            
            finally:
                conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Recipient management failed: {str(e)}'
        }), 500


@alert_bp.route('/template', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_templates():
    """
    Manage alert templates
    
    GET: List all templates
    POST: Create new template
    PUT: Update template (requires template_id in JSON)
    DELETE: Delete template (requires template_id in query param)
    """
    try:
        if request.method == 'GET':
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT * FROM alert_templates WHERE enabled = 1')
                templates = cursor.fetchall()
                
                templates_list = [
                    {
                        'id': t['id'],
                        'name': t['name'],
                        'alert_type': t['alert_type'],
                        'subject': t['subject'],
                        'message': t['message'],
                        'severity': t['severity']
                    }
                    for t in templates
                ]
                
                return jsonify({
                    'success': True,
                    'templates': templates_list,
                    'count': len(templates_list)
                }), 200
            
            finally:
                conn.close()
        
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data or not data.get('name') or not data.get('message'):
                return jsonify({
                    'success': False,
                    'error': 'Name and message are required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO alert_templates 
                    (name, alert_type, subject, message, severity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    data.get('name'),
                    data.get('alert_type', 'general'),
                    data.get('subject'),
                    data.get('message'),
                    data.get('severity', 'medium')
                ))
                
                conn.commit()
                template_id = cursor.lastrowid
                
                return jsonify({
                    'success': True,
                    'template_id': template_id,
                    'message': 'Template created successfully'
                }), 201
            
            finally:
                conn.close()
        
        elif request.method == 'PUT':
            data = request.get_json()
            template_id = data.get('template_id')
            
            if not template_id:
                return jsonify({
                    'success': False,
                    'error': 'Template ID is required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                updates = []
                params = []
                
                if 'subject' in data:
                    updates.append('subject = ?')
                    params.append(data['subject'])
                if 'message' in data:
                    updates.append('message = ?')
                    params.append(data['message'])
                if 'severity' in data:
                    updates.append('severity = ?')
                    params.append(data['severity'])
                
                if not updates:
                    return jsonify({
                        'success': False,
                        'error': 'No fields to update'
                    }), 400
                
                query = f"UPDATE alert_templates SET {', '.join(updates)} WHERE id = ?"
                params.append(template_id)
                
                cursor.execute(query, params)
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Template updated successfully'
                }), 200
            
            finally:
                conn.close()
        
        elif request.method == 'DELETE':
            template_id = request.args.get('template_id', type=int)
            
            if not template_id:
                return jsonify({
                    'success': False,
                    'error': 'Template ID is required'
                }), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    UPDATE alert_templates SET enabled = 0 WHERE id = ?
                ''', (template_id,))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Template deleted successfully'
                }), 200
            
            finally:
                conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Template management failed: {str(e)}'
        }), 500


@alert_bp.route('/suppress', methods=['POST'])
def suppress_alerts():
    """
    Suppress alerts of a specific type
    
    Expected JSON:
    {
        "alert_type": "weapon_detected",
        "duration_minutes": 60,
        "reason": "Maintenance window"
    }
    
    Response:
    {
        "success": true,
        "suppression_id": 1
    }
    """
    try:
        data = request.get_json()
        alert_type = data.get('alert_type')
        duration_minutes = data.get('duration_minutes', 60)
        reason = data.get('reason', '')
        user_id = data.get('user_id')
        
        if not alert_type:
            return jsonify({
                'success': False,
                'error': 'Alert type is required'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now()
            suppressed_until = now + timedelta(minutes=duration_minutes)
            
            cursor.execute('''
                INSERT INTO alert_suppression 
                (alert_type, reason, suppressed_from, suppressed_until, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (alert_type, reason, now, suppressed_until, user_id))
            
            conn.commit()
            suppression_id = cursor.lastrowid
            
            return jsonify({
                'success': True,
                'suppression_id': suppression_id,
                'suppressed_until': suppressed_until.isoformat(),
                'message': f'Alerts for {alert_type} suppressed for {duration_minutes} minutes'
            }), 201
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to suppress alerts: {str(e)}'
        }), 500


@alert_bp.route('/statistics', methods=['GET'])
def get_alert_statistics():
    """
    Get alert statistics
    
    Query Parameters:
    - hours: time period in hours (default: 24)
    
    Response:
    {
        "success": true,
        "stats": {
            "total_alerts": 100,
            "open_alerts": 15,
            "closed_alerts": 85,
            "acknowledged_alerts": 40,
            "by_severity": {...},
            "by_type": {...}
        }
    }
    """
    try:
        hours = request.args.get('hours', default=24, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Total alerts
            cursor.execute('''
                SELECT COUNT(*) as total FROM detection_alerts 
                WHERE created_at > datetime('now', ?)
            ''', (f'-{hours} hours',))
            total = cursor.fetchone()['total']
            
            # Open alerts
            cursor.execute('''
                SELECT COUNT(*) as open FROM detection_alerts 
                WHERE is_resolved = 0 
                AND created_at > datetime('now', ?)
            ''', (f'-{hours} hours',))
            open_alerts = cursor.fetchone()['open']
            
            # Closed alerts
            cursor.execute('''
                SELECT COUNT(*) as closed FROM detection_alerts 
                WHERE is_resolved = 1 
                AND created_at > datetime('now', ?)
            ''', (f'-{hours} hours',))
            closed_alerts = cursor.fetchone()['closed']
            
            # Acknowledged
            cursor.execute('''
                SELECT COUNT(DISTINCT alert_id) as acknowledged 
                FROM alert_acknowledgment 
                WHERE acknowledged_at > datetime('now', ?)
            ''', (f'-{hours} hours',))
            acknowledged = cursor.fetchone()['acknowledged']
            
            # By severity
            cursor.execute('''
                SELECT severity, COUNT(*) as count FROM detection_alerts 
                WHERE created_at > datetime('now', ?)
                GROUP BY severity
            ''', (f'-{hours} hours',))
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # By type
            cursor.execute('''
                SELECT alert_type, COUNT(*) as count FROM detection_alerts 
                WHERE created_at > datetime('now', ?)
                GROUP BY alert_type
            ''', (f'-{hours} hours',))
            by_type = {row['alert_type']: row['count'] for row in cursor.fetchall()}
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_alerts': total,
                    'open_alerts': open_alerts,
                    'closed_alerts': closed_alerts,
                    'acknowledged_alerts': acknowledged,
                    'by_severity': by_severity,
                    'by_type': by_type,
                    'time_period_hours': hours
                }
            }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve statistics: {str(e)}'
        }), 500


@alert_bp.route('/queue/status', methods=['GET'])
def get_queue_status():
    """
    Get current alert queue status
    
    Response:
    {
        "success": true,
        "queue": {
            "total_in_queue": 50,
            "active_alerts": 15,
            "acknowledged_count": 40,
            "pending_escalations": 3
        }
    }
    """
    try:
        with alert_manager['lock']:
            return jsonify({
                'success': True,
                'queue': {
                    'total_in_queue': len(alert_manager['queue']),
                    'active_alerts': len(alert_manager['active_alerts']),
                    'acknowledged_count': len(alert_manager['acknowledged']),
                    'pending_escalations': len(alert_manager['escalations'])
                }
            }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get queue status: {str(e)}'
        }), 500


# Error handlers
@alert_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'success': False, 'error': 'Bad request'}), 400


@alert_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404


@alert_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
