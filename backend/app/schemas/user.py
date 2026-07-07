"""
Pydantic schemas for User requests and responses.

These define what data the API accepts and returns.
They are separate from models because:
1. We never expose password_hash in responses
2. Registration needs different fields than login
3. Profile update needs different fields than registration
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ═══════════════════════════════════════════════════════════
# REQUEST SCHEMAS (What the client sends to us)
# ═══════════════════════════════════════════════════════════

class UserRegisterRequest(BaseModel):
    """
    Fields required when creating a new account.
    
    EmailStr is Pydantic's built-in email validator.
    It checks for proper email format automatically.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=2, max_length=255)
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        Ensure password meets security requirements.
        
        Runs automatically when Pydantic processes the request.
        If validation fails, FastAPI returns a 422 error with
        the error message.
        """
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        return value


class UserLoginRequest(BaseModel):
    """Fields required for login."""
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    """
    Fields that can be updated after account creation.
    All fields are Optional - client only sends what changed.
    """
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ═══════════════════════════════════════════════════════════
# RESPONSE SCHEMAS (What we send back to the client)
# ═══════════════════════════════════════════════════════════

class UserResponse(BaseModel):
    """
    Public user data safe to return in API responses.
    
    Notice what's MISSING:
    - password_hash (never exposed)
    - org_id (internal detail, frontend usually doesn't need it)
    """
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # This tells Pydantic to read data from SQLAlchemy ORM objects
    # Without this, Pydantic expects a dict, not a model instance
    model_config = {"from_attributes": True}


class UserLoginResponse(BaseModel):
    """Returned after successful login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None  # Optional for refresh endpoint


class UserMessageResponse(BaseModel):
    """Simple message response for operations without data."""
    success: bool = True
    message: str
 
 
 
# ═══════════════════════════════════════════════════════════
# USER MANAGEMENT SCHEMAS (Add these to existing file)
# ═══════════════════════════════════════════════════════════

class UserListResponse(BaseModel):
    """
    Wrapper for paginated user list.
    
    Returns users array plus metadata for pagination.
    """
    users: list[UserResponse]
    total: int
    page: int
    per_page: int


class UserRoleUpdateRequest(BaseModel):
    """
    Request to change a user's role.
    
    Only accepts valid roles defined in the enum.
    """
    role: str = Field(..., pattern="^(admin|agent|viewer)$")


class UserPasswordChangeRequest(BaseModel):
    """
    Request to change password.
    
    Requires current password for verification
    and new password that meets strength requirements.
    """
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Same validation as registration."""
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        return value


class UserBulkActionRequest(BaseModel):
    """
    Request for bulk operations on users.
    
    Used for actions like bulk deactivate or bulk role change.
    """
    user_ids: list[str]
    action: str = Field(..., pattern="^(deactivate|reactivate)$")    
    
class RefreshTokenRequest(BaseModel):
    """Request to refresh tokens."""
    refresh_token: str    