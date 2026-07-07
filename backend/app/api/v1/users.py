"""
User management API endpoints.

Public URLs for user operations:
GET    /api/v1/users                    - List users
GET    /api/v1/users/{user_id}          - Get user details
PUT    /api/v1/users/{user_id}          - Update user
PUT    /api/v1/users/{user_id}/role     - Change user role
POST   /api/v1/users/{user_id}/password - Change password
DELETE /api/v1/users/{user_id}          - Deactivate user
POST   /api/v1/users/{user_id}/reactivate - Reactivate user
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserResponse,
    UserListResponse,
    UserUpdateRequest,
    UserRoleUpdateRequest,
    UserPasswordChangeRequest,
    UserMessageResponse,
)
from app.services.user_service import user_service
from app.api.deps.auth import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=UserListResponse,
)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None, pattern="^(admin|agent|viewer)$"),
    search: Optional[str] = Query(None, min_length=2),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List users in the current user's organization.
    
    Supports:
    - Pagination (page, per_page)
    - Role filtering (admin/agent/viewer)
    - Text search (name or email)
    - Active/inactive filter
    
    Users can only see members of their own organization.
    """
    users, total = user_service.list_users(
        db=db,
        org_id=current_user.org_id,
        page=page,
        per_page=per_page,
        role=UserRole(role) if role else None,
        search=search,
        active_only=active_only,
    )
    
    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single user's details.
    
    Users can view anyone in their organization.
    """
    user = user_service.get_by_id(db, user_id)
    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a user's profile.
    
    Users can update their own profile.
    Admins can update any user in their org.
    """
    user = user_service.update(
        db=db,
        user_id=user_id,
        full_name=request.full_name,
        email=request.email,
        is_active=request.is_active,
    )
    db.commit()
    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
)
def change_user_role(
    user_id: UUID,
    request: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role(UserRole.ADMIN)),
):
    """
    Change a user's role (admin only).
    
    Admins cannot change their own role.
    """
    user = user_service.change_role(
        db=db,
        user_id=user_id,
        new_role=UserRole(request.role),
        current_user=current_user,
    )
    db.commit()
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/password",
    response_model=UserMessageResponse,
)
def change_password(
    user_id: UUID,
    request: UserPasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change a user's password.
    
    Users can only change their own password.
    Requires current password for verification.
    """
    # Only allow changing your own password
    if current_user.id != user_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException(
            detail="You can only change your own password"
        )
    
    user_service.change_password(
        db=db,
        user_id=user_id,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    db.commit()
    
    return UserMessageResponse(
        message="Password changed successfully"
    )


@router.delete(
    "/{user_id}",
    response_model=UserMessageResponse,
)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role(UserRole.ADMIN)),
):
    """
    Deactivate a user (admin only).
    
    Soft delete - user is marked inactive but data preserved.
    Admins cannot deactivate themselves.
    """
    user_service.deactivate(
        db=db,
        user_id=user_id,
        current_user=current_user,
    )
    db.commit()
    
    return UserMessageResponse(
        message="User deactivated successfully"
    )


@router.post(
    "/{user_id}/reactivate",
    response_model=UserResponse,
)
def reactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role(UserRole.ADMIN)),
):
    """
    Reactivate a previously deactivated user (admin only).
    """
    user = user_service.reactivate(db, user_id)
    db.commit()
    return UserResponse.model_validate(user)