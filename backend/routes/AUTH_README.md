# Authentication Routes Documentation

This module provides JWT-based authentication for the AI Surveillance Dashboard.

## Overview

The `auth_routes.py` module handles:
- User registration
- User login with JWT token generation
- Token verification
- Token refresh
- Password changes
- User information retrieval

## Database Schema

### Users Table

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
)
```

## API Endpoints

### Base URL
```
/api/auth
```

### 1. Register User
**Endpoint:** `POST /api/auth/register`

**Request Body:**
```json
{
    "username": "john_doe",
    "password": "password123",
    "email": "john@example.com",
    "full_name": "John Doe"
}
```

**Response (201 Created):**
```json
{
    "message": "User registered successfully",
    "user_id": 1,
    "username": "john_doe"
}
```

**Validation Rules:**
- Username: minimum 3 characters, must be unique
- Password: minimum 6 characters
- Email: must be unique (optional)

---

### 2. Login User
**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
    "username": "john_doe",
    "password": "password123"
}
```

**Response (200 OK):**
```json
{
    "message": "Login successful",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": 1,
        "username": "john_doe"
    }
}
```

**Token Expiration:** 24 hours

---

### 3. Verify Token
**Endpoint:** `GET /api/auth/verify-token`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "message": "Token is valid",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe"
    }
}
```

---

### 4. Refresh Token
**Endpoint:** `POST /api/auth/refresh-token`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "message": "Token refreshed successfully",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### 5. Get User Information
**Endpoint:** `GET /api/auth/user-info`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "created_at": "2024-01-15 10:30:00",
        "last_login": "2024-01-20 14:45:00",
        "is_active": 1
    }
}
```

---

### 6. Change Password
**Endpoint:** `POST /api/auth/change-password`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "old_password": "password123",
    "new_password": "newpassword456"
}
```

**Response (200 OK):**
```json
{
    "message": "Password changed successfully"
}
```

**Validation Rules:**
- New password: minimum 6 characters
- New password must be different from old password

---

### 7. Logout
**Endpoint:** `POST /api/auth/logout`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "message": "Logged out successfully"
}
```

**Note:** Token invalidation is typically handled client-side by deleting the stored token.

---

## Error Responses

### 400 Bad Request
```json
{
    "message": "Username and password are required"
}
```

### 401 Unauthorized
```json
{
    "message": "Invalid username or password"
}
```

### 403 Forbidden
```json
{
    "message": "User account is inactive"
}
```

### 404 Not Found
```json
{
    "message": "User not found"
}
```

### 409 Conflict
```json
{
    "message": "Username or email already exists"
}
```

### 500 Internal Server Error
```json
{
    "message": "Registration failed: <error details>"
}
```

---

## Token Format

The JWT token contains the following claims:
```json
{
    "user_id": 1,
    "username": "john_doe",
    "exp": 1705779600
}
```

---

## Security Features

1. **Password Hashing:** All passwords are hashed using `werkzeug.security.generate_password_hash()`
2. **JWT Tokens:** Secure token-based authentication with 24-hour expiration
3. **Token Required Decorator:** Protects endpoints that require authentication
4. **Password Validation:** Minimum 6 characters required
5. **Unique Constraints:** Username and email must be unique

---

## Usage Example

### JavaScript (Frontend)

```javascript
// Register
const registerResponse = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'john_doe',
        password: 'password123',
        email: 'john@example.com',
        full_name: 'John Doe'
    })
});
const registerData = await registerResponse.json();

// Login
const loginResponse = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'john_doe',
        password: 'password123'
    })
});
const loginData = await loginResponse.json();
const token = loginData.token;

// Store token
localStorage.setItem('auth_token', token);

// Use token in requests
const userResponse = await fetch('/api/auth/user-info', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
const userData = await userResponse.json();
```

---

## Integration with Frontend

To integrate with the frontend login form:

1. Update `static/login.js` to send credentials to `/api/auth/login`
2. Store the returned JWT token in `localStorage`
3. Send the token in the `Authorization` header for protected API calls
4. Handle token expiration and refresh when needed

---

## Notes

- Tokens expire after 24 hours
- All passwords are stored hashed and are never returned in API responses
- The `is_active` field can be used to disable user accounts
- `last_login` is automatically updated on successful login
