"""
Alert model and database helpers for alert lifecycle, notifications, escalation, suppression, templates, and recipients.
"""

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Project root is the backend directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(PROJECT_ROOT, 'classes.db')


def get_db_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection to the project database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class AlertRecord:
    id: int
    camera_id: Optional[int]
    alert_type: str
    severity: str
    detection_class: Optional[str]
    confidence: Optional[float]
    message: Optional[str]
    image_path: Optional[str]
    is_resolved: int
    resolved_at: Optional[str]
    created_at: str
    user_id: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'detection_class': self.detection_class,
            'confidence': self.confidence,
            'message': self.message,
            'image_path': self.image_path,
            'is_resolved': bool(self.is_resolved),
            'resolved_at': self.resolved_at,
            'created_at': self.created_at,
            'user_id': self.user_id
        }


@dataclass
class AlertNotificationRecord:
    id: int
    alert_id: int
    notification_type: str
    recipient: str
    status: str
    sent_at: Optional[str]
    error_message: Optional[str]
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'notification_type': self.notification_type,
            'recipient': self.recipient,
            'status': self.status,
            'sent_at': self.sent_at,
            'error_message': self.error_message,
            'created_at': self.created_at
        }


@dataclass
class AlertEscalationRecord:
    id: int
    alert_id: int
    escalation_level: int
    escalated_to: Optional[str]
    escalation_reason: Optional[str]
    escalated_at: str
    resolved_at: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'escalation_level': self.escalation_level,
            'escalated_to': self.escalated_to,
            'escalation_reason': self.escalation_reason,
            'escalated_at': self.escalated_at,
            'resolved_at': self.resolved_at
        }


@dataclass
class AlertAcknowledgmentRecord:
    id: int
    alert_id: int
    acknowledged_by: Optional[int]
    acknowledged_at: str
    acknowledged_status: str
    notes: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at,
            'acknowledged_status': self.acknowledged_status,
            'notes': self.notes
        }


@dataclass
class AlertRuleRecord:
    id: int
    name: str
    condition: str
    action: str
    enabled: int
    priority: int
    notification_enabled: int
    escalation_enabled: int
    created_at: str
    user_id: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'condition': self.condition,
            'action': self.action,
            'enabled': bool(self.enabled),
            'priority': self.priority,
            'notification_enabled': bool(self.notification_enabled),
            'escalation_enabled': bool(self.escalation_enabled),
            'created_at': self.created_at,
            'user_id': self.user_id
        }


@dataclass
class AlertTemplateRecord:
    id: int
    name: str
    alert_type: str
    subject: Optional[str]
    message: str
    severity: str
    enabled: int
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'alert_type': self.alert_type,
            'subject': self.subject,
            'message': self.message,
            'severity': self.severity,
            'enabled': bool(self.enabled),
            'created_at': self.created_at
        }


@dataclass
class AlertSuppressionRecord:
    id: int
    alert_type: str
    reason: Optional[str]
    suppressed_from: str
    suppressed_until: str
    user_id: Optional[int]
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'reason': self.reason,
            'suppressed_from': self.suppressed_from,
            'suppressed_until': self.suppressed_until,
            'user_id': self.user_id,
            'created_at': self.created_at
        }


@dataclass
class AlertRecipientRecord:
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    webhook_url: Optional[str]
    notification_types: Optional[str]
    priority_level: Optional[str]
    is_active: int
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'webhook_url': self.webhook_url,
            'notification_types': self.notification_types,
            'priority_level': self.priority_level,
            'is_active': bool(self.is_active),
            'created_at': self.created_at
        }


class AlertModel:
    """Helper class for alert database operations."""

    NOTIFICATIONS_TABLE = 'alert_notifications'
    ESCALATION_TABLE = 'alert_escalation'
    ACKNOWLEDGMENT_TABLE = 'alert_acknowledgment'
    RULES_TABLE = 'alert_rules'
    TEMPLATES_TABLE = 'alert_templates'
    SUPPRESSION_TABLE = 'alert_suppression'
    RECIPIENTS_TABLE = 'alert_recipients'
    ALERTS_TABLE = 'detection_alerts'

    @classmethod
    def initialize_tables(cls) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.NOTIFICATIONS_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.ESCALATION_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER NOT NULL,
                    escalation_level INTEGER DEFAULT 1,
                    escalated_to TEXT,
                    escalation_reason TEXT,
                    escalated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                )
            ''')

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.ACKNOWLEDGMENT_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER NOT NULL,
                    acknowledged_by INTEGER,
                    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_status TEXT DEFAULT 'acknowledged',
                    notes TEXT
                )
            ''')

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.RULES_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.TEMPLATES_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.SUPPRESSION_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    reason TEXT,
                    suppressed_from TIMESTAMP,
                    suppressed_until TIMESTAMP,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.RECIPIENTS_TABLE} (
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
        finally:
            conn.close()

    @classmethod
    def _row_to_alert(cls, row: sqlite3.Row) -> Optional[AlertRecord]:
        if row is None:
            return None
        return AlertRecord(
            id=row['id'],
            camera_id=row['camera_id'],
            alert_type=row['alert_type'],
            severity=row['severity'],
            detection_class=row['detection_class'],
            confidence=row['confidence'],
            message=row['message'],
            image_path=row['image_path'],
            is_resolved=row['is_resolved'],
            resolved_at=row['resolved_at'],
            created_at=row['created_at'],
            user_id=row['user_id']
        )

    @classmethod
    def _row_to_notification(cls, row: sqlite3.Row) -> Optional[AlertNotificationRecord]:
        if row is None:
            return None
        return AlertNotificationRecord(
            id=row['id'],
            alert_id=row['alert_id'],
            notification_type=row['notification_type'],
            recipient=row['recipient'],
            status=row['status'],
            sent_at=row['sent_at'],
            error_message=row['error_message'],
            created_at=row['created_at']
        )

    @classmethod
    def _row_to_escalation(cls, row: sqlite3.Row) -> Optional[AlertEscalationRecord]:
        if row is None:
            return None
        return AlertEscalationRecord(
            id=row['id'],
            alert_id=row['alert_id'],
            escalation_level=row['escalation_level'],
            escalated_to=row['escalated_to'],
            escalation_reason=row['escalation_reason'],
            escalated_at=row['escalated_at'],
            resolved_at=row['resolved_at']
        )

    @classmethod
    def _row_to_acknowledgment(cls, row: sqlite3.Row) -> Optional[AlertAcknowledgmentRecord]:
        if row is None:
            return None
        return AlertAcknowledgmentRecord(
            id=row['id'],
            alert_id=row['alert_id'],
            acknowledged_by=row['acknowledged_by'],
            acknowledged_at=row['acknowledged_at'],
            acknowledged_status=row['acknowledged_status'],
            notes=row['notes']
        )

    @classmethod
    def _row_to_rule(cls, row: sqlite3.Row) -> Optional[AlertRuleRecord]:
        if row is None:
            return None
        return AlertRuleRecord(
            id=row['id'],
            name=row['name'],
            condition=row['condition'],
            action=row['action'],
            enabled=row['enabled'],
            priority=row['priority'],
            notification_enabled=row['notification_enabled'],
            escalation_enabled=row['escalation_enabled'],
            created_at=row['created_at'],
            user_id=row['user_id']
        )

    @classmethod
    def _row_to_template(cls, row: sqlite3.Row) -> Optional[AlertTemplateRecord]:
        if row is None:
            return None
        return AlertTemplateRecord(
            id=row['id'],
            name=row['name'],
            alert_type=row['alert_type'],
            subject=row['subject'],
            message=row['message'],
            severity=row['severity'],
            enabled=row['enabled'],
            created_at=row['created_at']
        )

    @classmethod
    def _row_to_suppression(cls, row: sqlite3.Row) -> Optional[AlertSuppressionRecord]:
        if row is None:
            return None
        return AlertSuppressionRecord(
            id=row['id'],
            alert_type=row['alert_type'],
            reason=row['reason'],
            suppressed_from=row['suppressed_from'],
            suppressed_until=row['suppressed_until'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )

    @classmethod
    def _row_to_recipient(cls, row: sqlite3.Row) -> Optional[AlertRecipientRecord]:
        if row is None:
            return None
        return AlertRecipientRecord(
            id=row['id'],
            name=row['name'],
            email=row['email'],
            phone=row['phone'],
            webhook_url=row['webhook_url'],
            notification_types=row['notification_types'],
            priority_level=row['priority_level'],
            is_active=row['is_active'],
            created_at=row['created_at']
        )

    @classmethod
    def get_alert_by_id(cls, alert_id: int) -> Optional[AlertRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.ALERTS_TABLE} WHERE id = ?', (alert_id,))
            return cls._row_to_alert(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def list_alerts(cls,
                    status: Optional[str] = None,
                    severity: Optional[str] = None,
                    alert_type: Optional[str] = None,
                    limit: int = 100,
                    offset: int = 0,
                    sort_by: str = 'created_at',
                    sort_order: str = 'DESC') -> List[AlertRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'SELECT * FROM {cls.ALERTS_TABLE} WHERE 1=1'
            params: List[Any] = []

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

            if sort_by not in ['severity', 'created_at', 'updated_at']:
                sort_by = 'created_at'
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'

            query += f' ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_alert(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def get_alert_detail(cls, alert_id: int) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.ALERTS_TABLE} WHERE id = ?', (alert_id,))
            alert = cursor.fetchone()
            if not alert:
                return {}

            cursor.execute('SELECT * FROM alert_acknowledgment WHERE alert_id = ? ORDER BY acknowledged_at DESC', (alert_id,))
            acknowledgments = [cls._row_to_acknowledgment(row).as_dict() for row in cursor.fetchall() if row is not None]

            cursor.execute('SELECT * FROM alert_escalation WHERE alert_id = ? ORDER BY escalated_at DESC', (alert_id,))
            escalations = [cls._row_to_escalation(row).as_dict() for row in cursor.fetchall() if row is not None]

            cursor.execute('SELECT * FROM alert_notifications WHERE alert_id = ? ORDER BY created_at DESC', (alert_id,))
            notifications = [cls._row_to_notification(row).as_dict() for row in cursor.fetchall() if row is not None]

            return {
                'alert': cls._row_to_alert(alert).as_dict(),
                'acknowledgments': acknowledgments,
                'escalations': escalations,
                'notifications': notifications
            }
        finally:
            conn.close()

    @classmethod
    def acknowledge_alert(cls, alert_id: int, user_id: Optional[int] = None, notes: str = '') -> AlertAcknowledgmentRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.ACKNOWLEDGMENT_TABLE} (alert_id, acknowledged_by, notes)
                VALUES (?, ?, ?)
            ''', (alert_id, user_id, notes))
            conn.commit()
            return cls._row_to_acknowledgment(cursor.execute('SELECT * FROM alert_acknowledgment WHERE id = ?', (cursor.lastrowid,)).fetchone())
        finally:
            conn.close()

    @classmethod
    def escalate_alert(cls,
                       alert_id: int,
                       escalation_level: int = 1,
                       escalated_to: Optional[str] = None,
                       escalation_reason: str = '') -> AlertEscalationRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.ESCALATION_TABLE} (alert_id, escalation_level, escalated_to, escalation_reason)
                VALUES (?, ?, ?, ?)
            ''', (alert_id, escalation_level, escalated_to, escalation_reason))
            conn.commit()
            return cls._row_to_escalation(cursor.execute('SELECT * FROM alert_escalation WHERE id = ?', (cursor.lastrowid,)).fetchone())
        finally:
            conn.close()

    @classmethod
    def close_alert(cls, alert_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE {cls.ALERTS_TABLE}
                SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def list_recipients(cls) -> List[AlertRecipientRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.RECIPIENTS_TABLE} WHERE is_active = 1')
            return [cls._row_to_recipient(row) for row in cursor.fetchall() if row is not None]
        finally:
            conn.close()

    @classmethod
    def create_recipient(cls,
                         name: str,
                         email: Optional[str] = None,
                         phone: Optional[str] = None,
                         webhook_url: Optional[str] = None,
                         notification_types: Optional[str] = 'all',
                         priority_level: Optional[str] = None) -> AlertRecipientRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.RECIPIENTS_TABLE}
                (name, email, phone, webhook_url, notification_types, priority_level)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, webhook_url, notification_types, priority_level))
            conn.commit()
            return cls._row_to_recipient(cursor.execute('SELECT * FROM alert_recipients WHERE id = ?', (cursor.lastrowid,)).fetchone())
        finally:
            conn.close()

    @classmethod
    def update_recipient(cls, recipient_id: int, updates: Dict[str, Any]) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            fields = []
            params: List[Any] = []
            for key in ['name', 'email', 'phone', 'webhook_url', 'notification_types', 'priority_level']:
                if key in updates:
                    fields.append(f'{key} = ?')
                    params.append(updates[key])
            if not fields:
                return False
            params.append(recipient_id)
            cursor.execute(f'UPDATE {cls.RECIPIENTS_TABLE} SET {", ".join(fields)} WHERE id = ?', tuple(params))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def delete_recipient(cls, recipient_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'UPDATE {cls.RECIPIENTS_TABLE} SET is_active = 0 WHERE id = ?', (recipient_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def list_templates(cls) -> List[AlertTemplateRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.TEMPLATES_TABLE} WHERE enabled = 1')
            return [cls._row_to_template(row) for row in cursor.fetchall() if row is not None]
        finally:
            conn.close()

    @classmethod
    def create_template(cls,
                        name: str,
                        alert_type: str,
                        subject: Optional[str],
                        message: str,
                        severity: str = 'medium') -> AlertTemplateRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.TEMPLATES_TABLE}
                (name, alert_type, subject, message, severity)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, alert_type, subject, message, severity))
            conn.commit()
            return cls._row_to_template(cursor.execute('SELECT * FROM alert_templates WHERE id = ?', (cursor.lastrowid,)).fetchone())
        finally:
            conn.close()

    @classmethod
    def update_template(cls, template_id: int, updates: Dict[str, Any]) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            fields = []
            params: List[Any] = []
            for key in ['subject', 'message', 'severity']:
                if key in updates:
                    fields.append(f'{key} = ?')
                    params.append(updates[key])
            if not fields:
                return False
            params.append(template_id)
            cursor.execute(f'UPDATE {cls.TEMPLATES_TABLE} SET {", ".join(fields)} WHERE id = ?', tuple(params))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def disable_template(cls, template_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'UPDATE {cls.TEMPLATES_TABLE} SET enabled = 0 WHERE id = ?', (template_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def suppress_alert(cls,
                       alert_type: str,
                       duration_minutes: int = 60,
                       reason: str = '',
                       user_id: Optional[int] = None) -> AlertSuppressionRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            now = datetime.now()
            suppressed_until = now + timedelta(minutes=duration_minutes)
            cursor.execute(f'''
                INSERT INTO {cls.SUPPRESSION_TABLE}
                (alert_type, reason, suppressed_from, suppressed_until, user_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (alert_type, reason, now, suppressed_until, user_id))
            conn.commit()
            return cls._row_to_suppression(cursor.execute('SELECT * FROM alert_suppression WHERE id = ?', (cursor.lastrowid,)).fetchone())
        finally:
            conn.close()

    @classmethod
    def is_alert_suppressed(cls, alert_type: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            now = datetime.now()
            cursor.execute(f'''
                SELECT * FROM {cls.SUPPRESSION_TABLE}
                WHERE alert_type = ? AND suppressed_from <= ? AND suppressed_until >= ?
            ''', (alert_type, now, now))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    @classmethod
    def get_statistics(cls, hours: int = 24) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT COUNT(*) as total FROM {cls.ALERTS_TABLE} WHERE created_at > datetime('now', ?)", (f'-{hours} hours',))
            total = cursor.fetchone()['total']

            cursor.execute(f"SELECT COUNT(*) as open FROM {cls.ALERTS_TABLE} WHERE is_resolved = 0 AND created_at > datetime('now', ?)", (f'-{hours} hours',))
            open_alerts = cursor.fetchone()['open']

            cursor.execute(f"SELECT COUNT(*) as closed FROM {cls.ALERTS_TABLE} WHERE is_resolved = 1 AND created_at > datetime('now', ?)", (f'-{hours} hours',))
            closed_alerts = cursor.fetchone()['closed']

            cursor.execute(f"SELECT COUNT(DISTINCT alert_id) as acknowledged FROM {cls.ACKNOWLEDGMENT_TABLE} WHERE acknowledged_at > datetime('now', ?)", (f'-{hours} hours',))
            acknowledged = cursor.fetchone()['acknowledged']

            cursor.execute(f"SELECT severity, COUNT(*) as count FROM {cls.ALERTS_TABLE} WHERE created_at > datetime('now', ?) GROUP BY severity", (f'-{hours} hours',))
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}

            cursor.execute(f"SELECT alert_type, COUNT(*) as count FROM {cls.ALERTS_TABLE} WHERE created_at > datetime('now', ?) GROUP BY alert_type", (f'-{hours} hours',))
            by_type = {row['alert_type']: row['count'] for row in cursor.fetchall()}

            return {
                'total_alerts': total,
                'open_alerts': open_alerts,
                'closed_alerts': closed_alerts,
                'acknowledged_alerts': acknowledged,
                'by_severity': by_severity,
                'by_type': by_type,
                'time_period_hours': hours
            }
        finally:
            conn.close()

    @classmethod
    def serialize_alert(cls, alert: AlertRecord) -> Dict[str, Any]:
        return alert.as_dict() if alert else {}

    @classmethod
    def serialize_notification(cls, notification: AlertNotificationRecord) -> Dict[str, Any]:
        return notification.as_dict() if notification else {}

    @classmethod
    def serialize_escalation(cls, escalation: AlertEscalationRecord) -> Dict[str, Any]:
        return escalation.as_dict() if escalation else {}

    @classmethod
    def serialize_acknowledgment(cls, acknowledgment: AlertAcknowledgmentRecord) -> Dict[str, Any]:
        return acknowledgment.as_dict() if acknowledgment else {}

    @classmethod
    def serialize_template(cls, template: AlertTemplateRecord) -> Dict[str, Any]:
        return template.as_dict() if template else {}

    @classmethod
    def serialize_recipient(cls, recipient: AlertRecipientRecord) -> Dict[str, Any]:
        return recipient.as_dict() if recipient else {}

    @classmethod
    def serialize_suppression(cls, suppression: AlertSuppressionRecord) -> Dict[str, Any]:
        return suppression.as_dict() if suppression else {}
