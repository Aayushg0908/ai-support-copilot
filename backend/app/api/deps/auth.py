"""
Authentication dependencies for FastAPI.

These are reusable guards that protect API routes.
Any route can add `current_user: User = Depends(get_current_user)`
and FastAPI will automatically verify authentication before
the route handler runs.

How dependencies work in FastAPI:
1. FastAPI sees Depends(get_current_user)
2. It calls get_current_user(request)
3. If it returns a User → route runs with that user
4. If it raises an exception → route never runs, 401 returned
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import auth_service

# ──────────────────────────────────────────────
# Security Scheme: How we extract the token
# ──────────────────────────────────────────────
# HTTPBearer looks for the Authorization header:
# Authorization: Bearer eyJhbGciOiJI...
#
# auto_error=False means it won't auto-raise 401.
# We want to control the error message ourselves.
security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    Get the currently authenticated user from the JWT token.
    
    Usage in a route:
        @router.get("/profile")
        def get_profile(current_user: User = Depends(get_current_user)):
            return current_user
    
    Flow:
    1. Extract token from Authorization header
    2. If no token → 401 error
    3. Decode and verify token
    4. Find user in database
    5. Return user object to the route
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # credentials.credentials contains the actual token string
    token = credentials.credentials
    
    # Call the auth service to validate token and get user
    # This raises UnauthorizedException if token is invalid
    return auth_service.get_current_user(db, token)


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Same as get_current_user but also checks if user is active.
    
    This adds an extra layer: even with a valid token,
    deactivated accounts cannot access routes.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Factory function that creates a dependency for role-based access.
    
    Usage:
        # Only admins can access this route
        @router.delete("/users/{id}")
        def delete_user(
            user_id: str,
            current_user: User = Depends(get_current_user),
            _: bool = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    
    This is a "dependency factory" - a function that returns a dependency.
    It allows us to specify which roles are allowed at the route level.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> bool:
        if current_user.role not in allowed_roles:
            role_names = ", ".join([r.value for r in allowed_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {role_names}",
            )
        return True
    
    return role_checker


def require_org_access(
    org_id: str,
    current_user: User = Depends(get_current_user),
) -> bool:
    """
    Verify the current user belongs to the organization they're
    trying to access. Prevents users from accessing other orgs' data.
    
    Usage:
        @router.get("/organizations/{org_id}")
        def get_org(
            org_id: str,
            current_user: User = Depends(get_current_user),
            _: bool = Depends(require_org_access(org_id))
        ):
            ...
    """
    if str(current_user.org_id) != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )
    return True