"""
AI Routes
Connects AI detection, tracking, and alerting modules to Flask API endpoints.
"""

from flask import Blueprint, jsonify, request
from typing import Optional

from ai.detect import analyze_detection_frame, get_detection_statistics, process_batch_detections
from ai.tracker import CentroidTracker, TrackingAnalyzer
from models.detection_model import DetectionModel

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

tracker = CentroidTracker(max_distance=80.0, max_disappeared=40)
tracker_analyzer = TrackingAnalyzer()


@ai_bp.route('/process', methods=['POST'])
def process_ai_detection():
    """Process a single AI detection frame and persist analytics."""
    data = request.get_json() or {}
    if 'detections' not in data:
        return jsonify({'success': False, 'error': 'Missing detections field'}), 400

    camera_id = data.get('camera_id', 0)
    user_id = data.get('user_id')
    previous_frame = data.get('previous_frame')

    result = analyze_detection_frame(
        data,
        camera_id=camera_id,
        user_id=user_id,
        previous_frame=previous_frame,
        persist_to_db=True
    )

    return jsonify({'success': True, 'result': result}), 200


@ai_bp.route('/stats', methods=['GET'])
def ai_statistics():
    """Return detection statistics for a camera."""
    camera_id = request.args.get('camera_id', default=0, type=int)
    hours = request.args.get('hours', default=24, type=int)
    stats = get_detection_statistics(camera_id=camera_id, hours=hours)
    return jsonify({'success': True, 'statistics': stats}), 200


@ai_bp.route('/batch', methods=['POST'])
def process_batch():
    """Process a batch of detection frames."""
    data = request.get_json() or {}
    if 'frames' not in data or not isinstance(data['frames'], list):
        return jsonify({'success': False, 'error': 'Missing frames array'}), 400

    camera_id = data.get('camera_id', 0)
    user_id = data.get('user_id')
    results = process_batch_detections(data['frames'], camera_id=camera_id, user_id=user_id)
    return jsonify({'success': True, 'results': results}), 200


@ai_bp.route('/alerts', methods=['GET'])
def list_ai_alerts():
    """List recent AI-generated alerts."""
    camera_id = request.args.get('camera_id', type=int)
    alerts = DetectionModel.get_alerts(limit=100, camera_id=camera_id)
    return jsonify({'success': True, 'alerts': [a.as_dict() for a in alerts]}), 200


@ai_bp.route('/anomalies', methods=['GET'])
def list_ai_anomalies():
    """List recent AI-detected anomalies."""
    camera_id = request.args.get('camera_id', type=int)
    anomalies = DetectionModel.get_anomalies(limit=100, camera_id=camera_id)
    return jsonify({'success': True, 'anomalies': [a.as_dict() for a in anomalies]}), 200


@ai_bp.route('/track/update', methods=['POST'])
def update_tracking():
    """Update object tracker state with current detections."""
    data = request.get_json() or {}
    if 'detections' not in data or not isinstance(data['detections'], list):
        return jsonify({'success': False, 'error': 'Missing detections field'}), 400

    tracked_objects = tracker.update(data['detections'])
    return jsonify({
        'success': True,
        'tracked_objects': [obj.as_dict() for obj in tracked_objects.values()]
    }), 200


@ai_bp.route('/track/summary', methods=['GET'])
def tracker_summary():
    """Return tracking summary statistics."""
    tracked_objects = list(tracker.get_tracked_objects().values())
    summary = tracker_analyzer.get_track_statistics(tracked_objects)
    return jsonify({'success': True, 'summary': summary}), 200
