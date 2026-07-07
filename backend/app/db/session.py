"""
Database session management.

This file handles:
1. Creating the database engine (connection to PostgreSQL)
2. Creating session factories (to open/close database conversations)
3. Providing a FastAPI dependency for clean session handling

Why sessions matter:
Every database operation happens inside a session. When you query
users or create tickets, you're working within a session that
manages transactions and ensures data consistency.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings


# ──────────────────────────────────────────────
# ENGINE: The actual connection to PostgreSQL
# ──────────────────────────────────────────────
# create_engine() takes the database URL and sets up
# the connection pool. The engine is created ONCE
# when the app starts and reused for all requests.
#
# pool_size=20 means up to 20 simultaneous connections.
# If all 20 are in use, new requests wait in queue.
# This prevents overwhelming the database.
#
# pool_pre_ping=True tests connections before using them.
# If a connection died (DB restart), it creates a fresh one.
# This prevents errors from stale connections.
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,            # Max simultaneous connections
    max_overflow=10,         # Extra connections if pool is full
    pool_pre_ping=True,      # Verify connection is alive before using
    echo=settings.DEBUG,     # Print SQL queries when debugging
)


# ──────────────────────────────────────────────
# SESSION FACTORY: Creates new database sessions
# ──────────────────────────────────────────────
# SessionLocal is a class. Each time you call SessionLocal(),
# you get a fresh session connected to the database.
#
# autocommit=False means changes don't save until you
# explicitly call session.commit(). This is important for
# data integrity - if something fails mid-operation,
# nothing gets saved.
#
# autoflush=False means SQLAlchemy won't automatically
# push changes to the database before queries. We control
# when flushes happen.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ──────────────────────────────────────────────
# DEPENDENCY: FastAPI dependency injection
# ──────────────────────────────────────────────
# This is the function that FastAPI calls for every request.
# It creates a session, gives it to the route handler,
# and automatically closes it when the request is done.
#
# Using yield instead of return means:
# 1. Everything before yield runs when the request starts
# 2. The session is passed to the route handler
# 3. Everything after yield runs when the request ends
#    (even if there was an error!)
#
# This ensures sessions are ALWAYS closed, preventing
# connection leaks that would crash the app over time.
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    Usage in a route:
        @router.get("/tickets")
        def get_tickets(db: Session = Depends(get_db)):
            tickets = db.query(Ticket).all()
            return tickets
    
    The session automatically closes when the request completes,
    even if an error occurred during processing.
    """
    db = SessionLocal()
    try:
        yield db           # Give session to the route handler
    finally:
        db.close()         # Always close, even on errors