"""
Pydantic schemas for audit logs.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Single audit log entry."""
    id: UUID
    org_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: UUID
    changes: Optional[dict] = {}
    description: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""
    logs: list[AuditLogResponse]
    total: int
    page: int
    per_page: int


class TicketHistoryResponse(BaseModel):
    """Complete history for a ticket."""
    ticket_id: UUID
    history: list[AuditLogResponse]
    total_events: int