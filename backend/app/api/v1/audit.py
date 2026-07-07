"""
Audit log API endpoints.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.database import get_current_org_id
from app.api.deps.auth import get_current_user
from app.models.user import User
from app.schemas.audit import (
    AuditLogResponse,
    AuditLogListResponse,
    TicketHistoryResponse,
)
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=AuditLogListResponse)
def get_audit_logs(
    resource_type: Optional[str] = Query(None, description="ticket, user, comment"),
    resource_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    action: Optional[str] = Query(None, description="created, updated, deleted"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get audit logs with optional filters.
    
    Filter by:
    - resource_type: ticket, user, comment, organization
    - resource_id: specific record ID
    - user_id: actions by specific user
    - action: created, updated, deleted, login, etc.
    """
    logs, total = audit_service.get_logs(
        db=db,
        org_id=org_id,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        action=action,
        page=page,
        per_page=per_page,
    )
    
    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/tickets/{ticket_id}/history", response_model=TicketHistoryResponse)
def get_ticket_history(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete audit history for a specific ticket.
    
    Shows every action: creation, status changes,
    assignments, updates, etc.
    """
    history = audit_service.get_ticket_history(db, ticket_id, org_id)
    
    return TicketHistoryResponse(
        ticket_id=ticket_id,
        history=[AuditLogResponse.model_validate(h) for h in history],
        total_events=len(history),
    )