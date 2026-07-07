# Comments Module - Complete Notes

## Files Created

| File | Purpose | Key Contents |
|------|---------|--------------|
| `models/comment.py` | Database table | ticket_id, user_id, parent_id (self-reference), is_internal |
| `schemas/comment.py` | Data validation | Create/Update/Response schemas with nested replies |
| `services/comment_service.py` | Business logic | Create, list (flat/threaded), update, delete |
| `api/v1/comments.py` | HTTP endpoints | 4 endpoints (create, list, update, delete) |

---

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /api/v1/tickets/{id}/comments | Add comment or reply |
| GET | /api/v1/tickets/{id}/comments | List comments (?threaded=true for nesting) |
| PUT | /api/v1/comments/{id} | Edit comment body |
| DELETE | /api/v1/comments/{id} | Delete comment + replies |

---

## Threaded Comments System

### How It Works
All comments are in one table. A comment can reference another comment as its parent via `parent_id`. This creates a tree structure.
Database (flat):

id	body	parent_id
1	"Need help"	NULL
2	"Try this"	1
3	"Still broken"	1
4	"Show error?"	2
Displayed (threaded):
Comment 1: "Need help"
├── Comment 2: "Try this"
│ └── Comment 4: "Show error?"
└── Comment 3: "Still broken"

text

### Threaded vs Flat Mode
- `GET /comments?threaded=false` → Flat list (good for mobile, simple UIs)
- `GET /comments?threaded=true` → Nested tree (good for conversation view)

### Tree Building Algorithm
1. Fetch all comments for a ticket
2. Put them in a map by ID
3. For each comment:
   - If parent_id is NULL → it's top-level
   - If parent_id exists → add to parent's `replies` list
4. Return only top-level comments (replies are nested inside)

---

## Internal Notes

Comments have `is_internal` flag:
- `is_internal=true` → Only visible to agents/admins
- `is_internal=false` → Visible to everyone (normal comment)

Used for team communication without the customer seeing:
Agent 1 (internal): "This looks like a server issue, escalating to DevOps"
Agent 2 (public): "We're looking into this, will update you shortly"

text

---

## Authorization Rules

| Action | Who Can Do It |
|--------|---------------|
| Create comment | Any logged-in user |
| Edit comment | Comment author only |
| Delete comment | Comment author only |
| View internal notes | Agents and admins (Phase 5) |

---

## Cascade Delete

When a comment is deleted:
- All replies to that comment are automatically deleted (CASCADE)
- This prevents orphaned replies with no parent
Delete Comment 2:
Comment 1: "Need help"
├── Comment 2: "Try this" ← DELETED
│ └── Comment 4: "Show error?" ← Also DELETED (CASCADE)
└── Comment 3: "Still broken" ← Stays (different parent)

text

---

## Database Table Structure
comments table:
├── id : UUID PRIMARY KEY
├── ticket_id : UUID FK → tickets (CASCADE delete)
├── user_id : UUID FK → users (SET NULL on delete)
├── parent_id : UUID FK → comments (self-reference, CASCADE)
├── body : TEXT
├── is_internal : BOOLEAN
├── created_at : TIMESTAMPTZ
└── updated_at : TIMESTAMPTZ

Indexes:

ticket_id (for listing comments on a ticket)

user_id (for finding user's comments)

parent_id (for building threaded view)

text

---

## How Comments Connect To Other Modules
Tickets Module
└── Each ticket has many comments
└── Comments can have replies (self-referencing)

Users Module
└── Comments have an author (user_id)
└── user_name is fetched and attached to response

Auth Module
└── Only authenticated users can comment
└── Only comment author can edit/delete

text

---

## Future Enhancements

- Rich text support (markdown, formatting)
- File attachments on comments
- Comment reactions (thumbs up, emoji)
- Edit history (track what was changed)
- Mention other users (@username)
- Email notifications for new comments
- WebSocket real-time updates