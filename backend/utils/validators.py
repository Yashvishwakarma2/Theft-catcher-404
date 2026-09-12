"""
Validation utilities for the Flask backend.
Provides reusable validators for common input validation scenarios.
"""

import re
from typing import Any, List, Optional, Union, Tuple
from datetime import datetime


class ValidationError(Exception):
    """Exception raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


# ============================================================================
# Username & Password Validators
# ============================================================================

def validate_username(username: str, min_length: int = 3, max_length: int = 50) -> Tuple[bool, str]:
    """
    Validate a username.

    Args:
        username: Username to validate
        min_length: Minimum length
        max_length: Maximum length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    username = str(username).strip()

    if len(username) < min_length:
        return False, f"Username must be at least {min_length} characters long"

    if len(username) > max_length:
        return False, f"Username must not exceed {max_length} characters"

    # Allow alphanumeric, underscore, and hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscore, and hyphen"

    return True, ""


def validate_password(password: str, min_length: int = 6, max_length: int = 128) -> Tuple[bool, str]:
    """
    Validate a password.

    Args:
        password: Password to validate
        min_length: Minimum length
        max_length: Maximum length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    password = str(password)

    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"

    if len(password) > max_length:
        return False, f"Password must not exceed {max_length} characters"

    return True, ""


# ============================================================================
# Email & Contact Validators
# ============================================================================

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate an email address.

    Args:
        email: Email to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return True, ""  # Email is optional

    email = str(email).strip()

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email address"

    if len(email) > 254:
        return False, "Email address is too long"

    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Validate a phone number (basic format).

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return True, ""  # Phone is optional

    phone = str(phone).strip()

    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)

    # Should be 10-15 digits
    if not re.match(r'^\d{10,15}$', cleaned):
        return False, "Invalid phone number format"

    return True, ""


# ============================================================================
# String & Text Validators
# ============================================================================

def validate_string_length(text: str, min_length: int = 0, max_length: int = 255,
                          field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate string length.

    Args:
        text: Text to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        if min_length > 0:
            return False, f"{field_name} is required"
        return True, ""

    text = str(text).strip()

    if len(text) < min_length:
        return False, f"{field_name} must be at least {min_length} characters long"

    if len(text) > max_length:
        return False, f"{field_name} must not exceed {max_length} characters"

    return True, ""


def validate_choice(value: Any, allowed_values: List[Any], field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate that value is one of allowed choices.

    Args:
        value: Value to validate
        allowed_values: List of allowed values
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"

    if value not in allowed_values:
        return False, f"{field_name} must be one of: {', '.join(str(v) for v in allowed_values)}"

    return True, ""


# ============================================================================
# Numeric Validators
# ============================================================================

def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None,
                    field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate an integer value.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"

    try:
        int_value = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name} must be an integer"

    if min_value is not None and int_value < min_value:
        return False, f"{field_name} must be at least {min_value}"

    if max_value is not None and int_value > max_value:
        return False, f"{field_name} must not exceed {max_value}"

    return True, ""


def validate_float(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None,
                  field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate a float value.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Field name for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"

    try:
        float_value = float(value)
    except (ValueError, TypeError):
        return False, f"{field_name} must be a number"

    if min_value is not None and float_value < min_value:
        return False, f"{field_name} must be at least {min_value}"

    if max_value is not None and float_value > max_value:
        return False, f"{field_name} must not exceed {max_value}"

    return True, ""


def validate_confidence(confidence: Union[int, float]) -> Tuple[bool, str]:
    """
    Validate a confidence score (0.0 - 1.0).

    Args:
        confidence: Confidence value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_float(confidence, 0.0, 1.0, "Confidence")


# ============================================================================
# Detection & Alert Validators
# ============================================================================

VALID_SEVERITY_LEVELS = ['low', 'medium', 'high', 'critical']
VALID_ALERT_TYPES = ['weapon', 'theft', 'intrusion', 'suspicious', 'anomaly', 'custom']
VALID_DETECTION_CLASSES = ['person', 'weapon', 'vehicle', 'object', 'unknown']


def validate_severity(severity: str) -> Tuple[bool, str]:
    """
    Validate alert severity level.

    Args:
        severity: Severity level to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_choice(severity, VALID_SEVERITY_LEVELS, "Severity")


def validate_alert_type(alert_type: str) -> Tuple[bool, str]:
    """
    Validate alert type.

    Args:
        alert_type: Alert type to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_choice(alert_type, VALID_ALERT_TYPES, "Alert type")


def validate_detection_class(detection_class: str) -> Tuple[bool, str]:
    """
    Validate detection class.

    Args:
        detection_class: Detection class to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_choice(detection_class, VALID_DETECTION_CLASSES, "Detection class")


# ============================================================================
# Required Fields Validator
# ============================================================================

def validate_required_fields(data: dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all required fields are present and not empty.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing = []

    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing.append(field)

    return len(missing) == 0, missing


# ============================================================================
# Batch Validation
# ============================================================================

def validate_request_data(data: dict, schema: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate request data against a schema.

    Schema format:
    {
        'field_name': {
            'required': bool,
            'type': 'string' | 'integer' | 'float' | 'email' | 'choice',
            'min_length': int (for strings),
            'max_length': int (for strings),
            'min_value': number,
            'max_value': number,
            'choices': list (for choice type)
        }
    }

    Args:
        data: Request data to validate
        schema: Validation schema

    Returns:
        Tuple of (is_valid, error_message)
    """
    for field, rules in schema.items():
        value = data.get(field)

        # Check required
        if rules.get('required', False):
            if value is None or value == "":
                return False, f"{field} is required"

        if value is None or value == "":
            continue

        # Type validation
        field_type = rules.get('type', 'string')

        if field_type == 'email':
            is_valid, error = validate_email(value)
            if not is_valid:
                return False, f"{field}: {error}"

        elif field_type == 'integer':
            is_valid, error = validate_integer(
                value,
                rules.get('min_value'),
                rules.get('max_value'),
                field
            )
            if not is_valid:
                return False, error

        elif field_type == 'float':
            is_valid, error = validate_float(
                value,
                rules.get('min_value'),
                rules.get('max_value'),
                field
            )
            if not is_valid:
                return False, error

        elif field_type == 'choice':
            choices = rules.get('choices', [])
            is_valid, error = validate_choice(value, choices, field)
            if not is_valid:
                return False, error

        elif field_type == 'string':
            is_valid, error = validate_string_length(
                str(value),
                rules.get('min_length', 0),
                rules.get('max_length', 255),
                field
            )
            if not is_valid:
                return False, error

    return True, None


# ============================================================================
# Timestamp Validators
# ============================================================================

def validate_iso_datetime(dt_string: str) -> Tuple[bool, str]:
    """
    Validate ISO 8601 datetime string.

    Args:
        dt_string: DateTime string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not dt_string:
        return False, "DateTime is required"

    try:
        # Try parsing ISO format
        datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return True, ""
    except ValueError:
        return False, "Invalid datetime format. Use ISO 8601 format (e.g., 2024-01-15T10:30:00Z)"


# ============================================================================
# URL & File Validators
# ============================================================================

def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate a URL.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return True, ""  # URL is optional

    url = str(url).strip()

    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url):
        return False, "Invalid URL format"

    return True, ""


def validate_filename(filename: str) -> Tuple[bool, str]:
    """
    Validate a filename.

    Args:
        filename: Filename to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"

    filename = str(filename).strip()

    # Disallow path separators and special characters
    if '/' in filename or '\\' in filename or '..' in filename:
        return False, "Invalid filename: path separators not allowed"

    # Allow alphanumeric, dots, hyphens, underscores
    if not re.match(r'^[\w\-. ]+$', filename):
        return False, "Filename contains invalid characters"

    return True, ""
