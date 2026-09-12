"""
Database helper module for the backend.
Provides shared SQLite connection management and database path utilities.
"""

import os
import sqlite3
from sqlite3 import Connection
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATABASE_NAME = 'classes.db'
DEFAULT_DATABASE_PATH = os.path.join(PROJECT_ROOT, DEFAULT_DATABASE_NAME)


def get_database_path(db_path: Optional[str] = None) -> str:
    """Resolve the database path from environment, explicit override, or default."""
    if db_path:
        return db_path

    env_path = os.environ.get('DATABASE_PATH') or os.environ.get('DB_PATH')
    if env_path:
        return os.path.abspath(env_path)

    return DEFAULT_DATABASE_PATH


def get_db_connection(db_path: Optional[str] = None) -> Connection:
    """Return a new sqlite3 connection to the project database."""
    path = get_database_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def database_exists(db_path: Optional[str] = None) -> bool:
    """Return True if the resolved database file exists."""
    return os.path.exists(get_database_path(db_path))


def ensure_database(db_path: Optional[str] = None) -> str:
    """Ensure the database file exists and return its path."""
    path = get_database_path(db_path)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    if not os.path.exists(path):
        open(path, 'a', encoding='utf-8').close()
    return path


def execute_sql(sql: str, parameters: Optional[tuple] = None, db_path: Optional[str] = None) -> None:
    """Execute an SQL statement against the database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, parameters or ())
        conn.commit()
    finally:
        conn.close()


def execute_script(script: str, db_path: Optional[str] = None) -> None:
    """Execute a multi-statement SQL script against the database."""
    conn = get_db_connection(db_path)
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> Optional[dict]:
    """Convert a sqlite3.Row to a regular dictionary."""
    if row is None:
        return None
    return dict(row)


def query(sql: str, parameters: Optional[tuple] = None, db_path: Optional[str] = None) -> list[dict]:
    """Execute a query and return a list of dictionaries."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, parameters or ())
        rows = cursor.fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()
