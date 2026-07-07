# Database Layer - Learning Notes

## Files Created

### base.py
- Parent class for all database models
- Provides id, created_at, updated_at to every table
- Uses UUIDs for security and distributed system compatibility

### session.py
- Creates database engine (connection to PostgreSQL)
- SessionLocal factory creates new sessions per request
- get_db() dependency automatically closes sessions

### init_db.py
- Enables PostgreSQL extensions on first run
- Creates all tables from model definitions
- Seeds demo data in development mode

## How They Work Together

base.py defines WHAT tables look like
    ↓
session.py handles HOW to connect and talk to database
    ↓
init_db.py ENSURES everything is set up when app starts

## Key Concepts

### Connection Pooling
Instead of creating a new database connection for every request (slow),
the engine maintains a pool of 20 ready-to-use connections.
Requests borrow a connection and return it when done.

### Session Lifecycle
1. Request comes in → new session opened
2. Route handler uses session
3. Response sent → session closed
4. Connection returns to pool

### Why autocommit=False
Allows batching multiple operations into one transaction.
If any step fails, everything rolls back.
Critical for data integrity (ticket + first comment must save together).