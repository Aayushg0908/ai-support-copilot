"""
Pydantic schemas for AI endpoints.
"""

from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════

class AIClassifyRequest(BaseModel):
    """Request to classify a ticket."""
    pass  # No extra fields needed - uses ticket ID from URL


class AISearchRequest(BaseModel):
    """Search for similar tickets by text."""
    query: str = Field(..., min_length=10, max_length=1000)
    top_k: int = Field(5, ge=1, le=10)


class AIGenerateReplyRequest(BaseModel):
    """Request to generate an AI reply."""
    include_similar: bool = Field(True, description="Use similar tickets as context")


# ═══════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════

class AIClassifyResponse(BaseModel):
    """Response from ticket classification."""
    category: str
    priority: str
    confidence: float
    message: str = "Classification complete"


class AIPriorityResponse(BaseModel):
    """Response from priority prediction."""
    priority: str
    confidence: float


class SimilarTicket(BaseModel):
    """A single similar ticket result."""
    id: str
    title: str
    status: str
    priority: str
    similarity: float
    resolution: Optional[str] = None
    created_at: Optional[str] = None


class AISimilarResponse(BaseModel):
    """Response containing similar tickets."""
    ticket_id: str
    similar_tickets: List[SimilarTicket]
    total_found: int


class AIReplyResponse(BaseModel):
    """Response from AI reply generation."""
    reply: str
    confidence: float
    sources_used: List[str] = []
    tone: str = "neutral"


class AISearchResponse(BaseModel):
    """Response from text-based similar ticket search."""
    query: str
    results: List[SimilarTicket]
    total_found: int
    
class AISentimentResponse(BaseModel):
    """Response from sentiment analysis."""
    sentiment: str
    score: float
    explanation: Optional[str] = None

class AIEscalationResponse(BaseModel):
    """Response from escalation prediction."""
    escalation_risk: str
    score: float
    signals: List[str] = []
    explanation: Optional[str] = None


class AIHealthScoreResponse(BaseModel):
    """Response from health score calculation."""
    score: int
    status: str
    metrics: dict

class RootCauseResponse(BaseModel):
    """Response from root cause detection."""
    root_causes: list = []


class TicketRootCauseResponse(BaseModel):
    """Root cause for a single ticket."""
    ticket_id: str
    related_tickets: list = []
    total_related: int = 0    