# Database Schema Design
# AI Support Operations Platform

**Version:** 1.0  
**Database:** PostgreSQL 15+ with pgvector extension  

---

## 1. EXTENSION SETUP

```sql
-- Required for AI embeddings
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
2. CORE TABLES
2.1 organizations
Column	Type	Constraints	Description
id	UUID	PK, DEFAULT uuid_generate_v4()	Unique org identifier
name	VARCHAR(255)	NOT NULL	Company name
slug	VARCHAR(100)	NOT NULL, UNIQUE	URL-safe identifier
is_active	BOOLEAN	DEFAULT true	Soft delete flag
settings	JSONB	DEFAULT '{}'	Org-level config
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
Indexes:

sql
CREATE UNIQUE INDEX idx_organizations_slug ON organizations(slug);
2.2 users
Column	Type	Constraints	Description
id	UUID	PK	User identifier
org_id	UUID	NOT NULL, FK → organizations(id)	Belongs to org
email	VARCHAR(255)	NOT NULL, UNIQUE	Login email
password_hash	VARCHAR(255)	NOT NULL	bcrypt hash
full_name	VARCHAR(255)	NOT NULL	Display name
role	VARCHAR(20)	NOT NULL, CHECK IN ('admin','agent','viewer')	RBAC role
is_active	BOOLEAN	DEFAULT true	
last_login_at	TIMESTAMPTZ	NULL	Track activity
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
Indexes:

sql
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_role ON users(role);
2.3 tickets
Column	Type	Constraints	Description
id	UUID	PK	Ticket identifier
org_id	UUID	NOT NULL, FK → organizations(id)	Multi-tenant isolation
created_by	UUID	NOT NULL, FK → users(id)	Ticket creator
assigned_to	UUID	NULL, FK → users(id)	Current assignee
title	VARCHAR(500)	NOT NULL	Ticket subject
description	TEXT	NOT NULL	Full ticket body
status	VARCHAR(20)	NOT NULL, DEFAULT 'open'	open/in_progress/resolved/closed
priority	VARCHAR(20)	NOT NULL, DEFAULT 'medium'	low/medium/high/critical
category	VARCHAR(50)	NULL	Manual category
tags	JSONB	DEFAULT '[]'	Flexible tags
AI COLUMNS			
ai_category	VARCHAR(50)	NULL	AI-predicted category
ai_priority	VARCHAR(20)	NULL	AI-predicted priority
ai_confidence	FLOAT	NULL	AI confidence score 0-1
sentiment	VARCHAR(20)	NULL	positive/neutral/negative
sentiment_score	FLOAT	NULL	-1.0 to 1.0
health_score	INTEGER	NULL	0-100 customer health
embedding	vector(384)	NULL	For similarity search
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
resolved_at	TIMESTAMPTZ	NULL	SLA tracking
Indexes:

sql
CREATE INDEX idx_tickets_org_id ON tickets(org_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_created_by ON tickets(created_by);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX idx_tickets_embedding ON tickets USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
Constraints:

sql
ALTER TABLE tickets ADD CONSTRAINT chk_status 
  CHECK (status IN ('open', 'in_progress', 'resolved', 'closed'));
ALTER TABLE tickets ADD CONSTRAINT chk_priority 
  CHECK (priority IN ('low', 'medium', 'high', 'critical'));
2.4 comments
Column	Type	Constraints	Description
id	UUID	PK	Comment identifier
ticket_id	UUID	NOT NULL, FK → tickets(id) ON DELETE CASCADE	Parent ticket
user_id	UUID	NOT NULL, FK → users(id)	Comment author
body	TEXT	NOT NULL	Comment content
parent_id	UUID	NULL, FK → comments(id)	For threaded replies
is_internal	BOOLEAN	DEFAULT false	Internal note flag
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
Indexes:

sql
CREATE INDEX idx_comments_ticket_id ON comments(ticket_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_parent_id ON comments(parent_id);
CREATE INDEX idx_comments_created_at ON comments(ticket_id, created_at);
2.5 knowledge_base (Phase 2)
Column	Type	Constraints	Description
id	UUID	PK	Article identifier
org_id	UUID	NOT NULL, FK → organizations(id)	Org-specific KB
title	VARCHAR(500)	NOT NULL	Article title
content	TEXT	NOT NULL	Article body
source_type	VARCHAR(50)	DEFAULT 'manual'	manual/imported/ai_generated
source_ticket_id	UUID	NULL, FK → tickets(id)	If generated from ticket
embedding	vector(384)	NULL	For semantic search
usage_count	INTEGER	DEFAULT 0	Popularity tracking
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
updated_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
Indexes:
sql
CREATE INDEX idx_kb_org_id ON knowledge_base(org_id);
CREATE INDEX idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
2.6 audit_logs (Phase 5)
Column	Type	Constraints	Description
id	UUID	PK	Log identifier
org_id	UUID	NOT NULL, FK → organizations(id)	
user_id	UUID	NULL, FK → users(id)	Who did it
action	VARCHAR(100)	NOT NULL	created/updated/deleted/exported
resource_type	VARCHAR(50)	NOT NULL	ticket/user/org
resource_id	UUID	NOT NULL	Affected record
changes	JSONB	DEFAULT '{}'	Before/after values
ip_address	VARCHAR(45)	NULL	IPv4/IPv6
created_at	TIMESTAMPTZ	NOT NULL, DEFAULT NOW()	
Indexes:

sql
CREATE INDEX idx_audit_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at DESC);
3. RELATIONSHIP SUMMARY
text
organizations 1───many users
organizations 1───many tickets
organizations 1───many knowledge_base
organizations 1───many audit_logs

users 1───many tickets (created_by)
users 1───many tickets (assigned_to)
users 1───many comments

tickets 1───many comments
tickets 1───many knowledge_base (source_ticket_id)

comments 1───many comments (parent_id - self-referential)
4. MIGRATION STRATEGY
Using Alembic for version-controlled migrations:

text
alembic/
├── versions/
│   ├── 001_create_organizations.py
│   ├── 002_create_users.py
│   ├── 003_create_tickets.py
│   ├── 004_create_comments.py
│   ├── 005_add_ai_columns.py
│   └── 006_create_knowledge_base.py
└── env.py
Migration Rules:

Never edit existing migrations - only add new ones

Always include downgrade() function

Test both upgrade and downgrade

5. QUERY PATTERNS (Common)
Get all tickets for an org (with filters)
sql
SELECT t.*, 
       creator.full_name as created_by_name,
       assignee.full_name as assigned_to_name
FROM tickets t
JOIN users creator ON t.created_by = creator.id
LEFT JOIN users assignee ON t.assigned_to = assignee.id
WHERE t.org_id = $1
  AND t.status = $2
ORDER BY t.created_at DESC
LIMIT 20 OFFSET 0;
Find similar tickets (AI)
sql
SELECT id, title, status, 
       1 - (embedding <=> $1) as similarity
FROM tickets 
WHERE org_id = $2 
  AND embedding IS NOT NULL
ORDER BY embedding <=> $1
LIMIT 5;
Dashboard stats
sql
SELECT 
  status,
  COUNT(*) as count
FROM tickets
WHERE org_id = $1
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY status;
6. DATA RETENTION & CLEANUP
Policy	Implementation
Soft delete users	is_active = false
Archive old tickets	Move to archive table after 1 year
Delete audit logs	After 2 years (GDPR)
Cascade delete	Comments deleted when ticket deleted
text

---

## Learning Notes File

Create file: `project-notes/database-schema-notes.md`

```markdown
# Database Schema Design - Learning Notes

## Why PostgreSQL?

### ACID Compliance
Tickets need transactions. If a ticket is created and comment fails, both roll back.
```python
# This must be atomic
create_ticket()
create_first_comment()  # If this fails, ticket should not exist
pgvector Extension
PostgreSQL has a vector extension that lets us store AI embeddings right next to ticket data. No separate vector database needed initially.

JSONB vs Separate Tables
tags and settings use JSONB because they're flexible and schema-less

Core data (users, tickets) use normalized tables because we query by these fields

Key Design Decisions
1. UUID vs Auto-Increment IDs
Chose UUID:

✅ No ID collision when sharding

✅ Can generate on frontend (optimistic UI)

✅ No enumeration attacks (/users/1, /users/2)

❌ Slightly larger storage

❌ Not sortable by creation time

2. Soft Delete vs Hard Delete
Chose Soft Delete for users:

Keep referential integrity (old tickets still reference deleted users)

GDPR compliance (can still delete PII)

Undo capability

3. AI Columns on Tickets Table
Why not separate AI table?

Simpler queries (no JOIN needed)

AI data is 1:1 with tickets

NULL columns don't take space in PostgreSQL

4. Self-Referencing Comments
parent_id enables threaded comments:

text
Comment 1
  └─ Reply to Comment 1 (parent_id = 1)
      └─ Reply to Reply (parent_id = 2)
5. Vector Index (IVFFlat)
Splits vectors into lists for approximate search

Much faster than exact search on large datasets

Trade-off: ~95% accuracy vs exact search

Interview Questions
Q: Why UUIDs instead of auto-increment IDs?
A: Security (no enumeration), distributed systems compatibility, frontend can generate IDs. Trade-off is storage size and index performance.

Q: How would you scale this database?
A:

Read replicas for dashboard queries

Partition tickets table by org_id

Move vector search to dedicated instance if needed

Cache frequent queries with Redis

Q: What's the most complex query in this system?
A: Similar ticket search using cosine similarity on embeddings. Requires vector index for performance.

Q: How do you handle database migrations in production?
A: Alembic with zero-downtime migrations:

Add nullable column

Backfill data

Add NOT NULL constraint

Never rename columns (add new, deprecate old)

Q: Explain the comments table design.
A: It's an adjacency list pattern. Each comment has optional parent_id pointing to another comment. This enables threaded replies. Alternative would be nested sets (better for reads, worse for writes).

Performance Optimization Notes
Index every foreign key - speeds up JOINs

Composite indexes for common queries - e.g., (org_id, status)

Partial indexes - index only unresolved tickets

pgvector IVFFlat - approximate similarity search

Connection pooling - use PgBouncer in production

Common Mistakes to Avoid
❌ Not indexing foreign keys → slow JOINs

❌ VARCHAR without limit → can cause issues

❌ Not using TIMESTAMPTZ → timezone bugs

❌ Hard deletes without soft delete → data loss

❌ Missing ON DELETE CASCADE → orphaned records

text

---

## Summary

✅ **Database Schema designed** - 6 tables, all relationships, indexes  
✅ **Learning notes created** - Database interview prep done  

---