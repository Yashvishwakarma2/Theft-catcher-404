"""
Camera model and database helpers for camera history and session management.
Provides a reusable layer for camera detection persistence, camera sessions, and analytics.
"""

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
class DetectionHistoryRecord:
    id: int
    camera_id: Optional[int]
    detection_class: str
    confidence: float
    x: Optional[int]
    y: Optional[int]
    width: Optional[int]
    height: Optional[int]
    timestamp: str
    image_path: Optional[str]
    user_id: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'class': self.detection_class,
            'confidence': self.confidence,
            'bbox': {
                'x': self.x,
                'y': self.y,
                'width': self.width,
                'height': self.height
            } if self.x is not None and self.y is not None else None,
            'timestamp': self.timestamp,
            'image_path': self.image_path,
            'user_id': self.user_id
        }


@dataclass
class CameraSessionRecord:
    id: int
    camera_id: Optional[int]
    user_id: Optional[int]
    start_time: str
    end_time: Optional[str]
    recording_file: Optional[str]
    detections_count: int
    is_active: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'user_id': self.user_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'recording_file': self.recording_file,
            'detections_count': self.detections_count,
            'is_active': bool(self.is_active)
        }


class CameraModel:
    """Helper class for camera database operations."""

    HISTORY_TABLE = 'detection_history'
    SESSION_TABLE = 'camera_sessions'

    @classmethod
    def initialize_tables(cls) -> None:
        """Create detection history and camera session tables if they do not exist."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.HISTORY_TABLE} (
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

            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.SESSION_TABLE} (
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
        finally:
            conn.close()

    @classmethod
    def _row_to_history(cls, row: sqlite3.Row) -> Optional[DetectionHistoryRecord]:
        if row is None:
            return None
        return DetectionHistoryRecord(
            id=row['id'],
            camera_id=row['camera_id'],
            detection_class=row['detection_class'],
            confidence=row['confidence'],
            x=row['x'],
            y=row['y'],
            width=row['width'],
            height=row['height'],
            timestamp=row['timestamp'],
            image_path=row['image_path'],
            user_id=row['user_id']
        )

    @classmethod
    def _row_to_session(cls, row: sqlite3.Row) -> Optional[CameraSessionRecord]:
        if row is None:
            return None
        return CameraSessionRecord(
            id=row['id'],
            camera_id=row['camera_id'],
            user_id=row['user_id'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            recording_file=row['recording_file'],
            detections_count=row['detections_count'],
            is_active=row['is_active']
        )

    @classmethod
    def save_detection(cls,
                       camera_id: int,
                       detection_class: str,
                       confidence: float,
                       x: Optional[int] = None,
                       y: Optional[int] = None,
                       width: Optional[int] = None,
                       height: Optional[int] = None,
                       image_path: Optional[str] = None,
                       user_id: Optional[int] = None) -> DetectionHistoryRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.HISTORY_TABLE} (
                    camera_id, detection_class, confidence,
                    x, y, width, height, image_path, user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                camera_id,
                detection_class,
                confidence,
                x,
                y,
                width,
                height,
                image_path,
                user_id
            ))
            conn.commit()
            return cls.get_history_by_id(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def get_history_by_id(cls, history_id: int) -> Optional[DetectionHistoryRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.HISTORY_TABLE} WHERE id = ?', (history_id,))
            return cls._row_to_history(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_detection_history(cls,
                              limit: int = 100,
                              camera_id: Optional[int] = None,
                              detection_class: Optional[str] = None,
                              hours: int = 24) -> List[DetectionHistoryRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'SELECT * FROM {cls.HISTORY_TABLE} WHERE timestamp > datetime(\'now\', ?)'  # noqa: E501
            params: List[Any] = [f'-{hours} hours']

            if camera_id is not None:
                query += ' AND camera_id = ?'
                params.append(camera_id)

            if detection_class:
                query += ' AND detection_class = ?'
                params.append(detection_class)

            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_history(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def get_history_stats(cls,
                          hours: int = 24,
                          camera_id: Optional[int] = None) -> Dict[str, Any]:
        history = cls.get_detection_history(limit=10000, camera_id=camera_id, hours=hours)
        total = len(history)
        classes_count: Dict[str, int] = {}
        confidences: List[float] = []

        for record in history:
            classes_count[record.detection_class] = classes_count.get(record.detection_class, 0) + 1
            confidences.append(record.confidence)

        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        return {
            'total_detections': total,
            'unique_classes': len(classes_count),
            'classes': classes_count,
            'avg_confidence': avg_confidence,
            'time_period_hours': hours
        }

    @classmethod
    def clear_detection_history(cls,
                                camera_id: Optional[int] = None,
                                older_than_hours: Optional[int] = None) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'DELETE FROM {cls.HISTORY_TABLE}'
            params: List[Any] = []
            predicates: List[str] = []

            if camera_id is not None:
                predicates.append('camera_id = ?')
                params.append(camera_id)

            if older_than_hours is not None:
                predicates.append('timestamp < datetime(\'now\', ?)')
                params.append(f'-{older_than_hours} hours')

            if predicates:
                query += ' WHERE ' + ' AND '.join(predicates)

            cursor.execute(query, params)
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()

    @classmethod
    def create_camera_session(cls,
                              camera_id: int,
                              user_id: Optional[int] = None,
                              recording_file: Optional[str] = None) -> CameraSessionRecord:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.SESSION_TABLE} (
                    camera_id, user_id, recording_file
                )
                VALUES (?, ?, ?)
            ''', (
                camera_id,
                user_id,
                recording_file
            ))
            conn.commit()
            return cls.get_session_by_id(cursor.lastrowid)
        finally:
            conn.close()

    @classmethod
    def get_session_by_id(cls, session_id: int) -> Optional[CameraSessionRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.SESSION_TABLE} WHERE id = ?', (session_id,))
            return cls._row_to_session(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def end_camera_session(cls,
                           session_id: int,
                           recording_file: Optional[str] = None,
                           detections_count: Optional[int] = None) -> Optional[CameraSessionRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            updates = ['end_time = CURRENT_TIMESTAMP', 'is_active = 0']
            params: List[Any] = []

            if recording_file is not None:
                updates.append('recording_file = ?')
                params.append(recording_file)

            if detections_count is not None:
                updates.append('detections_count = ?')
                params.append(detections_count)

            params.append(session_id)
            query = f'UPDATE {cls.SESSION_TABLE} SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, tuple(params))
            conn.commit()
            return cls.get_session_by_id(session_id)
        finally:
            conn.close()

    @classmethod
    def get_active_session(cls, camera_id: int) -> Optional[CameraSessionRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'SELECT * FROM {cls.SESSION_TABLE} WHERE camera_id = ? AND is_active = 1 ORDER BY start_time DESC LIMIT 1',
                (camera_id,)
            )
            return cls._row_to_session(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def list_camera_sessions(cls,
                             limit: int = 100,
                             camera_id: Optional[int] = None,
                             user_id: Optional[int] = None,
                             active_only: Optional[bool] = None) -> List[CameraSessionRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = f'SELECT * FROM {cls.SESSION_TABLE}'
            params: List[Any] = []
            filters: List[str] = []

            if camera_id is not None:
                filters.append('camera_id = ?')
                params.append(camera_id)

            if user_id is not None:
                filters.append('user_id = ?')
                params.append(user_id)

            if active_only is not None:
                filters.append('is_active = ?')
                params.append(int(active_only))

            if filters:
                query += ' WHERE ' + ' AND '.join(filters)

            query += ' ORDER BY start_time DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [cls._row_to_session(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def increment_session_detections(cls, session_id: int, count: int = 1) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'UPDATE {cls.SESSION_TABLE} SET detections_count = detections_count + ? WHERE id = ?',
                (count, session_id)
            )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def serialize_detection(cls, record: DetectionHistoryRecord) -> Dict[str, Any]:
        return record.as_dict() if record else {}

    @classmethod
    def serialize_session(cls, record: CameraSessionRecord) -> Dict[str, Any]:
        return record.as_dict() if record else {}
