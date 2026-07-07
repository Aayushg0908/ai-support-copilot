"""
Ticket business logic.

Handles all ticket operations:
- Creating tickets
- Listing with filters (status, priority, assignee, search, date range)
- Updating tickets (status changes, assignments, edits)
- Deleting (soft delete by closing)
- Getting ticket with related data (creator name, assignee name, comment count)

This is the most complex service because tickets are the
central entity of the application.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from sqlalchemy.sql import select

from app.models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from app.models.user import User
from app.models.comment import Comment
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.services.audit_service import audit_service


class TicketService:
    """Handles all ticket-related operations."""
    
    def create(
        self,
        db: Session,
        org_id: UUID,
        created_by: UUID,
        title: str,
        description: str,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
    ) -> Ticket:
        """
        Create a new ticket.
        
        Validates:
        - Assignee belongs to same organization
        - Category and priority are valid enum values
        """
        # Validate assignee belongs to same org
        if assigned_to:
            assignee = db.query(User).filter(
                User.id == assigned_to,
                User.org_id == org_id,
                User.is_active == True,
            ).first()
            if not assignee:
                raise ValidationException(
                    detail="Assignee not found or not in your organization"
                )
        
        # Create ticket
        ticket = Ticket(
            org_id=org_id,
            created_by=created_by,
            title=title.strip(),
            description=description.strip(),
            status=TicketStatus.OPEN,
            priority=TicketPriority(priority) if priority else TicketPriority.MEDIUM,
            category=TicketCategory(category) if category else None,
            assigned_to=assigned_to,
            tags=tags or [],
        )
        
        db.add(ticket)
        db.flush()
        # Log the action
        audit_service.log_ticket_created(
            db=db,
            org_id=org_id,
            ticket_id=ticket.id,
            user_id=created_by,
        )
        return ticket
    
    def get_by_id(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: Optional[UUID] = None,
    ) -> Ticket:
        """
        Get a single ticket by ID.
        
        If org_id is provided, ensures ticket belongs to that org
        (multi-tenancy check).
        """
        query = db.query(Ticket).filter(Ticket.id == ticket_id)
        
        if org_id:
            query = query.filter(Ticket.org_id == org_id)
        
        ticket = query.first()
        
        if not ticket:
            raise NotFoundException(resource="Ticket", identifier=ticket_id)
        
        return ticket
    
    def get_with_relations(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> dict:
        """
        Get ticket with creator name, assignee name, and comment count.
        
        Uses a single query with JOINs instead of multiple queries.
        Returns a dictionary with all the data needed for TicketDetailResponse.
        """
        # Query ticket with joined creator and assignee
        result = db.query(
            Ticket,
            User.full_name.label("creator_name"),
        ).outerjoin(
            User, User.id == Ticket.created_by
        ).filter(
            Ticket.id == ticket_id,
            Ticket.org_id == org_id,
        ).first()
        
        if not result:
            raise NotFoundException(resource="Ticket", identifier=ticket_id)
        
        ticket, creator_name = result
        
        # Get assignee name if assigned
        assignee_name = None
        if ticket.assigned_to:
            assignee = db.query(User).filter(
                User.id == ticket.assigned_to
            ).first()
            assignee_name = assignee.full_name if assignee else None
        
        # Get comment count
        comment_count = db.query(func.count(Comment.id)).filter(
            Comment.ticket_id == ticket_id
        ).scalar()
        
        return {
            "ticket": ticket,
            "creator_name": creator_name,
            "assignee_name": assignee_name,
            "comment_count": comment_count or 0,
        }
    
    def list_tickets(
        self,
        db: Session,
        org_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        search: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], int]:
        """
        List tickets with filtering, search, and pagination.
        
        This is the most complex query in the application.
        Supports multiple simultaneous filters.
        """
        # Base query - always filter by org
        query = db.query(
            Ticket,
            User.full_name.label("creator_name"),
        ).outerjoin(
            User, User.id == Ticket.created_by
        ).filter(
            Ticket.org_id == org_id
        )
        
        # Apply filters
        if status:
            query = query.filter(Ticket.status == status)
        
        if priority:
            query = query.filter(Ticket.priority == priority)
        
        if category:
            query = query.filter(Ticket.category == category)
        
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        
        if created_by:
            query = query.filter(Ticket.created_by == created_by)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Ticket.title.ilike(search_term),
                    Ticket.description.ilike(search_term),
                )
            )
        
        if from_date:
            query = query.filter(Ticket.created_at >= from_date)
        
        if to_date:
            query = query.filter(Ticket.created_at <= to_date)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(Ticket, sort_by, Ticket.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Apply pagination
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()
        
        # Build response with assignee names
        tickets = []
        for ticket, creator_name in results:
            # Get assignee name if assigned
            assignee_name = None
            if ticket.assigned_to:
                assignee = db.query(User).filter(
                    User.id == ticket.assigned_to
                ).first()
                assignee_name = assignee.full_name if assignee else None
            
            # Get comment count for each ticket
            comment_count = db.query(func.count(Comment.id)).filter(
                Comment.ticket_id == ticket.id
            ).scalar()
            
            tickets.append({
                "ticket": ticket,
                "creator_name": creator_name,
                "assignee_name": assignee_name,
                "comment_count": comment_count or 0,
            })
        
        return tickets, total
    
    def update(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
    ) -> Ticket:
        """
        Update ticket fields.
        
        Only provided fields are changed.
        Special handling for status changes:
        - resolved status sets resolved_at timestamp
        - reopening clears resolved_at
        """
        ticket = self.get_by_id(db, ticket_id, org_id)
        
        if title is not None:
            ticket.title = title.strip()
        
        if description is not None:
            ticket.description = description.strip()
        
        if status is not None:
            new_status = TicketStatus(status)
            
            # Set resolved_at when ticket is resolved
            if new_status == TicketStatus.RESOLVED and ticket.status != TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.now(timezone.utc)
            
            # Clear resolved_at if reopened
            if new_status in (TicketStatus.OPEN, TicketStatus.IN_PROGRESS):
                ticket.resolved_at = None
            
            ticket.status = new_status
        
        if priority is not None:
            ticket.priority = TicketPriority(priority)
        
        if category is not None:
            ticket.category = TicketCategory(category)
        
        if assigned_to is not None:
            # Validate assignee is in same org
            assignee = db.query(User).filter(
                User.id == assigned_to,
                User.org_id == org_id,
                User.is_active == True,
            ).first()
            if not assignee:
                raise ValidationException(
                    detail="Assignee not found or not in your organization"
                )
            ticket.assigned_to = assigned_to
        
        if tags is not None:
            ticket.tags = tags
        
         # Build changes dict for audit log
        audit_changes = {}
        if title is not None:
            audit_changes["title"] = {"new": title}
        if description is not None:
            audit_changes["description"] = {"new": "updated"}
        if status is not None:
            audit_changes["status"] = {"old": ticket.status.value, "new": status}
        if priority is not None:
            audit_changes["priority"] = {"old": ticket.priority.value, "new": priority}
        if assigned_to is not None:
            audit_changes["assigned_to"] = {"new": str(assigned_to)}
        
        if audit_changes:
            audit_service.log_ticket_updated(
                db=db,
                org_id=org_id,
                ticket_id=ticket.id,
                user_id=ticket.created_by,  # TODO: pass current user
                changes=audit_changes,
            )
        
        db.flush()
        return ticket
    
    def assign(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
        assigned_to: UUID,
    ) -> Ticket:
        """
        Assign a ticket to a user.
        
        Dedicated method because assignment is a common operation
        that may trigger notifications in the future.
        """
        ticket=self.update(
            db=db,
            ticket_id=ticket_id,
            org_id=org_id,
            assigned_to=assigned_to,
            status="in_progress",  # Auto-set to in_progress when assigned
        )
        
        audit_service.log_ticket_assigned(
            db=db,
            org_id=org_id,
            ticket_id=ticket.id,
            user_id=ticket.created_by,
            assigned_to=assigned_to,
        )
        
        
        return ticket
    
    def change_status(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
        new_status: str,
    ) -> Ticket:
        """Change ticket status."""
        ticket = self.update(
            db=db,
            ticket_id=ticket_id,
            org_id=org_id,
            status=new_status,
        )
        
        # Log AFTER update
        audit_service.log_ticket_status_changed(
            db=db,
            org_id=org_id,
            ticket_id=ticket.id,
            user_id=ticket.created_by,
            old_status=ticket.status.value,
            new_status=new_status,
        )
        
        return ticket
    
    def delete(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> None:
        """
        Close a ticket (soft delete).
        
        Instead of deleting, sets status to closed.
        This preserves the ticket for reporting.
        """
        ticket = self.get_by_id(db, ticket_id, org_id)
        ticket.status = TicketStatus.CLOSED
        ticket.resolved_at = datetime.now(timezone.utc)
        db.flush()


# Module-level instance
ticket_service = TicketService()