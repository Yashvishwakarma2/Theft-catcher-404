"""
Object Tracking Module
Handles tracking of detected objects across video frames using centroid tracking and distance metrics.
"""

import os
import sys
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class BBox:
    """Bounding box representation."""
    x: float
    y: float
    width: float
    height: float

    @property
    def x1(self) -> float:
        return self.x

    @property
    def y1(self) -> float:
        return self.y

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    @property
    def centroid(self) -> Tuple[float, float]:
        """Get bounding box centroid."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        """Get bounding box area."""
        return self.width * self.height

    def __eq__(self, other):
        if not isinstance(other, BBox):
            return False
        return (self.x == other.x and self.y == other.y and
                self.width == other.width and self.height == other.height)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'BBox':
        """Create BBox from dictionary."""
        if 'x1' in data and 'y1' in data and 'x2' in data and 'y2' in data:
            x1, y1, x2, y2 = data['x1'], data['y1'], data['x2'], data['y2']
            return cls(x1, y1, x2 - x1, y2 - y1)
        else:
            return cls(data['x'], data['y'], data['width'], data['height'])


@dataclass
class TrackedObject:
    """Represents a tracked object across frames."""
    object_id: int
    class_name: str
    class_id: int
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    confidence_history: List[float] = field(default_factory=list)
    bbox_history: List[BBox] = field(default_factory=list)
    centroid_history: deque = field(default_factory=lambda: deque(maxlen=50))
    frame_count: int = 0
    missed_frames: int = 0

    @property
    def age(self) -> float:
        """Get object age in seconds."""
        return (datetime.now() - self.first_seen).total_seconds()

    @property
    def last_confidence(self) -> float:
        """Get last detection confidence."""
        return self.confidence_history[-1] if self.confidence_history else 0.0

    @property
    def avg_confidence(self) -> float:
        """Get average confidence across all detections."""
        if not self.confidence_history:
            return 0.0
        return sum(self.confidence_history) / len(self.confidence_history)

    @property
    def current_bbox(self) -> Optional[BBox]:
        """Get most recent bounding box."""
        return self.bbox_history[-1] if self.bbox_history else None

    @property
    def current_centroid(self) -> Optional[Tuple[float, float]]:
        """Get most recent centroid."""
        return self.centroid_history[-1] if self.centroid_history else None

    def update(self, bbox: BBox, confidence: float):
        """Update tracked object with new detection."""
        self.bbox_history.append(bbox)
        self.confidence_history.append(confidence)
        self.centroid_history.append(bbox.centroid)
        self.last_seen = datetime.now()
        self.frame_count += 1
        self.missed_frames = 0

    def miss(self):
        """Record a missed detection."""
        self.missed_frames += 1

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        current_bbox = self.current_bbox
        return {
            'object_id': self.object_id,
            'class_name': self.class_name,
            'class_id': self.class_id,
            'age': self.age,
            'frame_count': self.frame_count,
            'last_confidence': self.last_confidence,
            'avg_confidence': self.avg_confidence,
            'bbox': {
                'x': current_bbox.x,
                'y': current_bbox.y,
                'width': current_bbox.width,
                'height': current_bbox.height
            } if current_bbox else None,
            'centroid': self.current_centroid,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'missed_frames': self.missed_frames
        }


class CentroidTracker:
    """
    Centroid-based object tracker.
    Tracks objects by matching centroids between consecutive frames.
    """

    def __init__(self, max_distance: float = 50.0, max_disappeared: int = 30):
        """
        Initialize centroid tracker.

        Args:
            max_distance: Maximum distance between centroids for matching
            max_disappeared: Max frames an object can disappear before removal
        """
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.next_object_id = 0
        self.objects: Dict[int, TrackedObject] = {}
        self.frame_count = 0

    def update(self, detections: List[Dict[str, Any]]) -> Dict[int, TrackedObject]:
        """
        Update tracker with new detections.

        Args:
            detections: List of detection dictionaries with 'class', 'class_id', 'confidence', 'bbox'

        Returns:
            Dictionary of tracked objects
        """
        self.frame_count += 1

        # Extract bboxes and build current positions
        input_centroids = {}
        for i, detection in enumerate(detections):
            bbox = BBox.from_dict(detection['bbox'])
            input_centroids[i] = {
                'centroid': bbox.centroid,
                'bbox': bbox,
                'class_name': detection.get('class', 'unknown'),
                'class_id': detection.get('class_id', -1),
                'confidence': detection.get('confidence', 0.5)
            }

        # If no objects tracked, initialize with detections
        if not self.objects:
            for i, data in input_centroids.items():
                tracked_obj = TrackedObject(
                    object_id=self.next_object_id,
                    class_name=data['class_name'],
                    class_id=data['class_id']
                )
                tracked_obj.update(data['bbox'], data['confidence'])
                self.objects[self.next_object_id] = tracked_obj
                self.next_object_id += 1
            return self.objects

        # Match current detections with tracked objects
        object_ids = list(self.objects.keys())
        object_centroids = [self.objects[oid].current_centroid for oid in object_ids]

        # Compute distances between object centroids and input centroids
        matched, unmatched_detections, unmatched_objects = self._match_detections(
            object_centroids, input_centroids
        )

        # Update matched objects
        for obj_idx, det_idx in matched:
            obj_id = object_ids[obj_idx]
            det_data = input_centroids[det_idx]
            self.objects[obj_id].update(det_data['bbox'], det_data['confidence'])

        # Register new detections
        for det_idx in unmatched_detections:
            det_data = input_centroids[det_idx]
            tracked_obj = TrackedObject(
                object_id=self.next_object_id,
                class_name=det_data['class_name'],
                class_id=det_data['class_id']
            )
            tracked_obj.update(det_data['bbox'], det_data['confidence'])
            self.objects[self.next_object_id] = tracked_obj
            self.next_object_id += 1

        # Deregister disappeared objects
        disappeared_ids = []
        for obj_idx in unmatched_objects:
            obj_id = object_ids[obj_idx]
            self.objects[obj_id].miss()

            if self.objects[obj_id].missed_frames > self.max_disappeared:
                disappeared_ids.append(obj_id)

        for obj_id in disappeared_ids:
            del self.objects[obj_id]

        return self.objects

    def _match_detections(self, object_centroids: List[Tuple[float, float]],
                         input_centroids: Dict[int, Dict]) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Match object centroids with input detections.

        Returns:
            Tuple of (matched_pairs, unmatched_detections, unmatched_objects)
        """
        if len(object_centroids) == 0:
            return [], list(input_centroids.keys()), []

        # Compute distance matrix
        distances = []
        for obj_centroid in object_centroids:
            row = []
            for det_idx, det_data in input_centroids.items():
                dist = self._euclidean_distance(obj_centroid, det_data['centroid'])
                row.append(dist)
            distances.append(row)

        # Find matches using greedy algorithm
        matched = []
        matched_obj_idxs = set()
        matched_det_idxs = set()

        # Sort distances
        distance_tuples = []
        for i, row in enumerate(distances):
            for j, dist in enumerate(row):
                distance_tuples.append((dist, i, j))
        distance_tuples.sort()

        for dist, obj_idx, det_idx in distance_tuples:
            if dist > self.max_distance:
                break
            if obj_idx not in matched_obj_idxs and det_idx not in matched_det_idxs:
                matched.append((obj_idx, det_idx))
                matched_obj_idxs.add(obj_idx)
                matched_det_idxs.add(det_idx)

        unmatched_detections = [i for i in input_centroids.keys() if i not in matched_det_idxs]
        unmatched_objects = [i for i in range(len(object_centroids)) if i not in matched_obj_idxs]

        return matched, unmatched_detections, unmatched_objects

    @staticmethod
    def _euclidean_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
        """Compute Euclidean distance between two points."""
        return math.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)

    def reset(self):
        """Reset tracker."""
        self.objects.clear()
        self.frame_count = 0

    def get_tracked_objects(self) -> Dict[int, Dict[str, Any]]:
        """Get all tracked objects as dictionaries."""
        return {oid: obj.as_dict() for oid, obj in self.objects.items()}

    def get_objects_by_class(self, class_name: str) -> List[TrackedObject]:
        """Get tracked objects of a specific class."""
        return [obj for obj in self.objects.values() if obj.class_name == class_name]


class MotionTracker:
    """Analyzes motion patterns of tracked objects."""

    @staticmethod
    def estimate_velocity(tracked_obj: TrackedObject) -> Optional[Tuple[float, float]]:
        """
        Estimate velocity of tracked object.

        Args:
            tracked_obj: TrackedObject instance

        Returns:
            Tuple of (vx, vy) or None if not enough history
        """
        history = list(tracked_obj.centroid_history)

        if len(history) < 2:
            return None

        x1, y1 = history[-2]
        x2, y2 = history[-1]

        vx = x2 - x1
        vy = y2 - y1

        return (vx, vy)

    @staticmethod
    def estimate_speed(velocity: Tuple[float, float]) -> float:
        """Estimate speed from velocity."""
        if velocity is None:
            return 0.0
        return math.sqrt(velocity[0] ** 2 + velocity[1] ** 2)

    @staticmethod
    def detect_stationary(tracked_obj: TrackedObject, velocity_threshold: float = 2.0) -> bool:
        """Detect if object is stationary."""
        velocity = MotionTracker.estimate_velocity(tracked_obj)
        if velocity is None:
            return False

        speed = MotionTracker.estimate_speed(velocity)
        return speed < velocity_threshold

    @staticmethod
    def detect_loitering(tracked_obj: TrackedObject, duration_threshold: float = 5.0,
                        area_threshold: float = 100.0) -> bool:
        """
        Detect if object is loitering (stationary for extended period).

        Args:
            tracked_obj: TrackedObject instance
            duration_threshold: Time threshold in seconds
            area_threshold: Area threshold in pixels for motion region

        Returns:
            True if loitering detected
        """
        age = tracked_obj.age
        if age < duration_threshold:
            return False

        # Check if centroid variation is small
        if len(tracked_obj.centroid_history) < 5:
            return False

        centroids = list(tracked_obj.centroid_history)
        recent_centroids = centroids[-10:]

        # Calculate bounding box of recent centroids
        xs = [c[0] for c in recent_centroids]
        ys = [c[1] for c in recent_centroids]

        motion_area = (max(xs) - min(xs)) * (max(ys) - min(ys))

        return motion_area < area_threshold

    @staticmethod
    def detect_rapid_movement(tracked_obj: TrackedObject, speed_threshold: float = 50.0) -> bool:
        """Detect if object is moving rapidly."""
        velocity = MotionTracker.estimate_velocity(tracked_obj)
        if velocity is None:
            return False

        speed = MotionTracker.estimate_speed(velocity)
        return speed > speed_threshold


class TrackingAnalyzer:
    """Analyzes tracking data for insights and anomalies."""

    @staticmethod
    def get_track_statistics(tracker: CentroidTracker) -> Dict[str, Any]:
        """Get statistics about tracked objects."""
        objects = tracker.objects.values()

        if not objects:
            return {
                'total_objects': 0,
                'active_objects': 0,
                'avg_age': 0,
                'classes': {}
            }

        active_objects = [obj for obj in objects if obj.missed_frames == 0]

        classes_stats = defaultdict(lambda: {'count': 0, 'avg_confidence': 0})
        for obj in objects:
            classes_stats[obj.class_name]['count'] += 1
            classes_stats[obj.class_name]['avg_confidence'] += obj.avg_confidence

        for class_name in classes_stats:
            count = classes_stats[class_name]['count']
            classes_stats[class_name]['avg_confidence'] /= count

        return {
            'total_objects': len(objects),
            'active_objects': len(active_objects),
            'avg_age': sum(obj.age for obj in objects) / len(objects) if objects else 0,
            'classes': dict(classes_stats)
        }

    @staticmethod
    def detect_crowd(tracker: CentroidTracker, class_name: str = 'person',
                    density_threshold: int = 10) -> bool:
        """Detect crowding (many objects close together)."""
        objects = tracker.get_objects_by_class(class_name)

        if len(objects) < density_threshold:
            return False

        return True

    @staticmethod
    def get_loitering_objects(tracker: CentroidTracker) -> List[Dict[str, Any]]:
        """Get list of loitering objects."""
        loitering = []

        for obj in tracker.objects.values():
            if MotionTracker.detect_loitering(obj):
                loitering.append({
                    'object_id': obj.object_id,
                    'class': obj.class_name,
                    'age': obj.age,
                    'position': obj.current_centroid
                })

        return loitering

    @staticmethod
    def get_high_speed_objects(tracker: CentroidTracker, threshold: float = 50.0) -> List[Dict[str, Any]]:
        """Get list of rapidly moving objects."""
        fast_movers = []

        for obj in tracker.objects.values():
            if MotionTracker.detect_rapid_movement(obj, threshold):
                velocity = MotionTracker.estimate_velocity(obj)
                speed = MotionTracker.estimate_speed(velocity)
                fast_movers.append({
                    'object_id': obj.object_id,
                    'class': obj.class_name,
                    'speed': speed,
                    'velocity': velocity
                })

        return fast_movers
