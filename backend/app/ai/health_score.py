"""
Customer health score calculator.

Combines multiple signals into a single 0-100 score:
- Ticket volume and trends
- Sentiment analysis
- Resolution times
- Escalation history
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User


class HealthScoreCalculator:
    def calculate(self, db: Session, org_id: str) -> dict:
        """Calculate health score for an organization."""
        
        # Get all tickets for the org
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id
        ).all()
        
        if not tickets:
            return {"score": 100, "status": "healthy", "metrics": {}}
        
        total = len(tickets)
        open_tickets = sum(1 for t in tickets if t.status in (TicketStatus.OPEN, TicketStatus.IN_PROGRESS))
        resolved_tickets = sum(1 for t in tickets if t.status == TicketStatus.RESOLVED)
        closed_tickets = sum(1 for t in tickets if t.status == TicketStatus.CLOSED)
        
        # Sentiment metrics
        negative_tickets = sum(1 for t in tickets if t.sentiment == "negative")
        positive_tickets = sum(1 for t in tickets if t.sentiment == "positive")
        
        # Resolution ratio
        resolved_ratio = (resolved_tickets + closed_tickets) / total if total > 0 else 1.0
        
        # Sentiment ratio
        sentiment_ratio = positive_tickets / total if total > 0 else 1.0
        
        # Open ticket penalty
        open_penalty = min(open_tickets * 2, 40)  # Max 40 point penalty
        
        # Negative sentiment penalty
        negative_penalty = min(negative_tickets * 3, 30)  # Max 30 point penalty
        
        # Calculate score
        score = 100
        score -= open_penalty
        score -= negative_penalty
        score -= (1.0 - resolved_ratio) * 20  # Up to 20 point penalty for low resolution
        score += (sentiment_ratio) * 10  # Up to 10 point bonus for positive sentiment
        
        score = max(0, min(100, int(score)))
        
        if score >= 70:
            status = "healthy"
        elif score >= 40:
            status = "at_risk"
        else:
            status = "critical"
        
        return {
            "score": score,
            "status": status,
            "metrics": {
                "total_tickets": total,
                "open_tickets": open_tickets,
                "resolved_tickets": resolved_tickets,
                "negative_tickets": negative_tickets,
                "positive_tickets": positive_tickets,
                "resolution_ratio": round(resolved_ratio, 2),
            }
        }


health_calculator = HealthScoreCalculator()