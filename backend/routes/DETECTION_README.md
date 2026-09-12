# Detection Routes Documentation

This module provides AI detection processing, alert management, anomaly detection, and detection event tracking for the AI Surveillance Dashboard.

## Overview

The `detection_routes.py` module handles:
- Detection result processing and validation
- Automated alert generation
- Anomaly detection (crowding, weapons, suspicious activity)
- Detection event storage and retrieval
- Alert management and configuration
- Detection statistics and analytics
- Target class management for different detection modes

## Database Schema

### detection_events Table

```sql
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
```

### detection_alerts Table

```sql
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
```

### alert_config Table

```sql
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
```

### anomalies Table

```sql
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
```

## API Endpoints

### Base URL
```
/api/detection
```

---

## 1. Process Detection
**Endpoint:** `POST /api/detection/process`

**Description:** Process detection results and generate alerts if needed.

**Request Body:**
```json
{
    "camera_id": 0,
    "detections": [
        {
            "class": "person",
            "confidence": 0.95,
            "bbox": {
                "x": 0.2,
                "y": 0.3,
                "width": 0.1,
                "height": 0.2
            }
        },
        {
            "class": "knife",
            "confidence": 0.88,
            "bbox": {
                "x": 0.3,
                "y": 0.4,
                "width": 0.05,
                "height": 0.15
            }
        }
    ],
    "frame": "base64_encoded_image",
    "user_id": 1
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "event_id": 42,
    "detections_count": 2,
    "alerts": [5],
    "anomalies": [
        {
            "type": "weapon_detected",
            "severity": "critical",
            "description": "Weapon detected: knife (confidence: 0.88)",
            "weapon": "knife",
            "confidence": 0.88
        }
    ],
    "message": "Detection processed successfully"
}
```

**Automatic Alert Triggers:**
- Weapon detection → Critical alert
- Crowding (>10 people) → Medium alert
- Suspicious activity → High alert

---

## 2. Validate Detection
**Endpoint:** `POST /api/detection/validate`

**Description:** Validate and filter detection results.

**Request Body:**
```json
{
    "detections": [
        {
            "class": "person",
            "confidence": 0.95,
            "bbox": {...}
        }
    ],
    "target_classes": ["person", "car"],
    "min_confidence": 0.5
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "valid_detections": [
        {
            "class": "person",
            "confidence": 0.95,
            "bbox": {...}
        }
    ],
    "filtered_count": 0,
    "total_detections": 1
}
```

---

## 3. Get Target Classes
**Endpoint:** `GET /api/detection/target-classes/<mode>`

**Description:** Get detection classes for a specific mode.

**Parameters:**
- `mode`: Detection mode - `person`, `weapon`, or `object`

**Response (200 OK):**
```json
{
    "success": true,
    "mode": "weapon",
    "classes": ["knife", "baseball bat", "gun"],
    "count": 3
}
```

**Available Modes:**
- `person` → ["person"]
- `weapon` → ["knife", "baseball bat", "gun"]
- `object` → ["car", "bicycle", "motorcycle", "truck", "bus"]

---

## 4. Get Alerts
**Endpoint:** `GET /api/detection/alerts`

**Description:** Retrieve detection alerts with optional filtering.

**Query Parameters:**
- `camera_id` (integer, optional): Filter by camera ID
- `alert_type` (string, optional): Filter by alert type
- `severity` (string, optional): `low`, `medium`, `high`, or `critical`
- `is_resolved` (integer, optional): 0 for unresolved, 1 for resolved
- `limit` (integer, default: 50): Maximum records to return
- `hours` (integer, default: 24): Get alerts from last N hours

**Response (200 OK):**
```json
{
    "success": true,
    "alerts": [
        {
            "id": 5,
            "camera_id": 0,
            "alert_type": "weapon_detected",
            "severity": "critical",
            "detection_class": "knife",
            "confidence": 0.88,
            "message": "Weapon detected: knife (confidence: 0.88)",
            "image_path": "path/to/image.jpg",
            "is_resolved": 0,
            "created_at": "2024-01-20 14:30:00",
            "resolved_at": null
        }
    ],
    "count": 1
}
```

**Example Requests:**
```bash
# Get unresolved critical alerts
curl "http://localhost:5000/api/detection/alerts?severity=critical&is_resolved=0"

# Get weapon detection alerts from last 7 days
curl "http://localhost:5000/api/detection/alerts?alert_type=weapon_detected&hours=168"

# Get alerts for camera 0
curl "http://localhost:5000/api/detection/alerts?camera_id=0&limit=100"
```

---

## 5. Resolve Alert
**Endpoint:** `POST /api/detection/alerts/<alert_id>/resolve`

**Description:** Mark an alert as resolved.

**Parameters:**
- `alert_id` (path): ID of the alert to resolve

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Alert resolved successfully"
}
```

---

## 6. Get Anomalies
**Endpoint:** `GET /api/detection/anomalies`

**Description:** Retrieve detected anomalies.

**Query Parameters:**
- `camera_id` (integer, optional): Filter by camera ID
- `anomaly_type` (string, optional): `weapon_detected`, `crowding`, `suspicious_activity`
- `severity` (string, optional): `low`, `medium`, `high`, `critical`
- `limit` (integer, default: 50): Maximum records to return
- `hours` (integer, default: 24): Get anomalies from last N hours

**Response (200 OK):**
```json
{
    "success": true,
    "anomalies": [
        {
            "id": 1,
            "camera_id": 0,
            "anomaly_type": "weapon_detected",
            "description": "Weapon detected: knife (confidence: 0.88)",
            "severity": "critical",
            "data": {
                "weapon": "knife",
                "confidence": 0.88
            },
            "timestamp": "2024-01-20 14:30:00"
        },
        {
            "id": 2,
            "camera_id": 0,
            "anomaly_type": "crowding",
            "description": "Crowding detected: 15 people",
            "severity": "medium",
            "data": {
                "count": 15
            },
            "timestamp": "2024-01-20 14:31:00"
        }
    ],
    "count": 2
}
```

---

## 7. Get Detection Statistics
**Endpoint:** `GET /api/detection/statistics`

**Description:** Get aggregated detection statistics.

**Query Parameters:**
- `camera_id` (integer, optional): Filter by camera ID
- `hours` (integer, default: 24): Time period in hours

**Response (200 OK):**
```json
{
    "success": true,
    "stats": {
        "total_events": 100,
        "unique_classes": 5,
        "alert_count": 10,
        "critical_alerts": 2,
        "high_alerts": 3,
        "most_detected_class": "person",
        "avg_confidence": 0.876,
        "detection_classes": {
            "person": 60,
            "car": 25,
            "bicycle": 10,
            "dog": 5
        },
        "alert_severities": {
            "critical": 2,
            "high": 3,
            "medium": 5
        },
        "time_period_hours": 24
    }
}
```

---

## 8. Get Detection Events
**Endpoint:** `GET /api/detection/events`

**Description:** Retrieve detection events.

**Query Parameters:**
- `camera_id` (integer, optional): Filter by camera ID
- `event_type` (string, optional): `single` or `multi`
- `limit` (integer, default: 50): Maximum records to return
- `hours` (integer, default: 24): Get events from last N hours

**Response (200 OK):**
```json
{
    "success": true,
    "events": [
        {
            "id": 42,
            "camera_id": 0,
            "detection_class": "person,car",
            "confidence": 0.95,
            "count": 2,
            "bbox_data": [
                {"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.2},
                {"x": 0.5, "y": 0.4, "width": 0.2, "height": 0.3}
            ],
            "event_type": "multi",
            "timestamp": "2024-01-20 14:30:00"
        }
    ],
    "count": 1
}
```

---

## 9. Get Alert Configuration
**Endpoint:** `GET /api/detection/alert-config/<camera_id>`

**Description:** Get alert configuration for a camera.

**Parameters:**
- `camera_id` (path): ID of the camera

**Response (200 OK):**
```json
{
    "success": true,
    "config": [
        {
            "id": 1,
            "alert_type": "weapon_detected",
            "enabled": true,
            "threshold": 0.8,
            "cooldown_minutes": 5
        },
        {
            "id": 2,
            "alert_type": "crowding",
            "enabled": true,
            "threshold": 10,
            "cooldown_minutes": 10
        }
    ]
}
```

---

## 10. Update Alert Configuration
**Endpoint:** `POST /api/detection/alert-config/<camera_id>`

**Description:** Update alert configuration for a camera.

**Parameters:**
- `camera_id` (path): ID of the camera

**Request Body:**
```json
{
    "alert_type": "weapon_detected",
    "enabled": true,
    "threshold": 0.85,
    "cooldown_minutes": 5
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Alert configuration updated"
}
```

---

## 11. Get Detection System Health
**Endpoint:** `GET /api/detection/health`

**Description:** Get detection system health status.

**Response (200 OK):**
```json
{
    "success": true,
    "status": "healthy",
    "recent_events": 15,
    "recent_alerts": 2,
    "average_confidence": 0.876
}
```

---

## Anomaly Types

### weapon_detected
Triggered when weapon classes are detected with high confidence.
- **Severity:** Critical
- **Classes:** knife, gun, baseball bat
- **Cooldown:** 5 minutes (configurable)

### crowding
Triggered when more than 10 people are detected in a single frame.
- **Severity:** Medium
- **Threshold:** > 10 people
- **Cooldown:** 10 minutes (configurable)

### suspicious_activity
Triggered by unusual detection patterns.
- **Severity:** Variable
- **Cooldown:** 5 minutes (configurable)

---

## Alert Severity Levels

- **critical**: Requires immediate action (weapon detection, intrusion)
- **high**: Should be investigated soon (crowding, multiple suspicious activities)
- **medium**: Standard alert (unusual activity patterns)
- **low**: Informational (standard detections)

---

## Usage Examples

### JavaScript (Frontend)

#### Process detection from model
```javascript
async function sendDetection(detections, frameCanvas) {
    const frameData = frameCanvas.toDataURL('image/jpeg').split(',')[1];
    
    const response = await fetch('/api/detection/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            camera_id: 0,
            detections: detections,
            frame: frameData,
            user_id: 1
        })
    });
    
    const data = await response.json();
    if (data.anomalies.length > 0) {
        showAlert(data.anomalies[0]);
    }
}
```

#### Get alerts
```javascript
async function checkAlerts() {
    const response = await fetch('/api/detection/alerts?is_resolved=0&severity=critical');
    const data = await response.json();
    console.log('Unresolved critical alerts:', data.alerts);
}
```

#### Resolve alert
```javascript
async function acknowledgeAlert(alertId) {
    const response = await fetch(`/api/detection/alerts/${alertId}/resolve`, {
        method: 'POST'
    });
    const data = await response.json();
    console.log('Alert resolved:', data);
}
```

#### Get statistics
```javascript
async function getStats() {
    const response = await fetch('/api/detection/statistics?hours=24');
    const data = await response.json();
    console.log('Detection stats:', data.stats);
}
```

#### Configure alerts
```javascript
async function configureWeaponAlert(cameraId) {
    const response = await fetch(`/api/detection/alert-config/${cameraId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            alert_type: 'weapon_detected',
            enabled: true,
            threshold: 0.8,
            cooldown_minutes: 5
        })
    });
    const data = await response.json();
    console.log('Config updated:', data);
}
```

---

## Integration with Detection Pipeline

### Typical workflow:
1. **Run detection** → Use AI model to detect objects
2. **Validate detections** → `POST /api/detection/validate`
3. **Process detections** → `POST /api/detection/process`
4. **Receive alerts** → Automatically generated for anomalies
5. **Check system** → `GET /api/detection/health`
6. **Get statistics** → `GET /api/detection/statistics`
7. **Manage alerts** → `POST /api/detection/alerts/<id>/resolve`
8. **Configure alerts** → `POST /api/detection/alert-config/<camera_id>`

---

## Performance Considerations

- **Alert Cooldown:** Prevents alert spam (5-10 minutes recommended)
- **Event Storage:** Limited to recent events (1000 in-memory queue)
- **Database:** Consider archiving old events periodically
- **Anomaly Detection:** Runs in real-time during detection processing
- **Statistics:** Calculated on-demand; cache for frequently accessed data

---

## Security Notes

- Validate all detection data before processing
- Implement rate limiting on alert endpoints
- Require authentication for configuration changes
- Log all alert resolutions for audit trail
- Use HTTPS in production for sensitive data
