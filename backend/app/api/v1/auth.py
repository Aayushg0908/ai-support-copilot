"""
Authentication API endpoints.

These are the public URLs for auth operations:
POST /api/v1/auth/register  - Create account
POST /api/v1/auth/login     - Sign in
POST /api/v1/auth/refresh   - Get new tokens
GET  /api/v1/auth/me        - Get current user profile
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserLoginResponse,
    UserResponse,
    UserMessageResponse,
    RefreshTokenRequest
)
from app.services.auth_service import auth_service
from app.api.deps.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel



# ──────────────────────────────────────────────
# Router Setup
# ──────────────────────────────────────────────
# prefix="/auth" means all routes here start with /auth
# tags=["Auth"] groups them in the API documentation


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new account.
    
    This creates both an Organization and a User.
    The registering user becomes the admin of the organization.
    
    Request body:
    {
        "email": "john@acme.com",
        "password": "StrongPass1",
        "full_name": "John Doe",
        "organization_name": "Acme Corp"
    }
    
    Returns:
    - access_token: JWT for API authentication
    - refresh_token: JWT for getting new access tokens
    - user: Profile information
    """
    user, org, access_token, refresh_token = auth_service.register(
        db=db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        organization_name=request.organization_name,
    )
    
    # Commit the transaction (saves user and org to database)
    db.commit()
    
    # Return tokens and user data
    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=UserLoginResponse,
)
def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Sign in with email and password.
    
    Request body:
    {
        "email": "john@acme.com",
        "password": "StrongPass1"
    }
    
    Returns tokens and user profile.
    """
    user, access_token, refresh_token = auth_service.login(
        db=db,
        email=request.email,
        password=request.password,
    )
    
    # Commit to save last_login_at update
    db.commit()
    
    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post(
    "/refresh",
    response_model=UserLoginResponse,
)
def refresh_token_endpoint(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    new_access_token, new_refresh_token = auth_service.refresh_token(
        db=db,
        refresh_token=request.refresh_token,
    )
    """
    Get new access and refresh tokens using a refresh token.
    
    Access tokens expire in 30 minutes. Instead of logging in again,
    the client sends the refresh token to get new tokens.
    
    Request body:
    {
        "refresh_token": "eyJhbGciOiJI..."
    }
    """
    
    return UserLoginResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        # We don't return user data on refresh
        # Client should cache user data from login
        user=None,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get the currently logged-in user's profile.
    
    Requires valid access token in Authorization header.
    Useful for:
    - Checking if token is still valid
    - Getting fresh user data after profile update
    - Frontend "on mount" check to restore session
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=UserMessageResponse,
)
def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Logout endpoint.
    
    Note: With JWT, there's no server-side session to destroy.
    The client must discard the tokens. This endpoint exists for:
    - API completeness
    - Future server-side token blacklisting
    - Logging/logout tracking
    """
    # In a production system, you might:
    # - Add token to a blacklist (Redis)
    # - Log the logout event
    # - Clear push notification tokens
    
    return UserMessageResponse(
        message="Logged out successfully. Please discard your tokens."
    )