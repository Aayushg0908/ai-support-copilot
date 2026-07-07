"""
Comment database model.

Represents comments on tickets. Supports:
- Top-level comments on tickets
- Threaded replies (comment on another comment)
- Internal notes (only visible to agents, not customers)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Comment(Base):
    """
    Comments table - stores all communication on tickets.
    
    Self-referential relationship via parent_id enables
    threaded conversations:
    
    Comment 1 (parent_id = null)
      ├── Reply A (parent_id = 1)
      │     └── Reply to A (parent_id = reply_a.id)
      └── Reply B (parent_id = 1)
    """
    __tablename__ = "comments"
    
    # ──────────────────────────────────────────────
    # Foreign Keys
    # ──────────────────────────────────────────────
    
    # Which ticket this comment belongs to
    # CASCADE: if ticket is deleted, all comments go too
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Who wrote this comment
    # SET NULL: if user deleted, comment stays but shows "Deleted User"
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # For threaded replies - points to parent comment
    # NULL means this is a top-level comment
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    
    # ──────────────────────────────────────────────
    # Content Fields
    # ──────────────────────────────────────────────
    
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Internal notes are only visible to agents/admins
    # Used for team communication without customer seeing
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # ──────────────────────────────────────────────
    # Timestamps
    # ──────────────────────────────────────────────
    # (id, created_at, updated_at come from Base)
    
    # ──────────────────────────────────────────────
    # Relationships
    # ──────────────────────────────────────────────
    
    # The ticket this comment belongs to
    ticket = relationship(
        "Ticket",
        back_populates="comments",
    )
    
    # The user who wrote this comment
    user = relationship(
        "User",
        back_populates="comments",
    )
    
    # Parent comment (for threaded replies)
    parent = relationship(
        "Comment",
        remote_side="Comment.id",  # Points to self
        back_populates="replies",
    )
    
    # Child replies to this comment
    replies = relationship(
        "Comment",
        back_populates="parent",
    )
    
    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, ticket_id={self.ticket_id}, is_internal={self.is_internal})>"