# Authentication Module - Complete Notes

## Files We Created

| File                       | Purpose          | Key Contents                                       |
| -------------------------- | ---------------- | -------------------------------------------------- |
| `models/user.py`           | Database table   | User model with org_id, email, password_hash, role |
| `schemas/user.py`          | Data validation  | Register/Login/Response schemas                    |
| `services/auth_service.py` | Business logic   | Register, login, refresh, get_current_user         |
| `api/deps/auth.py`         | Route protection | get_current_user, require_role                     |
| `api/v1/auth.py`           | HTTP endpoints   | /register, /login, /refresh, /me, /logout          |

---

## How These Files Work Together

Request comes in (`POST /api/v1/auth/register`)

↓

`api/v1/auth.py`

* Receives JSON body
* Pydantic validates against `UserRegisterRequest` (`schemas/user.py`)
* Calls `auth_service.register()` (`services/auth_service.py`)

↓

`services/auth_service.py`

* Checks email uniqueness (`models/user.py`)
* Creates Organization (`models/organization.py`)
* Creates User with hashed password (`models/user.py`)
* Uses `hash_password()` (`core/security.py`)
* Uses `create_access_token()` (`core/security.py`)
* Returns `user`, `org`, `access_token`, `refresh_token`

↓

`api/v1/auth.py`

* Calls `db.commit()` to save everything
* Returns `UserLoginResponse` (`schemas/user.py`)

↓

Response sent to client

---

## Authentication Flow

### Registration

1. Client sends email, password, full_name, organization_name
2. Server checks if email already exists
3. Server creates Organization with URL-safe slug
4. Server creates User (admin role) linked to that organization
5. Password is hashed with bcrypt (never stored raw)
6. JWT tokens generated with user_id and org_id embedded
7. Tokens returned to client

### Login

1. Client sends email, password
2. Server finds user by email
3. Server verifies password against stored hash
4. If match, generates new JWT tokens
5. Updates last_login_at timestamp
6. Returns tokens + user profile

### Token Refresh

1. Client sends refresh_token to `/auth/refresh`
2. Server verifies token is valid and type is `"refresh"`
3. Server finds user (checking they still exist and are active)
4. Server generates new access + refresh token pair
5. Returns new tokens

### Authenticated Request

1. Client sends request with header:

```text
Authorization: Bearer <token>
```

2. FastAPI dependency extracts token
3. Server decodes and verifies token
4. Server finds user from token's user_id
5. If all valid, user object passed to route handler
6. Route handler runs with current_user available

---

## Key Concepts Used

### Password Hashing (bcrypt)

User types:

```text
MyPassword123
```

Stored as:

```text
$2b$12$LJ3m4ys3GZkYOURANDOMSALTk8GZkYO...
```

Same password = different hash (because of random salt)

bcrypt is intentionally slow (~100ms) to prevent brute-force attacks.

---

### JWT Tokens

Header:

```json
{"alg": "HS256", "typ": "JWT"}
```

Payload:

```json
{"sub": "user_id", "org_id": "org_id", "exp": 1719000000}
```

Signature:

```text
HMACSHA256(header + "." + payload, secret_key)
```

Three parts separated by dots:

```text
header.payload.signature
```

---

### Access Token vs Refresh Token

|           | Access Token         | Refresh Token        |
| --------- | -------------------- | -------------------- |
| Lifetime  | 30 minutes           | 7 days               |
| Sent with | Every request        | Only `/auth/refresh` |
| Storage   | Memory (React state) | httpOnly cookie      |
| If stolen | Expires quickly      | Can be blacklisted   |

---

### Dependencies (FastAPI Depends)

```python
@router.get("/profile")
def profile(current_user: User = Depends(get_current_user)):
    return current_user
```

Instead of repeating authentication code in every route, the dependency runs **before** the route.

If it fails (invalid token), the route never executes.

---

## Database Schema (users table)

| Column        | Type         | Description                     |
| ------------- | ------------ | ------------------------------- |
| id            | UUID (PK)    | Auto-generated unique ID        |
| org_id        | UUID (FK)    | Links to organizations table    |
| email         | VARCHAR(255) | Unique, indexed                 |
| password_hash | VARCHAR(255) | bcrypt hash, never raw password |
| full_name     | VARCHAR(255) | Display name                    |
| role          | ENUM         | admin, agent, or viewer         |
| is_active     | BOOLEAN      | Soft delete flag                |
| last_login_at | TIMESTAMPTZ  | Updated on each login           |
| created_at    | TIMESTAMPTZ  | Auto-set on creation            |
| updated_at    | TIMESTAMPTZ  | Auto-updated on changes         |

---

## API Endpoints Summary

| Method | Path                    | Auth Required           | Purpose        |
| ------ | ----------------------- | ----------------------- | -------------- |
| POST   | `/api/v1/auth/register` | No                      | Create account |
| POST   | `/api/v1/auth/login`    | No                      | Sign in        |
| POST   | `/api/v1/auth/refresh`  | No (uses refresh token) | Get new tokens |
| GET    | `/api/v1/auth/me`       | Yes                     | Get profile    |
| POST   | `/api/v1/auth/logout`   | Yes                     | Logout         |

---

## Error Handling

| Scenario             | HTTP Status | Error Code   |
| -------------------- | ----------- | ------------ |
| Email already exists | 409         | CONFLICT     |
| Wrong password       | 401         | UNAUTHORIZED |
| Invalid token        | 401         | UNAUTHORIZED |
| Expired token        | 401         | UNAUTHORIZED |
| Deactivated account  | 403         | FORBIDDEN    |
| Missing auth header  | 401         | UNAUTHORIZED |
| Wrong role           | 403         | FORBIDDEN    |

---

## What We Haven't Built Yet (Future)

### Email Verification

Send email with a verification link before activating account.

### Password Reset

Forgot password flow.

### Token Blacklisting

Store revoked tokens in Redis.

### Rate Limiting

Prevent brute-force login attempts.

### MFA (Multi-Factor Authentication)

Two-factor authentication.

### OAuth

Login with Google/GitHub.

### Session Management

View and revoke active sessions.

---

## Testing This Module

Start the server:

```bash
uvicorn app.main:app --reload
```

### Test Registration

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@demo.com",
    "password": "StrongPass1",
    "full_name": "Test User",
    "organization_name": "Demo Inc"
  }'
```

### Test Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@demo.com",
    "password": "StrongPass1"
  }'
```

### Test Authenticated Endpoint

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
