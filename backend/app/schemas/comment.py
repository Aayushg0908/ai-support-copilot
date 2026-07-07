"""
Pydantic schemas for Comment requests and responses.

Handles both flat comments and threaded (nested) replies.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════

class CommentCreateRequest(BaseModel):
    """
    Create a new comment on a ticket.
    
    body is required. parent_id is for threaded replies.
    is_internal hides the comment from customers.
    """
    body: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[UUID] = None  # For replies
    is_internal: bool = False


class CommentUpdateRequest(BaseModel):
    """Edit an existing comment. Only body can be changed."""
    body: str = Field(..., min_length=1, max_length=5000)


# ═══════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════

class CommentResponse(BaseModel):
    """
    Comment data returned in API responses.
    
    Includes user info and can nest replies when used
    in threaded contexts.
    """
    id: UUID
    ticket_id: UUID
    user_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime
    
    # User info (populated by service)
    user_name: Optional[str] = None
    
    # Nested replies (for threaded view)
    replies: list["CommentResponse"] = []
    
    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    """Wrapper for paginated comment list."""
    comments: list[CommentResponse]
    total: int
    page: int
    per_page: int


class CommentMessageResponse(BaseModel):
    """Simple message response."""
    success: bool = True
    message: str