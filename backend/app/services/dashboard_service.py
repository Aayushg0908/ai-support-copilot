"""
Dashboard business logic.

Aggregates data from tickets, users, and comments tables
to provide dashboard statistics. All read-only operations.

Stats provided:
- Ticket counts by status
- Ticket counts by priority
- Ticket counts by category
- Average resolution time
- Tickets created over time (trends)
- Agent performance metrics
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.models.ticket import Ticket, TicketStatus
from app.models.user import User
from app.models.comment import Comment


class DashboardService:
    """Handles all dashboard aggregation queries."""
    
    def get_ticket_stats(
        self,
        db: Session,
        org_id: UUID,
    ) -> dict:
        """
        Get overall ticket statistics for an organization.
        
        Returns counts by status, priority, and category
        plus total tickets and average resolution time.
        """
        # Base query for this org's tickets
        base_query = db.query(Ticket).filter(Ticket.org_id == org_id)
        
        # Count by status
        status_counts = {}
        for status in TicketStatus:
            count = base_query.filter(Ticket.status == status).count()
            status_counts[status.value] = count
        
         # Count by priority
        priority_query = db.query(
            Ticket.priority,
            func.count(Ticket.id)
        ).filter(
            Ticket.org_id == org_id
        ).group_by(Ticket.priority).all()
        
        priority_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for priority, count in priority_query:
            priority_counts[priority.value] = count
        
        # Total tickets
        total_tickets = base_query.count()
        
        # Open tickets
        open_tickets = base_query.filter(
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        ).count()
        
        # Resolved today
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        resolved_today = base_query.filter(
            Ticket.status == TicketStatus.RESOLVED,
            Ticket.resolved_at >= today_start,
        ).count()
        
        # Average resolution time (in hours)
        avg_resolution = db.query(
            func.avg(
                func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600
            )
        ).filter(
            Ticket.org_id == org_id,
            Ticket.resolved_at.isnot(None),
        ).scalar()
        
        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_today": resolved_today,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "avg_resolution_hours": round(avg_resolution, 1) if avg_resolution else 0,
        }
    
    def get_ticket_trends(
        self,
        db: Session,
        org_id: UUID,
        days: int = 30,
    ) -> list[dict]:
        """
        Get ticket creation and resolution trends over time.
        
        Returns daily counts for the last N days.
        Used for line charts showing ticket volume.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Tickets created per day
        created_trend = db.query(
            func.date(Ticket.created_at).label("date"),
            func.count(Ticket.id).label("count"),
        ).filter(
            Ticket.org_id == org_id,
            Ticket.created_at >= start_date,
        ).group_by(
            func.date(Ticket.created_at)
        ).order_by("date").all()
        
        # Tickets resolved per day
        resolved_trend = db.query(
            func.date(Ticket.resolved_at).label("date"),
            func.count(Ticket.id).label("count"),
        ).filter(
            Ticket.org_id == org_id,
            Ticket.resolved_at >= start_date,
        ).group_by(
            func.date(Ticket.resolved_at)
        ).order_by("date").all()
        
        # Build daily data
        trends = []
        for i in range(days):
            date = (start_date + timedelta(days=i)).date()
            created_count = next(
                (c.count for c in created_trend if c.date == date), 0
            )
            resolved_count = next(
                (r.count for r in resolved_trend if r.date == date), 0
            )
            trends.append({
                "date": date.isoformat(),
                "created": created_count,
                "resolved": resolved_count,
            })
        
        return trends
    
    def get_agent_performance(
        self,
        db: Session,
        org_id: UUID,
        days: int = 30,
    ) -> list[dict]:
        """
        Get performance metrics for each agent.
        
        Metrics:
        - Tickets assigned
        - Tickets resolved
        - Average response time (time to first comment)
        - Comments written
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get all agents in the org
        agents = db.query(User).filter(
            User.org_id == org_id,
            User.is_active == True,
        ).all()
        
        agent_stats = []
        for agent in agents:
            # Tickets assigned to this agent
            assigned_count = db.query(func.count(Ticket.id)).filter(
                Ticket.org_id == org_id,
                Ticket.assigned_to == agent.id,
            ).scalar()
            
            # Tickets resolved by this agent
            resolved_count = db.query(func.count(Ticket.id)).filter(
                Ticket.org_id == org_id,
                Ticket.assigned_to == agent.id,
                Ticket.status == TicketStatus.RESOLVED,
            ).scalar()
            
            # Comments written by this agent
            comment_count = db.query(func.count(Comment.id)).filter(
                Comment.user_id == agent.id,
                Comment.created_at >= start_date,
            ).scalar()
            
            # Average first response time (hours)
            # This is simplified - a full implementation would
            # calculate time from ticket creation to agent's first comment
            avg_response_time = None
            
            agent_stats.append({
                "agent_id": agent.id,
                "agent_name": agent.full_name,
                "role": agent.role.value,
                "assigned_tickets": assigned_count or 0,
                "resolved_tickets": resolved_count or 0,
                "resolution_rate": round(
                    (resolved_count / assigned_count * 100) if assigned_count else 0, 1
                ),
                "comments_written": comment_count or 0,
                "avg_response_hours": avg_response_time,
            })
        
        # Sort by resolved tickets descending
        agent_stats.sort(key=lambda x: x["resolved_tickets"], reverse=True)
        
        return agent_stats
    
    def get_category_distribution(
        self,
        db: Session,
        org_id: UUID,
    ) -> list[dict]:
        """
        Get ticket distribution by category.
        
        Useful for pie charts showing what types of
        tickets are most common.
        """
        results = db.query(
            Ticket.category,
            func.count(Ticket.id).label("count"),
        ).filter(
            Ticket.org_id == org_id,
            Ticket.category.isnot(None),
        ).group_by(Ticket.category).all()
        
        return [
            {
                "category": category.value if category else "uncategorized",
                "count": count,
            }
            for category, count in results
        ]
    def get_weekly_trends(
        self,
        db: Session,
        org_id: UUID,
        weeks: int = 12,
    ) -> list[dict]:
        """
        Get weekly ticket creation and resolution trends.
        
        Returns last N weeks of data for bar/line charts.
        """
        from datetime import timedelta
        
        start_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        
        # Get all tickets in period
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.created_at >= start_date,
        ).all()
        
        # Group by week
        weekly_data = {}
        for ticket in tickets:
            # Get week start (Monday)
            week_start = ticket.created_at.date() - timedelta(
                days=ticket.created_at.weekday()
            )
            week_key = week_start.isoformat()
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "week": week_key,
                    "created": 0,
                    "resolved": 0,
                    "critical": 0,
                }
            
            weekly_data[week_key]["created"] += 1
            
            if ticket.priority.value == "critical":
                weekly_data[week_key]["critical"] += 1
            
            if ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
                weekly_data[week_key]["resolved"] += 1
        
        # Sort by week
        result = sorted(weekly_data.values(), key=lambda x: x["week"])
        
        return result[-weeks:]  # Last N weeks
    
    def get_category_analytics(
        self,
        db: Session,
        org_id: UUID,
    ) -> list[dict]:
        """
        Get category breakdown with average resolution times.
        
        Shows which categories have most tickets and
        how long they take to resolve.
        """
        results = db.query(
            Ticket.category,
            func.count(Ticket.id).label("count"),
            func.avg(
                func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600
            ).label("avg_hours"),
        ).filter(
            Ticket.org_id == org_id,
            Ticket.category.isnot(None),
        ).group_by(Ticket.category).order_by(func.count(Ticket.id).desc()).all()
        
        categories = []
        for category, count, avg_hours in results:
            categories.append({
                "category": category.value if category else "uncategorized",
                "ticket_count": count,
                "avg_resolution_hours": round(avg_hours, 1) if avg_hours else 0,
                "percentage": 0,  # Calculated below
            })
        
        # Calculate percentages
        total = sum(c["ticket_count"] for c in categories)
        for c in categories:
            c["percentage"] = round((c["ticket_count"] / total * 100), 1) if total > 0 else 0
        
        return categories
    
    def get_peak_hours(
        self,
        db: Session,
        org_id: UUID,
        days: int = 90,
    ) -> dict:
        """
        Get ticket volume by hour and day of week.
        
        Shows when your team receives the most tickets.
        Useful for staffing decisions.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.created_at >= start_date,
        ).all()
        
        # By hour
        hour_counts = {h: 0 for h in range(24)}
        # By day of week (0=Monday, 6=Sunday)
        day_counts = {d: 0 for d in range(7)}
        
        for ticket in tickets:
            hour_counts[ticket.created_at.hour] += 1
            day_counts[ticket.created_at.weekday()] += 1
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        return {
            "by_hour": [
                {"hour": h, "count": hour_counts[h]}
                for h in range(24)
            ],
            "by_day": [
                {"day": day_names[d], "count": day_counts[d]}
                for d in range(7)
            ],
            "peak_hour": max(hour_counts, key=hour_counts.get),
            "peak_day": day_names[max(day_counts, key=day_counts.get)],
        }
    
    def get_resolution_efficiency(
        self,
        db: Session,
        org_id: UUID,
    ) -> dict:
        """
        Get resolution efficiency metrics.
        
        Shows:
        - How many tickets resolve within SLA
        - Average time by priority
        - First response time averages
        """
        tickets = db.query(Ticket).filter(
            Ticket.org_id == org_id,
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.resolved_at.isnot(None),
        ).all()
        
        if not tickets:
            return {"avg_resolution_hours": 0, "by_priority": []}
        
        resolution_times = []
        by_priority = {}
        
        for ticket in tickets:
            hours = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
            resolution_times.append(hours)
            
            priority = ticket.priority.value
            if priority not in by_priority:
                by_priority[priority] = []
            by_priority[priority].append(hours)
        
        avg_by_priority = {}
        for priority, times in by_priority.items():
            avg_by_priority[priority] = round(sum(times) / len(times), 1)
        
        return {
            "total_resolved": len(tickets),
            "avg_resolution_hours": round(sum(resolution_times) / len(resolution_times), 1),
            "by_priority": avg_by_priority,
        }        


# Module-level instance
dashboard_service = DashboardService()