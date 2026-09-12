# Alert Routes Documentation

This module provides comprehensive alert management, notification handling, escalation workflows, and alert reporting for the AI Surveillance Dashboard.

## Overview

The `alert_routes.py` module handles:
- Alert creation and management
- Alert acknowledgment and resolution
- Alert escalation workflows
- Alert notifications (email, webhooks)
- Alert suppression and scheduling
- Alert recipients and templates management
- Alert statistics and reporting
- Alert queue management

## Database Schema

### alert_notifications Table

```sql
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
```

### alert_escalation Table

```sql
CREATE TABLE IF NOT EXISTS alert_escalation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    escalation_level INTEGER DEFAULT 1,
    escalated_to TEXT,
    escalation_reason TEXT,
    escalated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
)
```

### alert_acknowledgment Table

```sql
CREATE TABLE IF NOT EXISTS alert_acknowledgment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    acknowledged_by INTEGER,
    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_status TEXT DEFAULT 'acknowledged',
    notes TEXT
)
```

### alert_rules Table

```sql
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
```

### alert_templates Table

```sql
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
```

### alert_suppression Table

```sql
CREATE TABLE IF NOT EXISTS alert_suppression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    reason TEXT,
    suppressed_from TIMESTAMP,
    suppressed_until TIMESTAMP,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### alert_recipients Table

```sql
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
```

## API Endpoints

### Base URL
```
/api/alert
```

---

## 1. Create Alert
**Endpoint:** `POST /api/alert/create`

**Description:** Create a new alert and send notifications.

**Request Body:**
```json
{
    "type": "weapon_detected",
    "severity": "critical",
    "message": "Weapon detected in zone A",
    "camera_id": 0,
    "data": {
        "weapon": "knife",
        "confidence": 0.95
    }
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "alert_id": 42,
    "notifications_sent": 3,
    "message": "Alert created successfully"
}
```

**Automatic Features:**
- Checks if alert type is suppressed
- Loads alert template if exists
- Sends notifications to configured recipients
- Triggers escalation if configured

---

## 2. Acknowledge Alert
**Endpoint:** `POST /api/alert/acknowledge/<alert_id>`

**Description:** Mark an alert as acknowledged.

**Parameters:**
- `alert_id` (path): ID of the alert

**Request Body:**
```json
{
    "user_id": 1,
    "notes": "Acknowledged, investigating the issue"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Alert acknowledged successfully"
}
```

---

## 3. Escalate Alert
**Endpoint:** `POST /api/alert/escalate/<alert_id>`

**Description:** Escalate an alert to a higher priority level.

**Parameters:**
- `alert_id` (path): ID of the alert

**Request Body:**
```json
{
    "escalation_level": 2,
    "escalated_to": "supervisor@company.com",
    "reason": "Alert requires immediate management attention"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "escalation_id": 5,
    "message": "Alert escalated successfully"
}
```

---

## 4. Close Alert
**Endpoint:** `POST /api/alert/close/<alert_id>`

**Description:** Close/resolve an alert.

**Parameters:**
- `alert_id` (path): ID of the alert

**Request Body:**
```json
{
    "resolution": "false_alarm",
    "notes": "No actual threat detected after investigation"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Alert closed successfully",
    "resolution": "false_alarm"
}
```

---

## 5. List Alerts
**Endpoint:** `GET /api/alert/list`

**Description:** Retrieve alerts with filtering and pagination.

**Query Parameters:**
- `status` (string, optional): `open`, `acknowledged`, or `closed`
- `severity` (string, optional): `low`, `medium`, `high`, or `critical`
- `alert_type` (string, optional): Filter by alert type
- `limit` (integer, default: 100): Records per page
- `offset` (integer, default: 0): Pagination offset
- `sort_by` (string, default: `created_at`): Sort field
- `sort_order` (string, default: `desc`): `asc` or `desc`

**Response (200 OK):**
```json
{
    "success": true,
    "alerts": [
        {
            "id": 42,
            "camera_id": 0,
            "alert_type": "weapon_detected",
            "severity": "critical",
            "message": "Weapon detected in zone A",
            "is_resolved": 0,
            "created_at": "2024-01-20 14:30:00",
            "resolved_at": null
        }
    ],
    "total": 50,
    "limit": 100,
    "offset": 0
}
```

**Example Requests:**
```bash
# Get open critical alerts
curl "http://localhost:5000/api/alert/list?status=open&severity=critical"

# Get weapon detection alerts with pagination
curl "http://localhost:5000/api/alert/list?alert_type=weapon_detected&limit=20&offset=20"

# Get closed alerts sorted by severity
curl "http://localhost:5000/api/alert/list?status=closed&sort_by=severity&sort_order=asc"
```

---

## 6. Get Alert Detail
**Endpoint:** `GET /api/alert/detail/<alert_id>`

**Description:** Get detailed information about a specific alert.

**Parameters:**
- `alert_id` (path): ID of the alert

**Response (200 OK):**
```json
{
    "success": true,
    "alert": {
        "id": 42,
        "camera_id": 0,
        "alert_type": "weapon_detected",
        "severity": "critical",
        "message": "Weapon detected in zone A",
        "is_resolved": 0,
        "created_at": "2024-01-20 14:30:00"
    },
    "acknowledgments": [
        {
            "id": 1,
            "acknowledged_by": 1,
            "acknowledged_at": "2024-01-20 14:31:00",
            "notes": "Investigating"
        }
    ],
    "escalations": [
        {
            "id": 1,
            "escalation_level": 2,
            "escalated_to": "supervisor@company.com",
            "escalation_reason": "Requires immediate attention",
            "escalated_at": "2024-01-20 14:32:00"
        }
    ],
    "notifications": [
        {
            "id": 1,
            "notification_type": "email",
            "recipient": "user@company.com",
            "status": "sent",
            "sent_at": "2024-01-20 14:30:15"
        }
    ]
}
```

---

## 7. Manage Recipients
**Endpoint:** `GET|POST|PUT|DELETE /api/alert/recipient`

**GET - List all recipients:**
```json
{
    "success": true,
    "recipients": [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john@company.com",
            "phone": "+1-555-0100",
            "webhook_url": "https://api.company.com/alerts",
            "notification_types": "weapon_detected,crowding",
            "priority_level": "critical"
        }
    ],
    "count": 5
}
```

**POST - Create recipient:**
```json
{
    "name": "John Doe",
    "email": "john@company.com",
    "phone": "+1-555-0100",
    "webhook_url": "https://api.company.com/alerts",
    "notification_types": "weapon_detected,crowding",
    "priority_level": "critical"
}
```

**PUT - Update recipient:**
```json
{
    "recipient_id": 1,
    "email": "john.doe@company.com",
    "priority_level": "high"
}
```

**DELETE - Delete recipient:**
```
/api/alert/recipient?recipient_id=1
```

---

## 8. Manage Templates
**Endpoint:** `GET|POST|PUT|DELETE /api/alert/template`

**GET - List all templates:**
```json
{
    "success": true,
    "templates": [
        {
            "id": 1,
            "name": "Weapon Detection",
            "alert_type": "weapon_detected",
            "subject": "CRITICAL: Weapon Detected",
            "message": "A weapon has been detected in zone {zone}. Confidence: {confidence}",
            "severity": "critical"
        }
    ],
    "count": 5
}
```

**POST - Create template:**
```json
{
    "name": "Weapon Detection Alert",
    "alert_type": "weapon_detected",
    "subject": "CRITICAL: Weapon Detected",
    "message": "A weapon (confidence: {confidence}) has been detected. Immediate action required!",
    "severity": "critical"
}
```

**PUT - Update template:**
```json
{
    "template_id": 1,
    "message": "Updated message template",
    "severity": "high"
}
```

**DELETE - Delete template:**
```
/api/alert/template?template_id=1
```

---

## 9. Suppress Alerts
**Endpoint:** `POST /api/alert/suppress`

**Description:** Temporarily suppress alerts of a specific type.

**Request Body:**
```json
{
    "alert_type": "weapon_detected",
    "duration_minutes": 60,
    "reason": "Maintenance window - expected detections"
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "suppression_id": 3,
    "suppressed_until": "2024-01-20 15:30:00",
    "message": "Alerts for weapon_detected suppressed for 60 minutes"
}
```

---

## 10. Get Alert Statistics
**Endpoint:** `GET /api/alert/statistics`

**Description:** Get aggregated alert statistics.

**Query Parameters:**
- `hours` (integer, default: 24): Time period in hours

**Response (200 OK):**
```json
{
    "success": true,
    "stats": {
        "total_alerts": 150,
        "open_alerts": 25,
        "closed_alerts": 125,
        "acknowledged_alerts": 80,
        "by_severity": {
            "critical": 15,
            "high": 35,
            "medium": 80,
            "low": 20
        },
        "by_type": {
            "weapon_detected": 15,
            "crowding": 50,
            "suspicious_activity": 85
        },
        "time_period_hours": 24
    }
}
```

---

## 11. Get Queue Status
**Endpoint:** `GET /api/alert/queue/status`

**Description:** Get current alert queue status.

**Response (200 OK):**
```json
{
    "success": true,
    "queue": {
        "total_in_queue": 100,
        "active_alerts": 25,
        "acknowledged_count": 80,
        "pending_escalations": 5
    }
}
```

---

## Alert Severity Levels

- **critical**: Requires immediate action (weapon detection, security threat)
- **high**: Urgent, should be addressed soon (multiple intrusions, coordinated activity)
- **medium**: Standard alert (unusual detections, minor violations)
- **low**: Informational (routine detections, system status)

---

## Usage Examples

### JavaScript (Frontend)

#### Create alert
```javascript
async function createAlert(alertType, severity) {
    const response = await fetch('/api/alert/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: alertType,
            severity: severity,
            message: `${alertType} detected`,
            camera_id: 0,
            data: { timestamp: new Date().toISOString() }
        })
    });
    
    const data = await response.json();
    if (data.success) {
        console.log(`Alert ${data.alert_id} created, ${data.notifications_sent} notifications sent`);
    }
}
```

#### Acknowledge alert
```javascript
async function acknowledgeAlert(alertId, userId) {
    const response = await fetch(`/api/alert/acknowledge/${alertId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            notes: 'Acknowledged by operator'
        })
    });
    
    const data = await response.json();
    console.log('Alert acknowledged:', data.message);
}
```

#### Escalate alert
```javascript
async function escalateAlert(alertId, escalationLevel) {
    const response = await fetch(`/api/alert/escalate/${alertId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            escalation_level: escalationLevel,
            escalated_to: 'supervisor@company.com',
            reason: 'Requires management review'
        })
    });
    
    const data = await response.json();
    console.log('Alert escalated:', data.escalation_id);
}
```

#### Get alert statistics
```javascript
async function getAlertStats() {
    const response = await fetch('/api/alert/statistics?hours=24');
    const data = await response.json();
    
    console.log('Total alerts:', data.stats.total_alerts);
    console.log('Open alerts:', data.stats.open_alerts);
    console.log('Critical alerts:', data.stats.by_severity.critical);
}
```

#### Suppress alerts
```javascript
async function suppressAlerts(alertType, duration) {
    const response = await fetch('/api/alert/suppress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            alert_type: alertType,
            duration_minutes: duration,
            reason: 'Maintenance window'
        })
    });
    
    const data = await response.json();
    console.log('Alerts suppressed until:', data.suppressed_until);
}
```

#### List alerts
```javascript
async function listOpenAlerts() {
    const response = await fetch('/api/alert/list?status=open&limit=20');
    const data = await response.json();
    
    data.alerts.forEach(alert => {
        console.log(`[${alert.severity}] ${alert.alert_type}: ${alert.message}`);
    });
}
```

---

## Integration Workflow

### Typical alert lifecycle:

1. **Create Alert** → `POST /api/alert/create`
   - Detection system identifies anomaly
   - Alert template loads (if exists)
   - Notifications sent to recipients

2. **Acknowledge Alert** → `POST /api/alert/acknowledge/<id>`
   - Operator acknowledges receipt
   - Adds investigation notes

3. **Escalate if Needed** → `POST /api/alert/escalate/<id>`
   - Alert upgraded to higher priority
   - Management notified

4. **Resolve Alert** → `POST /api/alert/close/<id>`
   - Issue resolved or determined false alarm
   - Alert status updated

5. **Analyze Statistics** → `GET /api/alert/statistics`
   - Generate reports
   - Track patterns
   - Improve alert rules

---

## Features Highlights

✅ **Multi-channel Notifications**: Email, Webhooks  
✅ **Alert Suppression**: Prevent spam during maintenance  
✅ **Escalation Workflows**: Route to appropriate personnel  
✅ **Flexible Templating**: Customizable alert messages  
✅ **Recipient Management**: Dynamic notification routing  
✅ **Comprehensive Statistics**: Analytics and reporting  
✅ **Queue Management**: Monitor alert processing  
✅ **Thread-safe Operations**: Production-ready concurrency  

---

## Best Practices

1. **Configure Recipients**: Set up email/webhook recipients for each alert type
2. **Use Templates**: Create templates for consistent messaging
3. **Set Thresholds**: Configure alert rules to reduce false positives
4. **Regular Review**: Monitor statistics to optimize alert effectiveness
5. **Suppress Appropriately**: Use suppression for known maintenance windows
6. **Acknowledge Promptly**: Keep SLA for alert acknowledgment
7. **Escalate Timely**: Don't delay escalation of critical alerts

---

## Security Considerations

- Validate all incoming alert data
- Implement rate limiting to prevent alert flooding
- Require authentication for management operations
- Log all alert acknowledgments and escalations
- Encrypt webhook URLs and sensitive data
- Use HTTPS for all external notifications
