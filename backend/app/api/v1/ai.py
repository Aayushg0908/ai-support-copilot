"""
AI API endpoints.

Public URLs for AI features:
POST   /api/v1/tickets/{id}/classify        - Classify a ticket
POST   /api/v1/tickets/{id}/predict-priority - Predict priority only
GET    /api/v1/tickets/{id}/similar          - Find similar tickets
POST   /api/v1/tickets/{id}/generate-reply   - Generate AI reply draft
POST   /api/v1/ai/search                     - Search tickets by text
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.database import get_current_org_id
from app.api.deps.auth import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AIClassifyResponse,
    AIPriorityResponse,
    AISimilarResponse,
    AIReplyResponse,
    AISearchRequest,
    AISearchResponse,
    AIGenerateReplyRequest,
    AISentimentResponse,
    AIEscalationResponse,
    AIHealthScoreResponse,
    RootCauseResponse,
    TicketRootCauseResponse,
)
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/tickets/{ticket_id}/classify",
    response_model=AIClassifyResponse,
)
def classify_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Classify a ticket using AI.
    
    Determines:
    - Category (bug, support, billing, etc.)
    - Priority (low, medium, high, critical)
    
    Results are saved to the ticket automatically.
    """
    result = ai_service.classify_ticket(db, ticket_id, org_id)
    return result


@router.post(
    "/tickets/{ticket_id}/predict-priority",
    response_model=AIPriorityResponse,
)
def predict_priority(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Predict only the priority for a ticket.
    
    Faster than full classification. Use when category
    is already set but priority needs AI input.
    """
    result = ai_service.predict_priority(db, ticket_id, org_id)
    return result


@router.get(
    "/tickets/{ticket_id}/similar",
    response_model=AISimilarResponse,
)
def find_similar_tickets(
    ticket_id: UUID,
    top_k: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Find tickets similar to the given ticket.
    
    Uses semantic similarity to find tickets with
    similar meaning, not just matching keywords.
    """
    results = ai_service.find_similar_tickets(
        db=db,
        ticket_id=ticket_id,
        org_id=org_id,
        top_k=top_k,
    )
    
    return AISimilarResponse(
        ticket_id=str(ticket_id),
        similar_tickets=results,
        total_found=len(results),
    )


@router.post(
    "/tickets/{ticket_id}/generate-reply",
    response_model=AIReplyResponse,
)
def generate_reply(
    ticket_id: UUID,
    request: AIGenerateReplyRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI reply draft for a ticket.
    
    Uses similar resolved tickets as context to
    create a helpful, professional response.
    """
    result = ai_service.generate_reply(
        db=db,
        ticket_id=ticket_id,
        org_id=org_id,
        include_similar=request.include_similar,
    )
    return result

@router.post(
    "/tickets/{ticket_id}/analyze-sentiment",
    response_model=AISentimentResponse,
)
def analyze_sentiment(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze the sentiment of a ticket.
    
    Returns emotional tone (positive/neutral/negative)
    and a score from -1.0 to 1.0.
    """
    result = ai_service.analyze_sentiment(db, ticket_id, org_id)
    return result

@router.post(
    "/tickets/{ticket_id}/predict-escalation",
    response_model=AIEscalationResponse,
)
def predict_escalation(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Predict if a ticket is likely to escalate."""
    result = ai_service.predict_escalation(db, ticket_id, org_id)
    return result


@router.get(
    "/health-score",
    response_model=AIHealthScoreResponse,
)
def get_health_score(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get health score for current organization."""
    result = ai_service.get_health_score(db, org_id)
    return result

@router.get("/root-causes", response_model=RootCauseResponse)
def find_root_causes(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Find root causes by grouping similar tickets."""
    results = ai_service.find_root_causes(db, org_id)
    return RootCauseResponse(root_causes=results)


@router.get(
    "/tickets/{ticket_id}/root-cause",
    response_model=TicketRootCauseResponse,
)
def find_ticket_root_cause(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Find tickets related to this ticket."""
    result = ai_service.find_root_cause_for_ticket(db, ticket_id, org_id)
    return result

@router.post(
    "/search",
    response_model=AISearchResponse,
)
def search_similar_tickets(
    request: AISearchRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Search for tickets similar to a text query.
    
    Use this before creating a new ticket to check
    if the issue has already been reported.
    """
    results = ai_service.search_similar_tickets(
        db=db,
        org_id=org_id,
        query_text=request.query,
        top_k=request.top_k,
    )
    
    return AISearchResponse(
        query=request.query,
        results=results,
        total_found=len(results),
    )
    