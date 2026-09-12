-- Project database schema for theft-detection backend
-- Creates all tables used by authentication, camera persistence, detection, alerts, and notifications.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

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
);

CREATE TABLE IF NOT EXISTS camera_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER,
    user_id INTEGER,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    recording_file TEXT,
    detections_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

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
);

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
);

CREATE TABLE IF NOT EXISTS alert_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER,
    alert_type TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    threshold REAL,
    cooldown_minutes INTEGER DEFAULT 5,
    user_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER,
    anomaly_type TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'low',
    data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER
);

CREATE TABLE IF NOT EXISTS alert_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    notification_type TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    sent_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_escalation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    escalation_level INTEGER DEFAULT 1,
    escalated_to TEXT,
    escalation_reason TEXT,
    escalated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_acknowledgment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    acknowledged_by INTEGER,
    acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_status TEXT DEFAULT 'acknowledged',
    notes TEXT
);

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
);

CREATE TABLE IF NOT EXISTS alert_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    alert_type TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_suppression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    reason TEXT,
    suppressed_from TIMESTAMP,
    suppressed_until TIMESTAMP,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
);
