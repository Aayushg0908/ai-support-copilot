"""
Dashboard API endpoints.

Read-only endpoints that return aggregated statistics
for the organization's dashboard.

Public URLs:
GET /api/v1/dashboard/stats              - Overall ticket statistics
GET /api/v1/dashboard/trends             - Ticket creation/resolution trends
GET /api/v1/dashboard/agent-performance  - Per-agent metrics
GET /api/v1/dashboard/categories         - Category distribution
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.database import get_current_org_id
from app.api.deps.auth import get_current_user
from app.models.user import User
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_ticket_stats(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get overall ticket statistics.
    
    Returns:
    - Total tickets in the organization
    - Open tickets count
    - Resolved today count
    - Breakdown by status (open, in_progress, resolved, closed)
    - Breakdown by priority (low, medium, high, critical)
    - Average resolution time in hours
    
    This is the main dashboard overview card data.
    """
    stats = dashboard_service.get_ticket_stats(db, org_id)
    return {"success": True, "data": stats}


@router.get("/trends")
def get_ticket_trends(
    days: int = Query(30, ge=7, le=365, description="Number of days to include"),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get ticket creation and resolution trends.
    
    Returns daily counts for the specified number of days.
    Used for line charts showing:
    - How many tickets created each day
    - How many tickets resolved each day
    
    Query params:
    - days: Number of days to look back (7-365, default 30)
    """
    trends = dashboard_service.get_ticket_trends(db, org_id, days=days)
    return {"success": True, "data": trends}


@router.get("/agent-performance")
def get_agent_performance(
    days: int = Query(30, ge=7, le=365, description="Period to measure"),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get performance metrics for each agent.
    
    Returns per-agent stats:
    - Tickets assigned
    - Tickets resolved
    - Resolution rate (percentage)
    - Comments written
    - Average response time
    
    Sorted by most resolved tickets.
    """
    performance = dashboard_service.get_agent_performance(db, org_id, days=days)
    return {"success": True, "data": performance}


@router.get("/categories")
def get_category_distribution(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """
    Get ticket distribution by category.
    
    Returns count of tickets in each category.
    Useful for pie charts and bar charts.
    """
    categories = dashboard_service.get_category_distribution(db, org_id)
    return {"success": True, "data": categories}

@router.get("/sla/stats")
def get_sla_stats(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get overall SLA compliance statistics."""
    from app.services.sla_service import sla_service
    
    stats = sla_service.get_sla_stats(db, org_id)
    return {"success": True, "data": stats}


@router.get("/sla/tickets/{ticket_id}")
def get_ticket_sla(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get SLA status for a specific ticket."""
    from app.services.sla_service import sla_service
    from app.services.ticket_service import ticket_service
    
    ticket = ticket_service.get_by_id(db, ticket_id, org_id)
    sla_status = sla_service.get_ticket_sla_status(db, ticket)
    
    return {"success": True, "data": sla_status}

@router.get("/analytics/weekly")
def get_weekly_trends(
    weeks: int = Query(12, ge=4, le=52),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get weekly ticket trends."""
    trends = dashboard_service.get_weekly_trends(db, org_id, weeks)
    return {"success": True, "data": trends}


@router.get("/analytics/categories")
def get_category_analytics(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get category breakdown with resolution times."""
    data = dashboard_service.get_category_analytics(db, org_id)
    return {"success": True, "data": data}


@router.get("/analytics/peak-hours")
def get_peak_hours(
    days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get ticket volume by hour and day."""
    data = dashboard_service.get_peak_hours(db, org_id, days)
    return {"success": True, "data": data}


@router.get("/analytics/resolution")
def get_resolution_efficiency(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_current_org_id),
    current_user: User = Depends(get_current_user),
):
    """Get resolution efficiency metrics."""
    data = dashboard_service.get_resolution_efficiency(db, org_id)
    return {"success": True, "data": data}