"""
SLA (Service Level Agreement) tracking service.

Tracks response and resolution times against targets.
Uses existing ticket timestamps - no new database table needed.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.comment import Comment


# SLA targets in hours
SLA_TARGETS = {
    "critical": {"first_response": 0.5, "resolution": 4},   # 30 min / 4 hours
    "high": {"first_response": 1, "resolution": 8},          # 1 hour / 8 hours
    "medium": {"first_response": 4, "resolution": 24},       # 4 hours / 24 hours
    "low": {"first_response": 8, "resolution": 72},          # 8 hours / 72 hours
}


class SLAService:
    """Tracks SLA compliance for tickets."""
    
    def get_deadline(self, ticket: Ticket) -> Dict:
        """
        Calculate SLA deadlines for a ticket.
        
        Returns first_response_deadline and resolution_deadline.
        """
        targets = SLA_TARGETS.get(ticket.priority.value, SLA_TARGETS["medium"])
        
        first_response_deadline = ticket.created_at + timedelta(
            hours=targets["first_response"]
        )
        resolution_deadline = ticket.created_at + timedelta(
            hours=targets["resolution"]
        )
        
        return {
            "first_response_deadline": first_response_deadline.isoformat(),
            "resolution_deadline": resolution_deadline.isoformat(),
            "targets": targets,
        }
    
    def get_ticket_sla_status(self, db: Session, ticket: Ticket) -> Dict:
        """
        Get SLA status for a single ticket.
        
        Returns:
        - sla_status: "within_sla", "at_risk", "breached", "resolved"
        - first_response_status: "met", "pending", "breached"
        - resolution_status: "met", "pending", "breached"
        - time_remaining or time_overdue
        """
        targets = SLA_TARGETS.get(ticket.priority.value, SLA_TARGETS["medium"])
        now = datetime.now(timezone.utc)
        
        # First response check
        first_comment = db.query(Comment).filter(
            Comment.ticket_id == ticket.id,
            Comment.is_internal == False,
        ).order_by(Comment.created_at).first()
        
        first_response_deadline = ticket.created_at + timedelta(hours=targets["first_response"])
        
        if first_comment:
            if first_comment.created_at <= first_response_deadline:
                first_response_status = "met"
            else:
                first_response_status = "breached"
        else:
            if now > first_response_deadline:
                first_response_status = "breached"
            elif now + timedelta(hours=1) > first_response_deadline:
                first_response_status = "at_risk"
            else:
                first_response_status = "pending"
        
        # Resolution check
        resolution_deadline = ticket.created_at + timedelta(hours=targets["resolution"])
        
        if ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            resolved_at = ticket.resolved_at or ticket.updated_at
            if resolved_at <= resolution_deadline:
                resolution_status = "met"
            else:
                resolution_status = "breached"
        else:
            if now > resolution_deadline:
                resolution_status = "breached"
            elif now + timedelta(hours=2) > resolution_deadline:
                resolution_status = "at_risk"
            else:
                resolution_status = "pending"
        
        # Overall status
        if ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            sla_status = "resolved"
        elif first_response_status == "breached" or resolution_status == "breached":
            sla_status = "breached"
        elif first_response_status == "at_risk" or resolution_status == "at_risk":
            sla_status = "at_risk"
        else:
            sla_status = "within_sla"
        
        # Calculate time remaining or overdue
        if now < resolution_deadline:
            time_remaining_hours = (resolution_deadline - now).total_seconds() / 3600
        else:
            time_remaining_hours = -(now - resolution_deadline).total_seconds() / 3600
        
        return {
            "ticket_id": str(ticket.id),
            "title": ticket.title,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "sla_status": sla_status,
            "first_response": first_response_status,
            "resolution": resolution_status,
            "first_response_deadline": first_response_deadline.isoformat(),
            "resolution_deadline": resolution_deadline.isoformat(),
            "time_remaining_hours": round(time_remaining_hours, 1),
            "first_comment_at": first_comment.created_at.isoformat() if first_comment else None,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        }
    
    def get_sla_stats(self, db: Session, org_id: UUID) -> Dict:
        """
        Get overall SLA statistics for an organization.
        
        Returns:
        - Total tickets
        - SLA compliance percentage
        - Counts by status (within_sla, breached, at_risk)
        - Average response and resolution times
        """
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id
        ).all()
        
        if not tickets:
            return {
                "total_tickets": 0,
                "compliance_rate": 100,
                "within_sla": 0,
                "breached": 0,
                "at_risk": 0,
                "resolved": 0,
                "avg_response_hours": 0,
                "avg_resolution_hours": 0,
            }
        
        stats = {"within_sla": 0, "breached": 0, "at_risk": 0, "resolved": 0}
        response_times = []
        resolution_times = []
        
        for ticket in tickets:
            sla = self.get_ticket_sla_status(db, ticket)
            stats[sla["sla_status"]] += 1
            
            # Collect response times
            if sla["first_comment_at"]:
                first_comment = datetime.fromisoformat(sla["first_comment_at"])
                response_hours = (first_comment - ticket.created_at).total_seconds() / 3600
                response_times.append(response_hours)
            
            # Collect resolution times
            if sla["resolved_at"]:
                resolved = datetime.fromisoformat(sla["resolved_at"])
                resolution_hours = (resolved - ticket.created_at).total_seconds() / 3600
                resolution_times.append(resolution_hours)
        
        total = len(tickets)
        non_resolved = stats["within_sla"] + stats["breached"] + stats["at_risk"]
        compliance_rate = round((stats["within_sla"] / non_resolved * 100) if non_resolved > 0 else 100, 1)
        
        avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0
        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0
        
        return {
            "total_tickets": total,
            "compliance_rate": compliance_rate,
            "within_sla": stats["within_sla"],
            "breached": stats["breached"],
            "at_risk": stats["at_risk"],
            "resolved": stats["resolved"],
            "avg_response_hours": avg_response,
            "avg_resolution_hours": avg_resolution,
        }


# Module-level singleton
sla_service = SLAService()