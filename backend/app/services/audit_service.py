"""
Audit logging service.

Central logging for all system actions.
Called by other services to record what happened.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit_log import AuditLog


class AuditService:
    """Records and retrieves audit logs."""
    
    def log(
        self,
        db: Session,
        org_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        user_id: Optional[UUID] = None,
        changes: Optional[Dict] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Record an action in the audit log.
        
        Args:
            db: Database session
            org_id: Organization ID
            action: What happened (created, updated, deleted)
            resource_type: What type of record (ticket, user, comment)
            resource_id: Which record
            user_id: Who did it
            changes: What changed (old/new values)
            description: Human-readable description
            ip_address: Request IP
        
        Returns:
            Created AuditLog record
        """
        log_entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes or {},
            description=description,
            ip_address=ip_address,
        )
        
        db.add(log_entry)
        db.flush()
        
        return log_entry
    
    def log_ticket_created(
        self,
        db: Session,
        org_id: UUID,
        ticket_id: UUID,
        user_id: UUID,
    ) -> AuditLog:
        """Log ticket creation."""
        return self.log(
            db=db,
            org_id=org_id,
            user_id=user_id,
            action="created",
            resource_type="ticket",
            resource_id=ticket_id,
            description="Ticket created",
        )
    
    def log_ticket_updated(
        self,
        db: Session,
        org_id: UUID,
        ticket_id: UUID,
        user_id: UUID,
        changes: Dict,
    ) -> AuditLog:
        """Log ticket update with what changed."""
        return self.log(
            db=db,
            org_id=org_id,
            user_id=user_id,
            action="updated",
            resource_type="ticket",
            resource_id=ticket_id,
            changes=changes,
            description=f"Ticket updated: {', '.join(changes.keys())}",
        )
    
    def log_ticket_status_changed(
        self,
        db: Session,
        org_id: UUID,
        ticket_id: UUID,
        user_id: UUID,
        old_status: str,
        new_status: str,
    ) -> AuditLog:
        """Log ticket status change."""
        return self.log(
            db=db,
            org_id=org_id,
            user_id=user_id,
            action="status_changed",
            resource_type="ticket",
            resource_id=ticket_id,
            changes={"status": {"old": old_status, "new": new_status}},
            description=f"Status changed from {old_status} to {new_status}",
        )
    
    def log_ticket_assigned(
        self,
        db: Session,
        org_id: UUID,
        ticket_id: UUID,
        user_id: UUID,
        assigned_to: UUID,
    ) -> AuditLog:
        """Log ticket assignment."""
        return self.log(
            db=db,
            org_id=org_id,
            user_id=user_id,
            action="assigned",
            resource_type="ticket",
            resource_id=ticket_id,
            changes={"assigned_to": assigned_to},
            description=f"Ticket assigned to user {assigned_to}",
        )
    
    def log_user_role_changed(
        self,
        db: Session,
        org_id: UUID,
        target_user_id: UUID,
        changed_by: UUID,
        old_role: str,
        new_role: str,
    ) -> AuditLog:
        """Log user role change."""
        return self.log(
            db=db,
            org_id=org_id,
            user_id=changed_by,
            action="role_changed",
            resource_type="user",
            resource_id=target_user_id,
            changes={"role": {"old": old_role, "new": new_role}},
            description=f"Role changed from {old_role} to {new_role}",
        )
    
    def log_user_login(
        self,
        db: Session,
        org_id: UUID,
        user_id: UUID,
    ) -> AuditLog:
        """Log user login."""
        return self.log(
            db=db,
            org_id=org_id,
            user_id=user_id,
            action="login",
            resource_type="user",
            resource_id=user_id,
            description="User logged in",
        )
    
    def get_logs(
        self,
        db: Session,
        org_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Query audit logs with filters.
        
        Args:
            org_id: Filter by organization
            resource_type: Filter by resource type (ticket, user, etc.)
            resource_id: Filter by specific resource
            user_id: Filter by who performed the action
            action: Filter by action type
            page: Page number
            per_page: Items per page
        
        Returns:
            (logs_list, total_count)
        """
        query = db.query(AuditLog).filter(AuditLog.org_id == org_id)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        total = query.count()
        
        offset = (page - 1) * per_page
        logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(per_page).all()
        
        return logs, total
    
    def get_ticket_history(
        self,
        db: Session,
        ticket_id: UUID,
        org_id: UUID,
    ) -> list[AuditLog]:
        """Get complete history for a ticket."""
        return db.query(AuditLog).filter(
            AuditLog.org_id == org_id,
            AuditLog.resource_type == "ticket",
            AuditLog.resource_id == ticket_id,
        ).order_by(desc(AuditLog.created_at)).all()


# Module-level singleton
audit_service = AuditService()