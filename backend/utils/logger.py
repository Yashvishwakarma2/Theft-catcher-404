"""
Logging configuration for the Flask backend.
Provides centralized logging setup with file and console output.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

# Global logger instances
_loggers = {}


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None,
                  max_bytes: int = 10*1024*1024, backup_count: int = 5) -> None:
    """
    Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, uses default location)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified or default)
    if log_file is None:
        # Default log file in backend/logs directory
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(backend_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'app.log')

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Log the setup
    root_logger.info(f"Logging configured: level={log_level}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module/component.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    if name not in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger
    return _loggers[name]


def log_request(logger: logging.Logger, method: str, path: str, status_code: int,
                duration: Optional[float] = None, user_id: Optional[int] = None) -> None:
    """
    Log an HTTP request.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        user_id: User ID if authenticated
    """
    message = f"{method} {path} -> {status_code}"
    if user_id:
        message += f" (user: {user_id})"
    if duration is not None:
        message += f" ({duration:.3f}s)"

    if status_code >= 500:
        logger.error(message)
    elif status_code >= 400:
        logger.warning(message)
    else:
        logger.info(message)


def log_database_operation(logger: logging.Logger, operation: str, table: str,
                          record_id: Optional[int] = None, user_id: Optional[int] = None) -> None:
    """
    Log a database operation.

    Args:
        logger: Logger instance
        operation: Operation type (INSERT, UPDATE, DELETE, SELECT)
        table: Table name
        record_id: Record ID if applicable
        user_id: User ID performing the operation
    """
    message = f"DB {operation} on {table}"
    if record_id:
        message += f" (id: {record_id})"
    if user_id:
        message += f" (user: {user_id})"

    logger.info(message)


def log_error(logger: logging.Logger, error: Exception, context: Optional[str] = None) -> None:
    """
    Log an exception with context.

    Args:
        logger: Logger instance
        error: Exception object
        context: Additional context information
    """
    message = f"Exception: {type(error).__name__}: {str(error)}"
    if context:
        message = f"{context} - {message}"

    logger.error(message, exc_info=True)


class RequestLogger:
    """
    Context manager for logging request start/end with timing.
    """

    def __init__(self, logger: logging.Logger, method: str, path: str, user_id: Optional[int] = None):
        self.logger = logger
        self.method = method
        self.path = path
        self.user_id = user_id
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Started {self.method} {self.path}" + (f" (user: {self.user_id})" if self.user_id else ""))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        status_code = 500 if exc_type else 200

        log_request(self.logger, self.method, self.path, status_code, duration, self.user_id)

        if exc_type:
            log_error(self.logger, exc_val, f"Request failed: {self.method} {self.path}")


# Initialize default logging on import
setup_logging()
