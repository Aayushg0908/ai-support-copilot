"""
Pydantic schemas for Organization requests and responses.

Controls what data flows in and out of the API.
Separate from the model to:
1. Hide internal fields from API responses
2. Validate input differently than database constraints
3. Allow different fields for create vs update
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# REQUEST SCHEMAS (What the client sends to us)
# ═══════════════════════════════════════════════════════════

class OrganizationCreateRequest(BaseModel):
    """
    Fields required to create a new organization.
    
    Only needs a name. Slug and settings are auto-generated.
    """
    name: str = Field(..., min_length=2, max_length=255)
    # Optional: allow setting a custom slug
    slug: Optional[str] = Field(None, min_length=2, max_length=100)


class OrganizationUpdateRequest(BaseModel):
    """
    Fields that can be updated after creation.
    All optional - client sends only what changed.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None
    settings: Optional[dict] = None


# ═══════════════════════════════════════════════════════════
# RESPONSE SCHEMAS (What we send back to the client)
# ═══════════════════════════════════════════════════════════

class OrganizationResponse(BaseModel):
    """
    Organization data returned in API responses.
    
    Includes everything EXCEPT sensitive internal data.
    Users list is NOT included here - it's a separate endpoint
    to avoid loading too much data in one request.
    """
    id: UUID
    name: str
    slug: str
    is_active: bool
    settings: dict
    created_at: datetime
    updated_at: datetime
    
    # Allows creating this from SQLAlchemy ORM objects directly
    model_config = {"from_attributes": True}


class OrganizationDetailResponse(OrganizationResponse):
    """
    Extended organization response that includes user count.
    Used when fetching a single organization's details.
    """
    user_count: int = 0


class OrganizationListResponse(BaseModel):
    """
    Wrapper for paginated organization list.
    Includes metadata about the list itself.
    """
    organizations: list[OrganizationResponse]
    total: int
    page: int
    per_page: int


class OrganizationMessageResponse(BaseModel):
    """Simple message response for delete/status operations."""
    success: bool = True
    message: str