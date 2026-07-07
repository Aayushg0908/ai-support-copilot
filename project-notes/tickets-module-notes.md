# Tickets Module - Complete Notes

## Files Created

| File | Purpose | Key Contents |
|------|---------|--------------|
| `models/ticket.py` | Database table | 14 ticket categories, 4 statuses, AI columns, embedding vector |
| `schemas/ticket.py` | Data validation | Create/Update/Response schemas, dedicated status & assign schemas |
| `services/ticket_service.py` | Business logic | Create, list with 10+ filters, update, assign, status change, delete |
| `api/deps/database.py` | Dependency | get_current_org_id shortcut for multi-tenancy |
| `api/v1/tickets.py` | HTTP endpoints | 7 endpoints (CRUD + quick status + quick assign) |

---

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /api/v1/tickets | Create new ticket |
| GET | /api/v1/tickets | List with filters (paginated) |
| GET | /api/v1/tickets/{id} | View full details |
| PUT | /api/v1/tickets/{id} | Update ticket |
| PATCH | /api/v1/tickets/{id}/status | Quick status change |
| PATCH | /api/v1/tickets/{id}/assign | Quick assign (auto in_progress) |
| DELETE | /api/v1/tickets/{id} | Close ticket (soft delete) |

---

## Ticket Lifecycle
Ticket Created (status: open)
│
├── Agent Assigned (status → in_progress)
│ │
│ ├── Agent Resolves (status → resolved, resolved_at set)
│ │ │
│ │ ├── Customer Reopens (status → open, resolved_at cleared)
│ │ │
│ │ └── Ticket Closed (status → closed)
│ │
│ └── Ticket Closed directly (status → closed)
│
└── Closed without resolution (status → closed)

text

---

## Available Filters For List Endpoint

| Filter | Query Parameter | Example |
|--------|----------------|---------|
| Status | ?status=open | open/in_progress/resolved/closed |
| Priority | ?priority=critical | low/medium/high/critical |
| Category | ?category=bug | Any of 14 categories |
| Assigned To | ?assigned_to=uuid | User UUID |
| Created By | ?created_by=uuid | User UUID |
| Search | ?search=login+error | Searches title + description |
| Date Range | ?from_date=&to_date= | ISO datetime format |
| Sort By | ?sort_by=priority | created_at/updated_at/priority/status |
| Sort Order | ?sort_order=asc | asc/desc |
| Pagination | ?page=1&per_page=20 | Max 100 per page |

---

## Ticket Categories (14 Total)

bug, feature_request, support, billing, account, performance, security, onboarding, integration, refund, general_inquiry, complaint, feedback, other

---

## Key Design Decisions

### Why Dedicated Status & Assign Endpoints
Instead of one generic update, common actions have their own endpoints:
- PUT /tickets/{id} - Full update (any field)
- PATCH /tickets/{id}/status - Just status (with auto-logic)
- PATCH /tickets/{id}/assign - Just assignment (auto-sets in_progress)

This makes the frontend simpler and allows adding notification logic per action later.

### Why Soft Delete
Tickets are never actually deleted. DELETE sets status to "closed". This preserves:
- Ticket history for reporting
- All comments and activity
- Audit trail
- Ability to reopen if needed

### Auto resolved_at Logic
- When status changes to "resolved" → resolved_at = now()
- When status changes to "closed" → resolved_at = now()
- When reopened (open/in_progress) → resolved_at = None

This tracks resolution time for SLA reporting without manual input.

### Auto in_progress on Assignment
When a ticket is assigned to someone, status automatically becomes "in_progress". This means:
- No orphaned "assigned but still showing open" tickets
- Cleaner workflow: assign = start working

### Multi-Tenancy Scoping
Every query includes `WHERE org_id = current_user.org_id`. Users can never see other organizations' tickets. Even if they guess a ticket ID, the query returns nothing.

---

## Database Table Structure
tickets table:
├── id : UUID PRIMARY KEY
├── org_id : UUID FK → organizations
├── created_by : UUID FK → users (nullable on delete)
├── assigned_to : UUID FK → users (nullable)
├── title : VARCHAR(500)
├── description : TEXT
├── status : ENUM (open, in_progress, resolved, closed)
├── priority : ENUM (low, medium, high, critical)
├── category : ENUM (14 values)
├── tags : JSONB (flexible labels)
├── ai_category : VARCHAR (Phase 2)
├── ai_priority : VARCHAR (Phase 2)
├── ai_confidence : FLOAT (Phase 2)
├── sentiment : ENUM (Phase 3)
├── health_score : INTEGER (Phase 3)
├── embedding : vector(384) (Phase 2)
├── resolved_at : TIMESTAMPTZ
├── created_at : TIMESTAMPTZ
└── updated_at : TIMESTAMPTZ

Indexes:

org_id, status, priority, assigned_to, created_by, created_at

embedding (ivfflat for similarity search)

text

---

## What's Ready For AI Integration

The ticket model already has AI columns ready:
- ai_category, ai_priority, ai_confidence
- sentiment, sentiment_score
- health_score
- embedding (vector for similarity search)

In Phase 2, we just populate these fields. No database changes needed.

---

## Future Enhancements

- Bulk ticket operations (close multiple, assign multiple)
- Ticket merging (duplicate detection)
- SLA breach notifications
- Ticket templates for common issues
- Automated workflows (if priority=critical, assign to senior agent)
- Ticket history/changelog (who changed what when)