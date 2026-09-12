"""
Utility helper functions for the Flask backend.
Provides common utilities for responses, data formatting, validation, and file operations.
"""

import os
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from flask import jsonify, current_app


def get_project_root() -> str:
    """Get the absolute path to the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_backend_root() -> str:
    """Get the absolute path to the backend directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_response(data: Any = None, message: str = "", status: str = "success",
                  status_code: int = 200, **kwargs) -> tuple:
    """
    Create a standardized JSON response.

    Args:
        data: Response data
        message: Response message
        status: Response status ('success', 'error', 'warning')
        status_code: HTTP status code
        **kwargs: Additional fields to include

    Returns:
        Tuple of (json_response, status_code)
    """
    response = {
        'status': status,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    if data is not None:
        response['data'] = data

    response.update(kwargs)

    return jsonify(response), status_code


def success_response(data: Any = None, message: str = "Success", **kwargs) -> tuple:
    """Create a success response."""
    return make_response(data, message, "success", 200, **kwargs)


def error_response(message: str = "Error", status_code: int = 400, **kwargs) -> tuple:
    """Create an error response."""
    return make_response(None, message, "error", status_code, **kwargs)


def format_datetime(dt: Union[str, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object or ISO string to a readable format.

    Args:
        dt: Datetime object or ISO string
        format_str: strftime format string

    Returns:
        Formatted datetime string
    """
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt  # Return as-is if parsing fails

    if isinstance(dt, datetime):
        return dt.strftime(format_str)

    return str(dt)


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string by removing dangerous characters and trimming.

    Args:
        text: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not text:
        return ""

    # Remove null bytes and other dangerous characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    # Trim whitespace
    text = text.strip()

    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email string to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def paginate_results(results: List[Dict], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """
    Paginate a list of results.

    Args:
        results: List of result dictionaries
        page: Page number (1-based)
        per_page: Results per page

    Returns:
        Dictionary with paginated results and metadata
    """
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_results = results[start:end]

    return {
        'results': paginated_results,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_next': end < total,
            'has_prev': page > 1
        }
    }


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely serialize data to JSON string.

    Args:
        data: Data to serialize
        default: Default string if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return default


def ensure_directory(path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path
    """
    os.makedirs(path, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.

    Args:
        filename: Filename

    Returns:
        File extension (lowercase, without dot)
    """
    return os.path.splitext(filename)[1].lower().lstrip('.')


def is_allowed_file(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Check if a file has an allowed extension.

    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions (without dots)

    Returns:
        True if allowed, False otherwise
    """
    return get_file_extension(filename) in [ext.lower() for ext in allowed_extensions]


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a unique filename with timestamp.

    Args:
        original_filename: Original filename
        prefix: Optional prefix

    Returns:
        Unique filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    name, ext = os.path.splitext(original_filename)
    return f"{prefix}{timestamp}_{name}{ext}"


def clamp(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """
    Clamp a value between min and max.

    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value

    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def deep_merge_dicts(base: Dict, update: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        update: Dictionary with updates

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result
