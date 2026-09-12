"""
Detection model and database helpers for events, alerts, anomalies, and alert configuration.
Provides a reusable layer for detection persistence and analytics.
"""

import json
import os
import sqlite3
from dataclasses import dataclass
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
class DetectionEventRecord:
    id: int
    camera_id: Optional[int]
    detection_class: str
    confidence: float
    count: int
    bbox_data: Optional[str]
    frame_data: Optional[bytes]
    user_id: Optional[int]
    event_type: Optional[str]
    timestamp: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'detection_class': self.detection_class,
            'confidence': self.confidence,
            'count': self.count,
            'bbox_data': json.loads(self.bbox_data) if self.bbox_data else None,
            'event_type': self.event_type,
            'timestamp': self.timestamp,
            'user_id': self.user_id
        }


@dataclass
class DetectionAlertRecord:
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
class AlertConfigRecord:
    id: int
    camera_id: Optional[int]
    alert_type: str
    enabled: int
    threshold: Optional[float]
    cooldown_minutes: Optional[int]
    user_id: Optional[int]
    updated_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'alert_type': self.alert_type,
            'enabled': bool(self.enabled),
            'threshold': self.threshold,
            'cooldown_minutes': self.cooldown_minutes,
            'user_id': self.user_id,
            'updated_at': self.updated_at
        }


@dataclass
class AnomalyRecord:
    id: int
    camera_id: Optional[int]
    anomaly_type: str
    description: Optional[str]
    severity: str
    data: Optional[Dict[str, Any]]
    timestamp: str
    user_id: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'anomaly_type': self.anomaly_type,
            'description': self.description,
            'severity': self.severity,
            'data': self.data,
            'timestamp': self.timestamp,
            'user_id': self.user_id
        }


class DetectionModel:
    """Helper class for detection database operations."""

    EVENTS_TABLE = 'detection_events'
    ALERTS_TABLE = 'detection_alerts'
    CONFIG_TABLE = 'alert_config'
    ANOMALIES_TABLE = 'anomalies'

    @classmethod
    def initialize_tables(cls) -> None:
        """Create detection-related tables if they do not exist."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.EVENTS_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.ALERTS_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.CONFIG_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.ANOMALIES_TABLE} (
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
        finally:
            conn.close()

    @classmethod
    def _row_to_event(cls, row: sqlite3.Row) -> Optional[DetectionEventRecord]:
        if row is None:
            return None
        return DetectionEventRecord(
            id=row['id'],
            camera_id=row['camera_id'],
            detection_class=row['detection_class'],
            confidence=row['confidence'],
            count=row['count'],
            bbox_data=row['bbox_data'],
            frame_data=row['frame_data'],
            user_id=row['user_id'],
            event_type=row['event_type'],
            timestamp=row['timestamp']
        )

    @classmethod
    def _row_to_alert(cls, row: sqlite3.Row) -> Optional[DetectionAlertRecord]:
        if row is None:
            return None
        return DetectionAlertRecord(
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
    def _row_to_config(cls, row: sqlite3.Row) -> Optional[AlertConfigRecord]:
        if row is None:
            return None
        return AlertConfigRecord(
            id=row['id'],
            camera_id=row['camera_id'],
            alert_type=row['alert_type'],
            enabled=row['enabled'],
            threshold=row['threshold'],
            cooldown_minutes=row['cooldown_minutes'],
            user_id=row['user_id'],
            updated_at=row['updated_at']
        )

    @classmethod
    def _row_to_anomaly(cls, row: sqlite3.Row) -> Optional[AnomalyRecord]:
        if row is None:
            return None
        return AnomalyRecord(
            id=row['id'],
            camera_id=row['camera_id'],
            anomaly_type=row['anomaly_type'],
            description=row['description'],
            severity=row['severity'],
            data=json.loads(row['data']) if row['data'] else None,
            timestamp=row['timestamp'],
            user_id=row['user_id']
        )

    @classmethod
    def save_detection_event(cls,
                             camera_id: int,
                             detections: List[Dict[str, Any]],
                             frame_data: Optional[str] = None,
                             user_id: Optional[int] = None) -> DetectionEventRecord:
        detection_class = ','.join([d.get('class', '') for d in detections]) if detections else ''
        confidence = max([d.get('confidence', 0.0) for d in detections]) if detections else 0.0
        count = len(detections)
        bbox_data = json.dumps([d.get('bbox', {}) for d in detections]) if detections else None
        frame_bytes = frame_data.encode() if isinstance(frame_data, str) else frame_data
        event_type = 'multi' if count > 1 else 'single'

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.EVENTS_TABLE} (
                    camera_id, detection_class, confidence, count,
                    bbox_data, frame_data, user_id, event_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                camera_id,
                detection_class,
                confidence,
                count,
                bbox_data,
                frame_bytes,
                user_id,
                event_type
            ))
            conn.commit()
            return cls.get_event_by_id(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def get_event_by_id(cls, event_id: int) -> Optional[DetectionEventRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.EVENTS_TABLE} WHERE id = ?', (event_id,))
            return cls._row_to_event(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_detection_events(cls,
                             limit: int = 50,
                             camera_id: Optional[int] = None,
                             event_type: Optional[str] = None,
                             hours: int = 24) -> List[DetectionEventRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'SELECT * FROM {cls.EVENTS_TABLE} WHERE timestamp > datetime(\'now\', ?)'
            params: List[Any] = [f'-{hours} hours']

            if camera_id is not None:
                query += ' AND camera_id = ?'
                params.append(camera_id)

            if event_type:
                query += ' AND event_type = ?'
                params.append(event_type)

            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_event(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def save_alert(cls,
                   camera_id: int,
                   alert_type: str,
                   severity: str = 'medium',
                   detection_class: Optional[str] = None,
                   confidence: Optional[float] = None,
                   message: Optional[str] = None,
                   image_path: Optional[str] = None,
                   user_id: Optional[int] = None) -> DetectionAlertRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.ALERTS_TABLE} (
                    camera_id, alert_type, severity, detection_class,
                    confidence, message, image_path, user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                camera_id,
                alert_type,
                severity,
                detection_class,
                confidence,
                message,
                image_path,
                user_id
            ))
            conn.commit()
            return cls.get_alert_by_id(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def get_alert_by_id(cls, alert_id: int) -> Optional[DetectionAlertRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.ALERTS_TABLE} WHERE id = ?', (alert_id,))
            return cls._row_to_alert(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_alerts(cls,
                   limit: int = 50,
                   camera_id: Optional[int] = None,
                   alert_type: Optional[str] = None,
                   severity: Optional[str] = None,
                   is_resolved: Optional[int] = None,
                   hours: int = 24) -> List[DetectionAlertRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'SELECT * FROM {cls.ALERTS_TABLE} WHERE created_at > datetime(\'now\', ?)'
            params: List[Any] = [f'-{hours} hours']

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
            rows = cursor.fetchall()
            return [cls._row_to_alert(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def resolve_alert(cls, alert_id: int) -> bool:
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
    def save_anomaly(cls,
                     camera_id: int,
                     anomaly_type: str,
                     description: Optional[str] = None,
                     severity: str = 'low',
                     data: Optional[Dict[str, Any]] = None,
                     user_id: Optional[int] = None) -> AnomalyRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.ANOMALIES_TABLE} (
                    camera_id, anomaly_type, description, severity, data, user_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                camera_id,
                anomaly_type,
                description,
                severity,
                json.dumps(data) if data is not None else None,
                user_id
            ))
            conn.commit()
            return cls.get_anomaly_by_id(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def get_anomaly_by_id(cls, anomaly_id: int) -> Optional[AnomalyRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.ANOMALIES_TABLE} WHERE id = ?', (anomaly_id,))
            return cls._row_to_anomaly(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_anomalies(cls,
                      limit: int = 50,
                      camera_id: Optional[int] = None,
                      anomaly_type: Optional[str] = None,
                      severity: Optional[str] = None,
                      hours: int = 24) -> List[AnomalyRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'SELECT * FROM {cls.ANOMALIES_TABLE} WHERE timestamp > datetime(\'now\', ?)'
            params: List[Any] = [f'-{hours} hours']

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
            rows = cursor.fetchall()
            return [cls._row_to_anomaly(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def get_alert_config(cls, camera_id: int) -> List[AlertConfigRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.CONFIG_TABLE} WHERE camera_id = ?', (camera_id,))
            rows = cursor.fetchall()
            return [cls._row_to_config(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def set_alert_config(cls,
                         camera_id: int,
                         alert_type: str,
                         enabled: bool = True,
                         threshold: Optional[float] = None,
                         cooldown_minutes: int = 5,
                         user_id: Optional[int] = None) -> AlertConfigRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT id FROM {cls.CONFIG_TABLE} WHERE camera_id = ? AND alert_type = ?
            ''', (camera_id, alert_type))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(f'''
                    UPDATE {cls.CONFIG_TABLE}
                    SET enabled = ?, threshold = ?, cooldown_minutes = ?, user_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE camera_id = ? AND alert_type = ?
                ''', (int(enabled), threshold, cooldown_minutes, user_id, camera_id, alert_type))
                config_id = existing['id']
            else:
                cursor.execute(f'''
                    INSERT INTO {cls.CONFIG_TABLE} (
                        camera_id, alert_type, enabled, threshold, cooldown_minutes, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (camera_id, alert_type, int(enabled), threshold, cooldown_minutes, user_id))
                config_id = cursor.lastrowid

            conn.commit()
            return cls.get_alert_config_by_id(config_id)
        finally:
            conn.close()

    @classmethod
    def get_alert_config_by_id(cls, config_id: int) -> Optional[AlertConfigRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.CONFIG_TABLE} WHERE id = ?', (config_id,))
            return cls._row_to_config(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_detection_statistics(cls,
                                 camera_id: Optional[int] = None,
                                 hours: int = 24) -> Dict[str, Any]:
        events = cls.get_detection_events(limit=10000, camera_id=camera_id, hours=hours)
        alerts = cls.get_alerts(limit=10000, camera_id=camera_id, hours=hours)

        classes_count: Dict[str, int] = {}
        confidences: List[float] = []
        alert_severities: Dict[str, int] = {}

        for event in events:
            for cls_name in event.detection_class.split(',') if event.detection_class else []:
                classes_count[cls_name] = classes_count.get(cls_name, 0) + 1
            if event.confidence is not None:
                confidences.append(event.confidence)

        for alert in alerts:
            alert_severities[alert.severity] = alert_severities.get(alert.severity, 0) + 1

        most_detected_class = max(classes_count.items(), key=lambda x: x[1])[0] if classes_count else None
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        return {
            'total_events': len(events),
            'unique_classes': len(classes_count),
            'alert_count': len(alerts),
            'critical_alerts': alert_severities.get('critical', 0),
            'high_alerts': alert_severities.get('high', 0),
            'most_detected_class': most_detected_class,
            'avg_confidence': avg_confidence,
            'detection_classes': classes_count,
            'alert_severities': alert_severities,
            'time_period_hours': hours
        }

    @classmethod
    def check_alert_cooldown(cls,
                             alert_type: str,
                             camera_id: int,
                             cooldown_minutes: Optional[int] = None) -> bool:
        config = cls.get_alert_config(camera_id)
        cooldown = cooldown_minutes

        if not cooldown:
            for record in config:
                if record.alert_type == alert_type and record.cooldown_minutes is not None:
                    cooldown = record.cooldown_minutes
                    break

        if cooldown is None:
            cooldown = 5

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT created_at FROM {cls.ALERTS_TABLE}
                WHERE camera_id = ? AND alert_type = ? AND is_resolved = 0
                ORDER BY created_at DESC LIMIT 1
            ''', (camera_id, alert_type))
            last_alert = cursor.fetchone()
            if last_alert is None:
                return True

            last_time = last_alert['created_at']
            if last_time is None:
                return True

            cursor.execute(f"SELECT julianday('now') - julianday(?)", (last_time,))
            diff = cursor.fetchone()
            minutes_since = diff[0] * 24 * 60 if diff else float('inf')
            return minutes_since > cooldown
        finally:
            conn.close()

    @classmethod
    def serialize_event(cls, event: DetectionEventRecord) -> Dict[str, Any]:
        return event.as_dict() if event else {}

    @classmethod
    def serialize_alert(cls, alert: DetectionAlertRecord) -> Dict[str, Any]:
        return alert.as_dict() if alert else {}

    @classmethod
    def serialize_anomaly(cls, anomaly: AnomalyRecord) -> Dict[str, Any]:
        return anomaly.as_dict() if anomaly else {}

    @classmethod
    def serialize_config(cls, config: AlertConfigRecord) -> Dict[str, Any]:
        return config.as_dict() if config else {}
