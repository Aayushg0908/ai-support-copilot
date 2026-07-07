"""
User database model.

Represents the users table in PostgreSQL.
Every user belongs to an organization and has a role
that determines what they can access.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.base import Base


# ──────────────────────────────────────────────
# UserRole Enum: What permissions a user has
# ──────────────────────────────────────────────
# Using Python enum ensures only valid roles can be stored.
# If someone tries to set role="superadmin", it fails immediately.
#
# admin: Full access to org settings, users, all tickets
# agent: Can manage assigned tickets
# viewer: Read-only access to tickets
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"
    VIEWER = "viewer"


class User(Base):
    """
    Users table - stores authentication and profile info.
    
    Relationships:
    - Belongs to one Organization
    - Can create many Tickets
    - Can be assigned to many Tickets
    - Can write many Comments
    """
    __tablename__ = "users"
    
    # ──────────────────────────────────────────────
    # Foreign Keys
    # ──────────────────────────────────────────────
    # Every user belongs to an organization.
    # ondelete="CASCADE" means if an org is deleted,
    # all its users are deleted too.
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # ──────────────────────────────────────────────
    # Authentication Fields
    # ──────────────────────────────────────────────
    # email: Must be unique across ALL users (not just within org)
    # password_hash: Never store raw passwords. Always bcrypt hash.
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,  # We query by email on every login
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # ──────────────────────────────────────────────
    # Profile Fields
    # ──────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # ──────────────────────────────────────────────
    # Role & Status
    # ──────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole),
        default=UserRole.AGENT,
        nullable=False,
    )
    
    # Soft delete - instead of actually deleting users,
    # we set is_active=False. This preserves their tickets/comments.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Track when user last logged in (for analytics/security)
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # ──────────────────────────────────────────────
    # Relationships (connections to other tables)
    # ──────────────────────────────────────────────
    # These don't create columns. They let you do:
    # user.organization → get the org object
    # user.created_tickets → get all tickets this user created
    
    # back_populates tells SQLAlchemy this is linked to
    # Organization.users relationship (defined in organization.py)
    organization = relationship(
        "Organization",
        back_populates="users",
    )
    
    # Tickets created by this user
    created_tickets = relationship(
        "Ticket",
        foreign_keys="Ticket.created_by",
        back_populates="creator",
    )
    
    # Tickets assigned to this user
    assigned_tickets = relationship(
        "Ticket",
        foreign_keys="Ticket.assigned_to",
        back_populates="assignee",
    )
    
    # Comments written by this user
    comments = relationship(
        "Comment",
        back_populates="user",
    )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"