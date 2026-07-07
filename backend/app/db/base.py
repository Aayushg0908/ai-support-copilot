"""
Base class for all database models in the application.

Purpose:
- Provides common columns (id, created_at, updated_at) to every table
- Ensures consistent data types across all models
- Single place to change database-wide behavior

How it works:
Every model we create (User, Ticket, Comment, etc.) inherits from this class.
They automatically get id, created_at, and updated_at columns without
declaring them again.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    The parent class that every database model inherits from.
    
    DeclarativeBase is SQLAlchemy's modern way of defining models.
    It allows us to use type hints and mapped_column() instead of
    the older Column() style, giving us better IDE support.
    
    Columns provided to every child model:
    - id: UUID primary key, auto-generated
    - created_at: Timestamp set once when record is created
    - updated_at: Timestamp that updates every time record is modified
    """
    
    # ──────────────────────────────────────────────
    # id: Unique identifier for every row
    # ──────────────────────────────────────────────
    # Why UUID instead of auto-increment integer?
    # 1. Security: /users/1, /users/2 lets anyone guess valid IDs
    #    /users/a1b2c3d4-... is impossible to guess
    # 2. Distributed systems: If we ever use multiple databases,
    #    UUIDs won't collide. Auto-increment IDs would.
    # 3. Frontend can generate UUIDs before saving to database
    #    (useful for optimistic UI updates)
    #
    # server_default="uuid_generate_v4()" tells PostgreSQL
    # to generate the UUID if we don't provide one.
    # This requires the uuid-ossp extension enabled.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),  # Use PostgreSQL built-in function
    )
    
    # ──────────────────────────────────────────────
    # created_at: When was this record first saved?
    # ──────────────────────────────────────────────
    # Uses timezone-aware timestamps (timezone=True).
    # Always store in UTC, convert to local time in frontend.
    # 
    # default=lambda: datetime.now(timezone.utc)
    # The lambda ensures the function is called fresh each time.
    # If we wrote default=datetime.now(timezone.utc) without lambda,
    # it would use the time when the CLASS was defined, not when
    # the record was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    
    # ──────────────────────────────────────────────
    # updated_at: When was this record last modified?
    # ──────────────────────────────────────────────
    # Same as created_at, but the onupdate parameter
    # automatically changes this value every time
    # the row is updated in the database.
    #
    # No need to manually set updated_at in your code.
    # SQLAlchemy handles it automatically.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )