"""
Pydantic schemas for Ticket requests and responses.

Controls data validation for ticket operations:
- Creating tickets (title + description required)
- Updating tickets (all fields optional)
- Listing tickets (with filters and pagination)
- AI-related responses (for Phase 2)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════

class TicketCreateRequest(BaseModel):
    """
    Fields required to create a new ticket.
    
    Only title and description are mandatory.
    Category, priority, and tags are optional with defaults.
    """
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    category: Optional[str] = Field(
        None,
        pattern="^(bug|feature_request|support|billing|account|performance|security|onboarding|integration|refund|general_inquiry|complaint|feedback|other)$"
    )
    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high|critical)$"
    )
    assigned_to: Optional[UUID] = None
    tags: Optional[list[str]] = []


class TicketUpdateRequest(BaseModel):
    """
    Fields that can be updated after creation.
    All optional - only send what changed.
    """
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    description: Optional[str] = Field(None, min_length=10)
    status: Optional[str] = Field(
        None,
        pattern="^(open|in_progress|resolved|closed)$"
    )
    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high|critical)$"
    )
    category: Optional[str] = Field(
        None,
        pattern="^(bug|feature_request|support|billing|account|performance|security|onboarding|integration|refund|general_inquiry|complaint|feedback|other)$"
    )
    assigned_to: Optional[UUID] = None
    tags: Optional[list[str]] = None


# ═══════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════

class TicketResponse(BaseModel):
    """
    Ticket data returned in API responses.
    
    Includes creator and assignee info as nested objects
    so the frontend can display names without extra requests.
    """
    id: UUID
    org_id: UUID
    title: str
    description: str
    status: str
    priority: str
    category: Optional[str] = None
    tags: Optional[list] = []
    assigned_to: Optional[UUID] = None
    created_by: Optional[UUID] = None
    ai_category: Optional[str] = None
    ai_priority: Optional[str] = None
    ai_confidence: Optional[float] = None
    sentiment: Optional[str] = None
    health_score: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested user info (populated by service)
    creator_name: Optional[str] = None
    assignee_name: Optional[str] = None
    comment_count: int = 0
    
    model_config = {"from_attributes": True}


class TicketDetailResponse(TicketResponse):
    """
    Extended ticket response with AI suggestions.
    Used when viewing a single ticket in detail.
    """
    similar_tickets: list = []  # Populated in Phase 2
    ai_suggested_reply: Optional[str] = None  # Populated in Phase 2


class TicketListResponse(BaseModel):
    """Wrapper for paginated ticket list."""
    tickets: list[TicketResponse]
    total: int
    page: int
    per_page: int


class TicketStatusUpdateRequest(BaseModel):
    """Dedicated endpoint for status changes (common operation)."""
    status: str = Field(..., pattern="^(open|in_progress|resolved|closed)$")


class TicketAssignRequest(BaseModel):
    """Dedicated endpoint for assignment changes."""
    assigned_to: UUID


class TicketMessageResponse(BaseModel):
    """Simple message response."""
    success: bool = True
    message: str