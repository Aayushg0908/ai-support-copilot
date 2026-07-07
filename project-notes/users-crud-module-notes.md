# Users CRUD Module - Complete Notes

## Files Created/Updated

| File | Action | Purpose |
|------|--------|---------|
| `services/user_service.py` | New | User management business logic |
| `schemas/user.py` | Updated | Added 4 schemas for user management |
| `api/v1/users.py` | New | 7 API endpoints for user operations |

## Reused Files

| File | How It's Used |
|------|---------------|
| `models/user.py` | Same model from auth module |
| `api/deps/auth.py` | get_current_user, require_role dependencies |

---

## API Endpoints

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| GET | /api/v1/users | Any | List users (paginated, filtered) |
| GET | /api/v1/users/{id} | Any | Get user details |
| PUT | /api/v1/users/{id} | Any | Update profile |
| PUT | /api/v1/users/{id}/role | Admin | Change role |
| POST | /api/v1/users/{id}/password | Self | Change password |
| DELETE | /api/v1/users/{id} | Admin | Deactivate user |
| POST | /api/v1/users/{id}/reactivate | Admin | Reactivate user |

---

## Key Features

### Pagination
- Users listed with page/per_page parameters
- Returns total count for frontend pagination UI
- Max 100 per page to prevent performance issues

### Filtering
- Filter by role (admin/agent/viewer)
- Text search across name and email (case-insensitive)
- Filter active/deactivated users

### Soft Delete
- Users are never actually deleted from database
- Deactivation sets is_active=False
- Preserves ticket history and comments
- Can be reactivated by admin

### Self-Protection Rules
- Cannot change your own role (prevents losing admin access)
- Cannot deactivate yourself
- Can only change your own password
- Must provide current password to change it

---

## Security Rules

| Action | Who | Extra Protection |
|--------|-----|------------------|
| List users | Anyone in org | Auto-filtered by org_id |
| View user | Anyone in org | Same org only |
| Update profile | Anyone | - |
| Change role | Admin only | Not on self |
| Change password | Self only | Current password required |
| Deactivate | Admin only | Not on self |
| Reactivate | Admin only | - |

---

## How Auth Module vs Users Module Differ

| Auth Module | Users Module |
|-------------|--------------|
| Register new users | Manage existing users |
| Login/logout | Update profiles |
| Token management | Role management |
| Password hashing (creation) | Password changing |
| Public endpoints | Protected endpoints |

---

## Database Queries Used

**List with filters:**
```sql
SELECT * FROM users
WHERE org_id = $1
  AND role = $2              -- if role filter
  AND is_active = true       -- if active_only
  AND (full_name ILIKE '%john%' OR email ILIKE '%john%')  -- if search
ORDER BY created_at DESC
LIMIT 20 OFFSET 0;

Future Enhancements
Bulk user import (CSV)

Bulk role assignment

User activity log

Profile avatars

Email verification on email change

Password reset by admin (without current password)

User invitation system

