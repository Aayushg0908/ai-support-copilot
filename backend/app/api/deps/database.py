"""
Database and common dependencies for FastAPI.

Provides reusable dependencies used across multiple route files.
"""

from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db.session import get_db
from app.models.user import User
from app.api.deps.auth import get_current_user


def get_current_org_id(
    current_user: User = Depends(get_current_user),
) -> UUID:
    """
    Extract the current user's organization ID.
    
    Used in every multi-tenant endpoint to scope queries.
    Instead of manually extracting current_user.org_id in every route,
    routes can just add this dependency.
    
    Usage:
        @router.get("/tickets")
        def list_tickets(
            db: Session = Depends(get_db),
            org_id: UUID = Depends(get_current_org_id),
        ):
            tickets = ticket_service.list_tickets(db, org_id)
    """
    return current_user.org_id


# Re-export get_db so routes can import from one place
__all__ = ["get_db", "get_current_org_id"]