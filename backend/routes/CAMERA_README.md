# Camera Routes Documentation

This module provides comprehensive camera management, video streaming, recording, and detection history capabilities for the AI Surveillance Dashboard.

## Overview

The `camera_routes.py` module handles:
- Camera detection and initialization
- Real-time video streaming (Motion JPEG)
- Single frame capture
- Video recording
- Detection history storage and retrieval
- Camera settings management
- Detection statistics

## Database Schema

### detection_history Table

```sql
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
```

### camera_sessions Table

```sql
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
```

## API Endpoints

### Base URL
```
/api/camera
```

---

## 1. List Available Cameras
**Endpoint:** `GET /api/camera/list`

**Description:** Scan for and list all available cameras on the system.

**Response (200 OK):**
```json
{
    "success": true,
    "cameras": [
        {
            "id": 0,
            "name": "Camera 0",
            "available": true,
            "resolution": {
                "width": 640,
                "height": 480
            },
            "fps": 30
        },
        {
            "id": 1,
            "name": "Camera 1",
            "available": true,
            "resolution": {
                "width": 1920,
                "height": 1080
            },
            "fps": 30
        }
    ],
    "count": 2
}
```

---

## 2. Initialize Camera
**Endpoint:** `POST /api/camera/initialize/<camera_id>`

**Description:** Initialize a camera with specified settings.

**Parameters:**
- `camera_id` (path): ID of the camera to initialize

**Request Body:**
```json
{
    "width": 640,
    "height": 480,
    "fps": 30
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "camera_id": 0,
    "message": "Camera initialized successfully",
    "settings": {
        "width": 640,
        "height": 480,
        "fps": 30
    }
}
```

---

## 3. Release Camera
**Endpoint:** `POST /api/camera/release/<camera_id>`

**Description:** Release and close a camera resource.

**Parameters:**
- `camera_id` (path): ID of the camera to release

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Camera released successfully"
}
```

---

## 4. Get Single Frame
**Endpoint:** `GET /api/camera/frame/<camera_id>`

**Description:** Get a single frame from the specified camera as JPEG image.

**Parameters:**
- `camera_id` (path): ID of the camera

**Response:** JPEG image data (binary)

**Headers:** `Content-Type: image/jpeg`

---

## 5. Stream Video (Motion JPEG)
**Endpoint:** `GET /api/camera/stream/<camera_id>`

**Description:** Get continuous video stream as Motion JPEG format.

**Parameters:**
- `camera_id` (path): ID of the camera

**Response:** Motion JPEG stream with continuous frames

**Headers:** `Content-Type: multipart/x-mixed-replace; boundary=frame`

**Usage in HTML:**
```html
<img src="/api/camera/stream/0" alt="Camera Stream" style="width: 100%;">
```

---

## 6. Save Detection Record
**Endpoint:** `POST /api/camera/save-detection`

**Description:** Save a detection record to the database.

**Request Body:**
```json
{
    "camera_id": 0,
    "class": "person",
    "confidence": 0.95,
    "bbox": {
        "x": 100,
        "y": 150,
        "width": 50,
        "height": 100
    },
    "image_path": "path/to/saved/image.jpg",
    "user_id": 1
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "detection_id": 42,
    "message": "Detection saved successfully"
}
```

---

## 7. Get Detection History
**Endpoint:** `GET /api/camera/history`

**Description:** Retrieve detection history with optional filtering.

**Query Parameters:**
- `limit` (integer, default: 100): Maximum number of records to return
- `camera_id` (integer, optional): Filter by camera ID
- `class` (string, optional): Filter by detection class (e.g., "person", "car")
- `hours` (integer, default: 24): Get records from last N hours

**Response (200 OK):**
```json
{
    "success": true,
    "detections": [
        {
            "id": 42,
            "camera_id": 0,
            "class": "person",
            "confidence": 0.95,
            "bbox": {
                "x": 100,
                "y": 150,
                "width": 50,
                "height": 100
            },
            "timestamp": "2024-01-20 14:30:00",
            "image_path": "path/to/image.jpg"
        },
        {
            "id": 41,
            "camera_id": 0,
            "class": "car",
            "confidence": 0.88,
            "bbox": {
                "x": 200,
                "y": 250,
                "width": 150,
                "height": 120
            },
            "timestamp": "2024-01-20 14:29:50",
            "image_path": null
        }
    ],
    "count": 2
}
```

**Example Requests:**
```bash
# Get last 24 hours of detections (default)
curl "http://localhost:5000/api/camera/history"

# Get last 7 days of detections for camera 0
curl "http://localhost:5000/api/camera/history?camera_id=0&hours=168&limit=200"

# Get only person detections
curl "http://localhost:5000/api/camera/history?class=person"

# Get detections from last 12 hours, limit to 50 records
curl "http://localhost:5000/api/camera/history?hours=12&limit=50"
```

---

## 8. Get Detection Statistics
**Endpoint:** `GET /api/camera/history/stats`

**Description:** Get aggregated statistics about detections.

**Query Parameters:**
- `hours` (integer, default: 24): Time period in hours
- `camera_id` (integer, optional): Filter by camera ID

**Response (200 OK):**
```json
{
    "success": true,
    "stats": {
        "total_detections": 42,
        "unique_classes": 5,
        "classes": {
            "person": 25,
            "car": 12,
            "dog": 3,
            "bicycle": 1,
            "motorcycle": 1
        },
        "avg_confidence": 0.876,
        "time_period_hours": 24
    }
}
```

---

## 9. Get Camera Status
**Endpoint:** `GET /api/camera/status`

**Description:** Get current status of all cameras.

**Response (200 OK):**
```json
{
    "success": true,
    "active_camera": 0,
    "cameras_initialized": [0, 1],
    "recording": false,
    "status": "running"
}
```

---

## 10. Get Camera Settings
**Endpoint:** `GET /api/camera/settings/<camera_id>`

**Description:** Get current settings of a camera.

**Parameters:**
- `camera_id` (path): ID of the camera

**Response (200 OK):**
```json
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
```

---

## 11. Update Camera Settings
**Endpoint:** `POST /api/camera/settings/<camera_id>`

**Description:** Update settings of a camera.

**Parameters:**
- `camera_id` (path): ID of the camera

**Request Body:**
```json
{
    "brightness": 10,
    "contrast": 5,
    "saturation": 70,
    "fps": 30
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Settings updated successfully"
}
```

---

## 12. Start Recording
**Endpoint:** `POST /api/camera/record/start`

**Description:** Start video recording from a camera.

**Request Body:**
```json
{
    "camera_id": 0,
    "filename": "surveillance_2024-01-20.mp4"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Recording started",
    "filename": "surveillance_2024-01-20.mp4",
    "path": "backend/recordings/surveillance_2024-01-20.mp4"
}
```

---

## 13. Stop Recording
**Endpoint:** `POST /api/camera/record/stop`

**Description:** Stop the current video recording.

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Recording stopped"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
    "success": false,
    "error": "Camera 0 not initialized"
}
```

### 500 Internal Server Error
```json
{
    "success": false,
    "error": "Failed to capture frame: [error details]"
}
```

---

## Usage Examples

### JavaScript (Frontend)

#### List available cameras
```javascript
const response = await fetch('/api/camera/list');
const data = await response.json();
console.log('Available cameras:', data.cameras);
```

#### Initialize camera
```javascript
const response = await fetch('/api/camera/initialize/0', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        width: 640,
        height: 480,
        fps: 30
    })
});
const data = await response.json();
console.log('Camera initialized:', data);
```

#### Display video stream
```javascript
// In HTML
<img id="stream" src="/api/camera/stream/0" alt="Camera Stream">

// The stream will automatically display continuous frames
```

#### Get detection history
```javascript
const response = await fetch('/api/camera/history?camera_id=0&hours=24&limit=100');
const data = await response.json();
console.log('Detections:', data.detections);
```

#### Save detection
```javascript
const response = await fetch('/api/camera/save-detection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        camera_id: 0,
        class: 'person',
        confidence: 0.95,
        bbox: {
            x: 100,
            y: 150,
            width: 50,
            height: 100
        },
        user_id: 1
    })
});
const data = await response.json();
console.log('Detection saved:', data.detection_id);
```

#### Start recording
```javascript
const response = await fetch('/api/camera/record/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        camera_id: 0,
        filename: 'surveillance.mp4'
    })
});
const data = await response.json();
console.log('Recording started:', data);
```

#### Stop recording
```javascript
const response = await fetch('/api/camera/record/stop', {
    method: 'POST'
});
const data = await response.json();
console.log('Recording stopped:', data);
```

#### Get statistics
```javascript
const response = await fetch('/api/camera/history/stats?hours=24&camera_id=0');
const data = await response.json();
console.log('Statistics:', data.stats);
```

---

## Integration with Detection Pipeline

### Typical workflow:
1. **Initialize camera** → `POST /api/camera/initialize/0`
2. **Get stream** → `GET /api/camera/stream/0`
3. **Run detection on frames** → Use AI model on frontend/backend
4. **Save detections** → `POST /api/camera/save-detection`
5. **Optionally start recording** → `POST /api/camera/record/start`
6. **View history** → `GET /api/camera/history`
7. **Check statistics** → `GET /api/camera/history/stats`
8. **Stop recording** → `POST /api/camera/record/stop`
9. **Release camera** → `POST /api/camera/release/0`

---

## Performance Considerations

- **Streaming**: Motion JPEG is real-time but can be bandwidth intensive
- **Detection History**: Stored in SQLite; consider archiving old records
- **Video Recording**: MP4 codec is used; requires sufficient disk space
- **Concurrent Cameras**: Use threading/async for multiple cameras
- **Frame Rate**: Adjust based on detection accuracy vs. CPU load

---

## Security Notes

- Validate camera IDs to prevent unauthorized access
- Implement authentication middleware for sensitive endpoints
- Limit history query results to prevent large data transfers
- Use HTTPS in production for video stream security
- Implement access control based on user roles
