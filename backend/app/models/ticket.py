"""
Ticket database model.

The central model of the entire application.
Every support request is a ticket. Everything else
(comments, AI features, analytics) revolves around tickets.

Tickets belong to organizations and are created by users.
They track the full lifecycle of a support request from
creation to resolution.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
import enum

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
# from pgvector.sqlalchemy import Vector

from app.db.base import Base


# ──────────────────────────────────────────────
# Enums for ticket fields
# ──────────────────────────────────────────────

class TicketStatus(str, enum.Enum):
    """Possible states a ticket can be in."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    """How urgent the ticket is."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, enum.Enum):
    """Type of ticket for organization."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    SUPPORT = "support"
    BILLING = "billing"
    ACCOUNT = "account"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ONBOARDING = "onboarding"
    INTEGRATION = "integration"
    REFUND = "refund"
    GENERAL_INQUIRY = "general_inquiry"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    OTHER = "other"


class TicketSentiment(str, enum.Enum):
    """Customer sentiment detected from ticket content."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Ticket(Base):
    """
    Tickets table - the heart of the support system.
    
    Tracks every support request from creation to resolution.
    Includes AI-predicted fields that will be populated by
    the AI engine in Phase 2.
    """
    __tablename__ = "tickets"
    
    # ──────────────────────────────────────────────
    # Organization & User Foreign Keys
    # ──────────────────────────────────────────────
    
    # Which organization owns this ticket
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Who created the ticket
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Who is working on it (nullable - may be unassigned)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # ──────────────────────────────────────────────
    # Core Ticket Fields
    # ──────────────────────────────────────────────
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True,
    )
    
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    
    # Manual category set by user (can be overridden by AI)
    category: Mapped[Optional[TicketCategory]] = mapped_column(
        SAEnum(TicketCategory),
        nullable=True,
    )
    
    # Flexible tags like ["urgent", "vip-customer", "needs-review"]
    tags: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=list,
    )
    
    # ──────────────────────────────────────────────
    # AI-Predicted Fields (populated in Phase 2)
    # ──────────────────────────────────────────────
    
    # AI prediction for category
    ai_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # AI prediction for priority
    ai_priority: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # How confident the AI is (0.0 to 1.0)
    ai_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    # Customer sentiment from text analysis
    sentiment: Mapped[Optional[TicketSentiment]] = mapped_column(
        SAEnum(TicketSentiment),
        nullable=True,
    )
    
    # Numerical sentiment score (-1.0 negative to 1.0 positive)
    sentiment_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    # Customer health score (0-100)
    health_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Vector embedding for similarity search
    # 384 dimensions from sentence-transformers model
    # embedding: Mapped[Optional[list[float]]] = mapped_column(
    #     Vector(384),
    #     nullable=True,
    # )
    
    # ──────────────────────────────────────────────
    # Timestamps
    # ──────────────────────────────────────────────
    
    # When the ticket was resolved (for SLA tracking)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # ──────────────────────────────────────────────
    # Relationships
    # ──────────────────────────────────────────────
    
    # The organization this ticket belongs to
    organization = relationship(
        "Organization",
        back_populates="tickets",
    )
    
    # The user who created this ticket
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_tickets",
    )
    
    # The user assigned to this ticket
    assignee = relationship(
        "User",
        foreign_keys=[assigned_to],
        back_populates="assigned_tickets",
    )
    
    # Comments on this ticket
    comments = relationship(
        "Comment",
        back_populates="ticket",
        order_by="Comment.created_at",
    )
    
    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, title={self.title[:30]}..., status={self.status})>"
    
    @property
    def is_overdue(self) -> bool:
        """
        Check if ticket is overdue based on priority.
        
        SLA targets:
        - Critical: 4 hours
        - High: 24 hours
        - Medium: 72 hours
        - Low: 1 week
        """
        if self.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            return False
        
        sla_hours = {
            TicketPriority.CRITICAL: 4,
            TicketPriority.HIGH: 24,
            TicketPriority.MEDIUM: 72,
            TicketPriority.LOW: 168,  # 7 days
        }
        
        max_hours = sla_hours.get(self.priority, 72)
        age = datetime.now(timezone.utc) - self.created_at
        return age.total_seconds() / 3600 > max_hours