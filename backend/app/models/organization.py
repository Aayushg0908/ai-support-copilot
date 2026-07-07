"""
Organization database model.

Represents the organizations table in PostgreSQL.
Each organization is a separate tenant with its own
users, tickets, and settings.
"""

from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    """
    Organizations table - the top-level tenant container.
    
    Everything in the app belongs to an organization:
    - Users belong to an org
    - Tickets belong to an org
    - Comments belong to tickets which belong to an org
    
    This enables multi-tenancy: Acme Corp and Beta Inc
    can use the same app without seeing each other's data.
    """
    __tablename__ = "organizations"
    
    # Display name of the company
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # URL-safe identifier (auto-generated from name)
    # Example: "Acme Corp" → "acme-corp"
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Soft delete - organizations can be disabled
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Flexible settings stored as JSON
    # Example: {"ticket_prefix": "TICKET", "timezone": "US/Eastern"}
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    # ──────────────────────────────────────────────
    # Relationships
    # ──────────────────────────────────────────────
    # back_populates links to User.organization
    # This gives us: organization.users → list of all users in the org
    users = relationship(
        "User",
        back_populates="organization",
    )
    
    # All tickets belonging to this organization
    tickets = relationship(
        "Ticket",
        back_populates="organization",
    )
    
    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, slug={self.slug})>"