"""
Audit log database model.

Tracks every important action in the system for:
- Security monitoring
- Compliance (GDPR, ISO)
- Debugging
- Customer dispute resolution
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditLog(Base):
    """
    Audit logs table - immutable record of all actions.
    
    Each row captures:
    - Who performed the action
    - What action was performed
    - Which resource was affected
    - What changed (before/after)
    - When it happened
    """
    __tablename__ = "audit_logs"
    
    # Who did it
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Which organization
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # What happened
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # What type of record (ticket, user, organization, comment)
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Which specific record
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # What changed (JSON with old/new values)
    changes: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=True,
    )
    
    # Optional: IP address for security
    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 can be up to 45 chars
        nullable=True,
    )
    
    # Optional: Additional context
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    
    def __repr__(self) -> str:
        return f"<AuditLog({self.action} on {self.resource_type} by {self.user_id})>"