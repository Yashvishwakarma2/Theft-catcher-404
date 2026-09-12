"""
AI Detection Processing Module
Provides object detection analysis, anomaly detection, and alert generation logic.
Integrates with detection models and database persistence.
"""

import os
import sys
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json

# Import database helper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_db_connection, get_database_path
from models.detection_model import DetectionModel
from models.alert_model import AlertModel


class DetectionType(Enum):
    """Detection classification types."""
    PERSON = "person"
    WEAPON = "weapon"
    VEHICLE = "vehicle"
    OBJECT = "object"
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Detection:
    """Single detection result from model."""
    class_name: str
    confidence: float
    bbox: Dict[str, float]  # {x, y, width, height}
    timestamp: str
    detection_type: DetectionType = DetectionType.UNKNOWN

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'class': self.class_name,
            'confidence': self.confidence,
            'bbox': self.bbox,
            'type': self.detection_type.value,
            'timestamp': self.timestamp
        }


@dataclass
class Anomaly:
    """Detected anomaly."""
    anomaly_type: str
    severity: str
    description: str
    count: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'type': self.anomaly_type,
            'severity': self.severity,
            'description': self.description
        }
        if self.count:
            result['count'] = self.count
        if self.data:
            result['data'] = self.data
        return result


# Target classes configuration
TARGET_CLASSES = {
    'person': ['person'],
    'weapon': ['knife', 'gun', 'baseball bat', 'revolver', 'pistol', 'rifle', 'shotgun'],
    'vehicle': ['car', 'truck', 'motorcycle', 'bicycle', 'bus', 'van'],
    'object': ['backpack', 'bag', 'suitcase', 'bottle', 'chair', 'box']
}

# Minimum confidence thresholds by detection type
MIN_CONFIDENCE_THRESHOLDS = {
    'person': 0.5,
    'weapon': 0.7,
    'vehicle': 0.6,
    'object': 0.5,
    'default': 0.4
}

# Anomaly detection thresholds
ANOMALY_THRESHOLDS = {
    'crowding': 10,  # Number of people for crowding alert
    'loitering': 300,  # Seconds (5 minutes) for loitering
    'multiple_weapons': 1,  # Number of weapons for alert
    'unusual_activity': 5  # Confidence threshold for unusual activity
}


def classify_detection(class_name: str) -> DetectionType:
    """
    Classify a detection into a category.

    Args:
        class_name: Class name from detection model

    Returns:
        DetectionType classification
    """
    class_lower = class_name.lower()

    if class_name in TARGET_CLASSES['person']:
        return DetectionType.PERSON

    if any(w in class_lower for w in TARGET_CLASSES['weapon']):
        return DetectionType.WEAPON

    if any(v in class_lower for v in TARGET_CLASSES['vehicle']):
        return DetectionType.VEHICLE

    if any(o in class_lower for o in TARGET_CLASSES['object']):
        return DetectionType.OBJECT

    return DetectionType.UNKNOWN


def filter_detections(detections: List[Dict[str, Any]]) -> List[Detection]:
    """
    Filter and validate detections based on confidence thresholds.

    Args:
        detections: List of raw detections from model

    Returns:
        List of filtered Detection objects
    """
    filtered = []

    for det in detections:
        if not isinstance(det, dict):
            continue

        class_name = det.get('class', 'unknown')
        confidence = float(det.get('confidence', 0.0))
        bbox = det.get('bbox', {})
        timestamp = det.get('timestamp', datetime.now().isoformat())

        # Determine detection type
        det_type = classify_detection(class_name)

        # Check minimum confidence
        min_conf = MIN_CONFIDENCE_THRESHOLDS.get(det_type.value, 0.5)
        if confidence < min_conf:
            continue

        detection = Detection(
            class_name=class_name,
            confidence=confidence,
            bbox=bbox,
            timestamp=timestamp,
            detection_type=det_type
        )
        filtered.append(detection)

    return filtered


def detect_crowding(detections: List[Detection], threshold: int = None) -> Optional[Anomaly]:
    """
    Detect crowding anomaly (too many people in frame).

    Args:
        detections: List of filtered detections
        threshold: Crowding threshold (number of people)

    Returns:
        Anomaly object or None
    """
    if threshold is None:
        threshold = ANOMALY_THRESHOLDS['crowding']

    people_count = sum(1 for d in detections if d.detection_type == DetectionType.PERSON)

    if people_count > threshold:
        return Anomaly(
            anomaly_type='crowding',
            severity=SeverityLevel.MEDIUM.value,
            description=f'Crowding detected: {people_count} people in frame',
            count=people_count
        )

    return None


def detect_weapon(detections: List[Detection]) -> Optional[Anomaly]:
    """
    Detect weapon anomaly.

    Args:
        detections: List of filtered detections

    Returns:
        Anomaly object or None
    """
    weapons = [d for d in detections if d.detection_type == DetectionType.WEAPON]

    if weapons:
        # Get highest confidence weapon
        highest_conf_weapon = max(weapons, key=lambda x: x.confidence)
        descriptions = [f"{w.class_name} (confidence: {w.confidence:.2f})" for w in weapons]

        return Anomaly(
            anomaly_type='weapon_detected',
            severity=SeverityLevel.CRITICAL.value,
            description=f'Weapon detected: {", ".join(descriptions)}',
            count=len(weapons),
            data={
                'weapons': [w.as_dict() for w in weapons],
                'highest_confidence': highest_conf_weapon.confidence
            }
        )

    return None


def detect_loitering(current_detections: List[Detection],
                    previous_detections: List[Dict[str, Any]],
                    time_threshold: int = None) -> Optional[Anomaly]:
    """
    Detect loitering anomaly (same person in frame for too long).

    Args:
        current_detections: Current frame detections
        previous_detections: Previous detection records (with timestamps)
        time_threshold: Time threshold in seconds

    Returns:
        Anomaly object or None
    """
    if time_threshold is None:
        time_threshold = ANOMALY_THRESHOLDS['loitering']

    # Simple implementation: check if same number of people are detected
    # In production, use person tracking/reid
    current_people = [d for d in current_detections if d.detection_type == DetectionType.PERSON]

    if len(current_people) > 0:
        # Check if previous detections had similar count over extended period
        similar_count = sum(1 for p in previous_detections if p.get('type') == 'person')

        if similar_count > len(current_people) / 2:
            # Potential loitering
            return Anomaly(
                anomaly_type='loitering',
                severity=SeverityLevel.MEDIUM.value,
                description=f'Loitering detected: person in frame for extended period',
                count=len(current_people)
            )

    return None


def detect_unusual_activity(detections: List[Detection],
                           detection_count_threshold: int = 5) -> Optional[Anomaly]:
    """
    Detect unusual activity (multiple detections with high confidence).

    Args:
        detections: List of filtered detections
        detection_count_threshold: Threshold for unusual count

    Returns:
        Anomaly object or None
    """
    high_conf_detections = [d for d in detections if d.confidence > 0.8]

    if len(high_conf_detections) > detection_count_threshold:
        return Anomaly(
            anomaly_type='unusual_activity',
            severity=SeverityLevel.HIGH.value,
            description=f'Unusual activity: {len(high_conf_detections)} high-confidence detections',
            count=len(high_conf_detections),
            data={
                'high_confidence_detections': [d.as_dict() for d in high_conf_detections]
            }
        )

    return None


def process_detections(detections: List[Dict[str, Any]],
                      camera_id: int,
                      previous_detections: Optional[List[Dict]] = None) -> Tuple[List[Detection], List[Anomaly]]:
    """
    Process raw detections and identify anomalies.
    Integrates with database persistence.

    Args:
        detections: Raw detections from model
        camera_id: Camera ID
        previous_detections: Previous frame detections for temporal analysis

    Returns:
        Tuple of (filtered_detections, anomalies)
    """
    # Filter and validate detections
    filtered = filter_detections(detections)

    # Detect anomalies
    anomalies = []

    crowding_anomaly = detect_crowding(filtered)
    if crowding_anomaly:
        anomalies.append(crowding_anomaly)

    weapon_anomaly = detect_weapon(filtered)
    if weapon_anomaly:
        anomalies.append(weapon_anomaly)

    if previous_detections:
        loitering_anomaly = detect_loitering(filtered, previous_detections)
        if loitering_anomaly:
            anomalies.append(loitering_anomaly)

    unusual_anomaly = detect_unusual_activity(filtered)
    if unusual_anomaly:
        anomalies.append(unusual_anomaly)

    return filtered, anomalies


def generate_alert(anomaly: Anomaly, camera_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate an alert from an anomaly.

    Args:
        anomaly: Detected anomaly
        camera_id: Camera ID
        user_id: User ID

    Returns:
        Alert dictionary
    """
    severity_map = {
        'weapon_detected': SeverityLevel.CRITICAL,
        'crowding': SeverityLevel.MEDIUM,
        'loitering': SeverityLevel.MEDIUM,
        'unusual_activity': SeverityLevel.HIGH
    }

    severity = severity_map.get(anomaly.anomaly_type, SeverityLevel.MEDIUM).value

    alert_type_map = {
        'weapon_detected': 'weapon',
        'crowding': 'intrusion',
        'loitering': 'suspicious',
        'unusual_activity': 'anomaly'
    }

    alert_type = alert_type_map.get(anomaly.anomaly_type, 'custom')

    return {
        'camera_id': camera_id,
        'alert_type': alert_type,
        'severity': severity,
        'message': anomaly.description,
        'detection_class': anomaly.anomaly_type,
        'confidence': 0.9,  # System confidence in anomaly
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }


def analyze_detection_frame(frame_data: Dict[str, Any],
                           camera_id: int,
                           user_id: Optional[int] = None,
                           previous_frame: Optional[Dict] = None,
                           persist_to_db: bool = True) -> Dict[str, Any]:
    """
    Analyze a detection frame and generate results with database persistence.

    Args:
        frame_data: Frame with detections {'detections': [...]}
        camera_id: Camera ID
        user_id: User ID
        previous_frame: Previous frame analysis result
        persist_to_db: Whether to save results to database

    Returns:
        Analysis result with detections, anomalies, and alerts
    """
    detections = frame_data.get('detections', [])
    previous_detections = previous_frame.get('detections') if previous_frame else None

    # Process detections
    filtered, anomalies = process_detections(detections, camera_id, previous_detections)

    # Generate alerts
    alerts = [generate_alert(a, camera_id, user_id) for a in anomalies]

    result = {
        'camera_id': camera_id,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        'detections': [d.as_dict() for d in filtered],
        'anomalies': [a.as_dict() for a in anomalies],
        'alerts': alerts,
        'detection_count': len(filtered),
        'anomaly_count': len(anomalies),
        'alert_count': len(alerts)
    }

    # Persist to database if enabled
    if persist_to_db:
        try:
            # Save detection event
            DetectionModel.save_detection_event(
                camera_id=camera_id,
                detections=[d.as_dict() for d in filtered],
                frame_data=None,
                user_id=user_id
            )

            # Save anomalies and alerts
            for anomaly in anomalies:
                alert_data = generate_alert(anomaly, camera_id, user_id)
                DetectionModel.save_alert(
                    camera_id=alert_data['camera_id'],
                    alert_type=alert_data['alert_type'],
                    severity=alert_data['severity'],
                    detection_class=alert_data['detection_class'],
                    confidence=alert_data['confidence'],
                    message=alert_data['message'],
                    user_id=user_id
                )

                # Save anomaly record
                DetectionModel.save_anomaly(
                    camera_id=camera_id,
                    anomaly_type=anomaly.anomaly_type,
                    description=anomaly.description,
                    severity=anomaly.severity,
                    data=anomaly.data,
                    user_id=user_id
                )
        except Exception as e:
            print(f"Error persisting detection results: {e}")

    return result


def serialize_detection(detection: Dict[str, Any]) -> str:
    """Serialize detection to JSON string."""
    return json.dumps(detection, default=str)


def deserialize_detection(json_str: str) -> Dict[str, Any]:
    """Deserialize detection from JSON string."""
    return json.loads(json_str)


def check_alert_cooldown(alert_type: str, camera_id: int, cooldown_minutes: int = 5) -> bool:
    """
    Check if an alert of the given type can be generated (respects cooldown).

    Args:
        alert_type: Type of alert
        camera_id: Camera ID
        cooldown_minutes: Cooldown period in minutes

    Returns:
        True if alert can be generated, False if in cooldown
    """
    try:
        return DetectionModel.check_alert_cooldown(alert_type, camera_id, cooldown_minutes)
    except:
        return True  # Default to allowing alert if check fails


def get_detection_statistics(camera_id: int, hours: int = 24) -> Dict[str, Any]:
    """
    Get detection statistics for a camera.

    Args:
        camera_id: Camera ID
        hours: Number of hours to analyze

    Returns:
        Statistics dictionary with detection counts and alerts
    """
    try:
        return DetectionModel.get_detection_statistics(camera_id, hours)
    except:
        return {
            'detection_count': 0,
            'alert_count': 0,
            'anomaly_count': 0,
            'total_people': 0,
            'total_weapons': 0,
            'critical_alerts': 0
        }


def process_batch_detections(batch_frames: List[Dict[str, Any]],
                            camera_id: int,
                            user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Process a batch of detection frames.

    Args:
        batch_frames: List of frame data
        camera_id: Camera ID
        user_id: User ID

    Returns:
        List of analysis results
    """
    results = []
    previous_frame = None

    for frame in batch_frames:
        result = analyze_detection_frame(
            frame,
            camera_id,
            user_id,
            previous_frame,
            persist_to_db=True
        )
        results.append(result)
        previous_frame = result

    return results
