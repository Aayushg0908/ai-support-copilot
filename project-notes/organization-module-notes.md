# Organization Module - Complete Notes

## Files Created

| File                               | Purpose         | Key Contents                                      |
| ---------------------------------- | --------------- | ------------------------------------------------- |
| `models/organization.py`           | Database table  | name, slug, is_active, settings                   |
| `schemas/organization.py`          | Data validation | Create/Update/Response schemas                    |
| `services/organization_service.py` | Business logic  | create, update, delete, list, get with user count |
| `api/v1/organizations.py`          | HTTP endpoints  | CRUD + list users in org                          |

---

## API Endpoints

| Method | Route                            | Auth  | Purpose                  |
| ------ | -------------------------------- | ----- | ------------------------ |
| POST   | /api/v1/organizations            | Yes   | Create organization      |
| GET    | /api/v1/organizations            | Admin | List all (paginated)     |
| GET    | /api/v1/organizations/{id}       | Yes   | Get details + user count |
| PUT    | /api/v1/organizations/{id}       | Admin | Update organization      |
| DELETE | /api/v1/organizations/{id}       | Admin | Soft delete (deactivate) |
| GET    | /api/v1/organizations/{id}/users | Yes   | List users in org        |

---

## How Organization Connects To Everything

Organization (top-level container)

│

├── Users (belong to one org via org_id foreign key)

│

├── Tickets (belong to one org via org_id foreign key)

│

└── Future: Knowledge Base, Audit Logs (all scoped to org)

The organization is the multi-tenancy foundation. Every query in the system filters by org_id to keep companies isolated.

---

## Key Features Explained

### Slug Generation

Converts company names to URL-safe identifiers:

* "Acme Corp" → "acme-corp"
* "John's Repair!" → "johns-repair"

Handles duplicates by appending numbers:

* "acme-corp-1"

---

### Soft Delete

Never actually deletes rows. Sets `is_active=False` instead.

This preserves:

* User accounts linked to the org
* All tickets and comments
* Ability to reactivate later

---

### Pagination

List endpoint uses page/per_page pattern:

* `/organizations?page=1&per_page=20` → Items 1-20
* `/organizations?page=2&per_page=20` → Items 21-40

Returns total count so frontend knows how many pages exist.

---

### User Count Query

Uses SQL JOIN + COUNT to get org details and user count in one database query instead of two separate queries.

More efficient.

---

### Settings (JSONB)

Flexible JSON column for org-specific configuration.

Examples:

```json
{"timezone": "US/Eastern"}
```

```json
{"ticket_prefix": "TICKET"}
```

```json
{
  "branding": {
    "logo_url": "...",
    "color": "#FF5500"
  }
}
```

Currently stores empty object `{}`.

Useful for future customization without database changes.

---

## Role-Based Access In This Module

| Action         | admin | agent | viewer |
| -------------- | ----- | ----- | ------ |
| Create org     | ✅     | ✅     | ✅      |
| View own org   | ✅     | ✅     | ✅      |
| View all orgs  | ✅     | ❌     | ❌      |
| Update org     | ✅     | ❌     | ❌      |
| Delete org     | ✅     | ❌     | ❌      |
| View org users | ✅     | ✅     | ✅      |

---

## Database Schema

### organizations table

```text
organizations
├── id : UUID PRIMARY KEY
├── name : VARCHAR(255) NOT NULL
├── slug : VARCHAR(100) UNIQUE NOT NULL
├── is_active : BOOLEAN DEFAULT true
├── settings : JSONB DEFAULT '{}'
├── created_at : TIMESTAMPTZ NOT NULL
└── updated_at : TIMESTAMPTZ NOT NULL
```
