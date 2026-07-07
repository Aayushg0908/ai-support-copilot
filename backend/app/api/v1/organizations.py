"""
Organization API endpoints.

Public URLs for organization management:
POST   /api/v1/organizations           - Create organization
GET    /api/v1/organizations           - List organizations
GET    /api/v1/organizations/{org_id}  - Get organization details
PUT    /api/v1/organizations/{org_id}  - Update organization
DELETE /api/v1/organizations/{org_id}  - Delete (deactivate) organization
GET    /api/v1/organizations/{org_id}/users - List users in organization
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationResponse,
    OrganizationDetailResponse,
    OrganizationListResponse,
    OrganizationMessageResponse,
)
from app.schemas.user import UserResponse
from app.services.organization_service import org_service
from app.api.deps.auth import get_current_user, require_role

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    request: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new organization.
    
    Normally called during registration, but also available
    for creating sub-organizations or additional workspaces.
    """
    org = org_service.create(
        db=db,
        name=request.name,
        slug=request.slug,
    )
    db.commit()
    return OrganizationResponse.model_validate(org)


@router.get(
    "/",
    response_model=OrganizationListResponse,
)
def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(True, description="Show only active organizations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role(UserRole.ADMIN)),
):
    """
    List all organizations (admin only).
    
    Paginated to avoid loading thousands of records at once.
    Only admins can see all organizations.
    """
    orgs, total = org_service.list_organizations(
        db=db,
        page=page,
        per_page=per_page,
        active_only=active_only,
    )
    
    return OrganizationListResponse(
        organizations=[OrganizationResponse.model_validate(org) for org in orgs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{org_id}",
    response_model=OrganizationDetailResponse,
)
def get_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get organization details with user count.
    """
    org, user_count = org_service.get_with_user_count(db, org_id)
    
    # Convert to response and add user count
    response = OrganizationDetailResponse.model_validate(org)
    response.user_count = user_count
    
    return response


@router.put(
    "/{org_id}",
    response_model=OrganizationResponse,
)
def update_organization(
    org_id: UUID,
    request: OrganizationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role(UserRole.ADMIN)),
):
    """
    Update organization details (admin only).
    
    Only provided fields are updated. Fields left as None
    keep their current values.
    """
    org = org_service.update(
        db=db,
        org_id=org_id,
        name=request.name,
        slug=request.slug,
        is_active=request.is_active,
        settings=request.settings,
    )
    db.commit()
    return OrganizationResponse.model_validate(org)


@router.delete(
    "/{org_id}",
    response_model=OrganizationMessageResponse,
)
def delete_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role(UserRole.ADMIN)),
):
    """
    Deactivate an organization (admin only).
    
    This is a soft delete - the organization is marked inactive
    but data is preserved. Hard deletes require database access.
    """
    org_service.delete(db, org_id)
    db.commit()
    
    return OrganizationMessageResponse(
        message="Organization deactivated successfully"
    )


@router.get(
    "/{org_id}/users",
    response_model=list[UserResponse],
)
def list_organization_users(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all users belonging to an organization.
    
    Any member of the organization can view this.
    """
    # Verify organization exists
    org_service.get_by_id(db, org_id)
    
    # Get all users in this org
    users = db.query(User).filter(
        User.org_id == org_id,
        User.is_active == True,
    ).order_by(User.created_at.desc()).all()
    
    return [UserResponse.model_validate(user) for user in users]