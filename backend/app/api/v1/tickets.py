"""
Ticket API endpoints.

The largest API module because tickets are the core feature.
Public URLs:
POST   /api/v1/tickets                    - Create ticket
GET    /api/v1/tickets                    - List tickets (filtered, paginated)
GET    /api/v1/tickets/{ticket_id}        - Get ticket detail
PUT    /api/v1/tickets/{ticket_id}        - Update ticket
PATCH  /api/v1/tickets/{ticket_id}/status - Quick status change
PATCH  /api/v1/tickets/{ticket_id}/assign - Quick assign
DELETE /api/v1/tickets/{ticket_id}        - Close ticket
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.database import get_current_org_id
from app.api.deps.auth import get_current_user
from app.models.user import User
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse,
    TicketDetailResponse,
    TicketListResponse,
    TicketStatusUpdateRequest,
    TicketAssignRequest,
    TicketMessageResponse,
)
from app.services.ticket_service import ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    request: TicketCreateRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new support ticket.
    
    The ticket is automatically scoped to the user's organization.
    Creator is set to the currently logged-in user.
    """
    ticket = ticket_service.create(
        db=db,
        org_id=org_id,
        created_by=current_user.id,
        title=request.title,
        description=request.description,
        category=request.category,
        priority=request.priority,
        assigned_to=request.assigned_to,
        tags=request.tags,
    )
    db.commit()
    
    return TicketResponse(
        id=ticket.id,
        org_id=ticket.org_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        category=ticket.category.value if ticket.category else None,
        tags=ticket.tags,
        assigned_to=ticket.assigned_to,
        created_by=ticket.created_by,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        creator_name=current_user.full_name,
    )


@router.get(
    "/",
    response_model=TicketListResponse,
)
def list_tickets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(
        None, pattern="^(open|in_progress|resolved|closed)$"
    ),
    priority: Optional[str] = Query(
        None, pattern="^(low|medium|high|critical)$"
    ),
    category: Optional[str] = Query(
        None, pattern="^(bug|feature_request|support|billing|account|performance|security|onboarding|integration|refund|general_inquiry|complaint|feedback|other)$"
    ),
    assigned_to: Optional[UUID] = None,
    created_by: Optional[UUID] = None,
    search: Optional[str] = Query(None, min_length=2),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|priority|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    List tickets with filtering, search, and pagination.
    
    Supports:
    - Status/priority/category filters
    - Assignment and creator filters
    - Text search in title and description
    - Date range filtering
    - Custom sorting
    
    All results are scoped to the user's organization.
    """
    tickets, total = ticket_service.list_tickets(
        db=db,
        org_id=org_id,
        page=page,
        per_page=per_page,
        status=status,
        priority=priority,
        category=category,
        assigned_to=assigned_to,
        created_by=created_by,
        search=search,
        from_date=from_date,
        to_date=to_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    return TicketListResponse(
        tickets=[
            TicketResponse(
                id=t["ticket"].id,
                org_id=t["ticket"].org_id,
                title=t["ticket"].title,
                description=t["ticket"].description,
                status=t["ticket"].status.value,
                priority=t["ticket"].priority.value,
                category=t["ticket"].category.value if t["ticket"].category else None,
                tags=t["ticket"].tags,
                assigned_to=t["ticket"].assigned_to,
                created_by=t["ticket"].created_by,
                resolved_at=t["ticket"].resolved_at,
                created_at=t["ticket"].created_at,
                updated_at=t["ticket"].updated_at,
                creator_name=t["creator_name"],
                assignee_name=t["assignee_name"],
                comment_count=t["comment_count"],
            )
            for t in tickets
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
)
def get_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get full ticket details.
    
    Returns ticket data plus:
    - Creator and assignee names
    - Comment count
    - Similar tickets (Phase 2)
    - AI suggested reply (Phase 2)
    """
    result = ticket_service.get_with_relations(db, ticket_id, org_id)
    ticket = result["ticket"]
    
    return TicketDetailResponse(
        id=ticket.id,
        org_id=ticket.org_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        category=ticket.category.value if ticket.category else None,
        tags=ticket.tags,
        assigned_to=ticket.assigned_to,
        created_by=ticket.created_by,
        ai_category=ticket.ai_category,
        ai_priority=ticket.ai_priority,
        ai_confidence=ticket.ai_confidence,
        sentiment=ticket.sentiment.value if ticket.sentiment else None,
        health_score=ticket.health_score,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        creator_name=result["creator_name"],
        assignee_name=result["assignee_name"],
        comment_count=result["comment_count"],
        similar_tickets=[],  # Phase 2
        ai_suggested_reply=None,  # Phase 2
    )


@router.put(
    "/{ticket_id}",
    response_model=TicketResponse,
)
def update_ticket(
    ticket_id: UUID,
    request: TicketUpdateRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Update ticket fields.
    
    Only provided fields are changed. Send only what needs updating.
    """
    ticket = ticket_service.update(
        db=db,
        ticket_id=ticket_id,
        org_id=org_id,
        title=request.title,
        description=request.description,
        status=request.status,
        priority=request.priority,
        category=request.category,
        assigned_to=request.assigned_to,
        tags=request.tags,
    )
    db.commit()
    
    return TicketResponse(
        id=ticket.id,
        org_id=ticket.org_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        category=ticket.category.value if ticket.category else None,
        tags=ticket.tags,
        assigned_to=ticket.assigned_to,
        created_by=ticket.created_by,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
)
def update_ticket_status(
    ticket_id: UUID,
    request: TicketStatusUpdateRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Quick status change for a ticket.
    
    Common operations:
    - "Start Working" → status: in_progress
    - "Resolve" → status: resolved
    - "Reopen" → status: open
    """
    ticket = ticket_service.change_status(db, ticket_id, org_id, request.status)
    db.commit()
    
    return TicketResponse(
        id=ticket.id,
        org_id=ticket.org_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        category=ticket.category.value if ticket.category else None,
        tags=ticket.tags,
        assigned_to=ticket.assigned_to,
        created_by=ticket.created_by,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.patch(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
)
def assign_ticket(
    ticket_id: UUID,
    request: TicketAssignRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Assign a ticket to a user.
    
    Automatically sets status to in_progress when assigned.
    """
    ticket = ticket_service.assign(db, ticket_id, org_id, request.assigned_to)
    db.commit()
    
    return TicketResponse(
        id=ticket.id,
        org_id=ticket.org_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        category=ticket.category.value if ticket.category else None,
        tags=ticket.tags,
        assigned_to=ticket.assigned_to,
        created_by=ticket.created_by,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.delete(
    "/{ticket_id}",
    response_model=TicketMessageResponse,
)
def delete_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Close a ticket (soft delete).
    
    Sets status to 'closed' instead of actually deleting.
    Preserves ticket for reporting and audit purposes.
    """
    ticket_service.delete(db, ticket_id, org_id)
    db.commit()
    
    return TicketMessageResponse(
        message="Ticket closed successfully"
    )