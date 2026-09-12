"""
User model and database helpers for authentication.
Provides a reusable layer for user CRUD, password hashing, and login-related operations.
"""

import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from werkzeug.security import check_password_hash, generate_password_hash

# Project root is the backend directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(PROJECT_ROOT, 'classes.db')


def get_db_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection to the project database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class UserRecord:
    id: int
    username: str
    password: str
    email: Optional[str]
    full_name: Optional[str]
    created_at: str
    last_login: Optional[str]
    is_active: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': bool(self.is_active)
        }


class UserModel:
    """Helper class for user database operations."""

    TABLE_NAME = 'users'

    @classmethod
    def initialize_table(cls) -> None:
        """Create the users table if it does not exist."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE,
                    full_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def _row_to_user(cls, row: sqlite3.Row) -> Optional[UserRecord]:
        if row is None:
            return None
        return UserRecord(
            id=row['id'],
            username=row['username'],
            password=row['password'],
            email=row['email'],
            full_name=row['full_name'],
            created_at=row['created_at'],
            last_login=row['last_login'],
            is_active=row['is_active']
        )

    @classmethod
    def create_user(cls, username: str, password: str, email: Optional[str] = None,
                    full_name: Optional[str] = None) -> UserRecord:
        """Create a new user and return the stored record."""
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {cls.TABLE_NAME} (username, password, email, full_name)
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, email, full_name))
            conn.commit()
            user_id = cursor.lastrowid
            return cls.get_user_by_id(user_id)
        finally:
            conn.close()

    @classmethod
    def get_user_by_id(cls, user_id: int) -> Optional[UserRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.TABLE_NAME} WHERE id = ?', (user_id,))
            return cls._row_to_user(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_user_by_username(cls, username: str) -> Optional[UserRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.TABLE_NAME} WHERE username = ?', (username,))
            return cls._row_to_user(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[UserRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.TABLE_NAME} WHERE email = ?', (email,))
            return cls._row_to_user(cursor.fetchone())
        finally:
            conn.close()

    @classmethod
    def verify_password(cls, username: str, password: str) -> bool:
        user = cls.get_user_by_username(username)
        if user is None:
            return False
        return check_password_hash(user.password, password)

    @classmethod
    def update_last_login(cls, user_id: int) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'UPDATE {cls.TABLE_NAME} SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def change_password(cls, user_id: int, new_password: str) -> None:
        hashed_password = generate_password_hash(new_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'UPDATE {cls.TABLE_NAME} SET password = ? WHERE id = ?',
                           (hashed_password, user_id))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def update_profile(cls, user_id: int, email: Optional[str] = None,
                       full_name: Optional[str] = None, is_active: Optional[bool] = None) -> None:
        updates = []
        values = []

        if email is not None:
            updates.append('email = ?')
            values.append(email)
        if full_name is not None:
            updates.append('full_name = ?')
            values.append(full_name)
        if is_active is not None:
            updates.append('is_active = ?')
            values.append(int(is_active))

        if not updates:
            return

        values.append(user_id)
        query = f'UPDATE {cls.TABLE_NAME} SET {", ".join(updates)} WHERE id = ?'

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, tuple(values))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def deactivate_user(cls, user_id: int) -> None:
        cls.update_profile(user_id, is_active=False)

    @classmethod
    def activate_user(cls, user_id: int) -> None:
        cls.update_profile(user_id, is_active=True)

    @classmethod
    def list_users(cls, limit: int = 100, offset: int = 0) -> List[UserRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT * FROM {cls.TABLE_NAME} ORDER BY created_at DESC LIMIT ? OFFSET ?',
                           (limit, offset))
            rows = cursor.fetchall()
            return [cls._row_to_user(row) for row in rows if row is not None]
        finally:
            conn.close()

    @classmethod
    def delete_user(cls, user_id: int) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'DELETE FROM {cls.TABLE_NAME} WHERE id = ?', (user_id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def serialize_user(cls, user: UserRecord) -> Dict[str, Any]:
        return user.as_dict() if user else {}
