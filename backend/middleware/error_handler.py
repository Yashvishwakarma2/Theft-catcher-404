"""
Error handling middleware for the Flask backend.
Provides centralized error handling for HTTP errors and custom exceptions.
"""

from flask import jsonify, current_app, request
from werkzeug.exceptions import HTTPException
import traceback
import logging


class APIError(Exception):
    """Base class for API-specific errors."""

    def __init__(self, message: str, status_code: int = 400, payload: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}


class AuthenticationError(APIError):
    """Error for authentication failures."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)


class AuthorizationError(APIError):
    """Error for authorization failures."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, 403)


class ValidationError(APIError):
    """Error for input validation failures."""

    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, 400)


class DatabaseError(APIError):
    """Error for database operation failures."""

    def __init__(self, message: str = "Database error"):
        super().__init__(message, 500)


def register_error_handlers(app):
    """
    Register all error handlers with the Flask app.

    Call this function in your app factory:
    register_error_handlers(app)
    """

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors."""
        response = {
            'error': error.message,
            'status_code': error.status_code
        }
        if error.payload:
            response.update(error.payload)

        # Log the error
        logging.warning(f"API Error {error.status_code}: {error.message}")

        return jsonify(response), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle standard HTTP exceptions."""
        response = {
            'error': error.description or 'HTTP error',
            'status_code': error.code
        }

        # Log client errors (4xx) as info, server errors (5xx) as error
        if error.code >= 500:
            logging.error(f"HTTP {error.code}: {error.description}")
        elif error.code >= 400:
            logging.info(f"HTTP {error.code}: {error.description}")

        return jsonify(response), error.code

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors."""
        response = {
            'error': 'Resource not found',
            'status_code': 404,
            'path': request.path
        }
        logging.info(f"404 Not Found: {request.path}")
        return jsonify(response), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        response = {
            'error': 'Method not allowed',
            'status_code': 405,
            'method': request.method,
            'path': request.path
        }
        logging.info(f"405 Method Not Allowed: {request.method} {request.path}")
        return jsonify(response), 405

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle 500 Internal Server Error."""
        # Don't expose internal details in production
        if current_app.config.get('DEBUG', False):
            response = {
                'error': 'Internal server error',
                'status_code': 500,
                'traceback': traceback.format_exc()
            }
        else:
            response = {
                'error': 'Internal server error',
                'status_code': 500
            }

        logging.error(f"500 Internal Server Error: {traceback.format_exc()}")
        return jsonify(response), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected exceptions."""
        # Don't expose internal details in production
        if current_app.config.get('DEBUG', False):
            response = {
                'error': 'Unexpected error',
                'status_code': 500,
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        else:
            response = {
                'error': 'Unexpected error',
                'status_code': 500
            }

        logging.error(f"Unexpected error: {traceback.format_exc()}")
        return jsonify(response), 500


def handle_database_error(func):
    """
    Decorator to catch database errors and convert them to APIError.

    Usage:
    @handle_database_error
    def some_db_operation():
        # ... database code
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if it's a database-related error
            if 'sqlite3' in str(type(e)).lower() or 'database' in str(e).lower():
                raise DatabaseError(f"Database operation failed: {str(e)}")
            else:
                raise
    return wrapper


def validate_request_data(required_fields: list, data: dict):
    """
    Validate that required fields are present in request data.

    Raises ValidationError if any required field is missing.
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
