"""
User management business logic.

Handles user CRUD operations:
- Listing users (with pagination and filters)
- Getting user details
- Updating user profiles
- Changing roles
- Deactivating/reactivating users

Separate from auth_service because:
- Auth handles login/register/tokens
- This handles ongoing user management
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User, UserRole
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ForbiddenException,
)
from app.core.security import hash_password


class UserService:
    """Handles user management operations."""
    
    def get_by_id(
        self,
        db: Session,
        user_id: UUID,
    ) -> User:
        """
        Get a single user by ID.
        
        Raises NotFoundException if user doesn't exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise NotFoundException(resource="User", identifier=user_id)
        
        return user
    
    def list_users(
        self,
        db: Session,
        org_id: UUID,
        page: int = 1,
        per_page: int = 20,
        role: Optional[UserRole] = None,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> tuple[list[User], int]:
        """
        List users in an organization with filtering and pagination.
        
        Args:
            org_id: Only return users from this organization
            page: Page number (1-based)
            per_page: Items per page
            role: Filter by role (admin/agent/viewer)
            search: Search by name or email
            active_only: Only show active users
        
        Returns:
            Tuple of (users_list, total_count)
        """
        # Start with base query - always filter by org
        query = db.query(User).filter(User.org_id == org_id)
        
        # Apply filters
        if role:
            query = query.filter(User.role == role)
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        if search:
            # Search in both name and email
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term),
                )
            )
        
        # Get total count for pagination metadata
        total = query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * per_page
        users = query.order_by(
            User.created_at.desc()
        ).offset(offset).limit(per_page).all()
        
        return users, total
    
    def update(
        self,
        db: Session,
        user_id: UUID,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        """
        Update user profile fields.
        
        Only provided fields are changed. Email changes are
        checked for uniqueness.
        """
        user = self.get_by_id(db, user_id)
        
        # Update name
        if full_name is not None:
            user.full_name = full_name.strip()
        
        # Update email (with uniqueness check)
        if email is not None:
            email = email.lower().strip()
            existing = db.query(User).filter(
                User.email == email,
                User.id != user_id,  # Exclude current user
            ).first()
            if existing:
                raise ConflictException(
                    detail=f"Email '{email}' is already in use"
                )
            user.email = email
        
        # Update active status
        if is_active is not None:
            user.is_active = is_active
        
        db.flush()
        return user
    
    def change_role(
        self,
        db: Session,
        user_id: UUID,
        new_role: UserRole,
        current_user: User,
    ) -> User:
        """
        Change a user's role.
        
        Rules:
        - Cannot change your own role
        - Only admins can change roles (enforced at API level)
        """
        user = self.get_by_id(db, user_id)
        
        # Prevent self-role-change for security
        if user.id == current_user.id:
            raise ForbiddenException(
                detail="You cannot change your own role"
            )
        
        user.role = new_role
        db.flush()
        return user
    
    def change_password(
        self,
        db: Session,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Change a user's password.
        
        Requires current password for verification.
        """
        from app.core.security import verify_password
        
        user = self.get_by_id(db, user_id)
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise ForbiddenException(
                detail="Current password is incorrect"
            )
        
        # Hash and set new password
        user.password_hash = hash_password(new_password)
        db.flush()
        return user
    
    def deactivate(
        self,
        db: Session,
        user_id: UUID,
        current_user: User,
    ) -> User:
        """
        Deactivate a user (soft delete).
        
        Rules:
        - Cannot deactivate yourself
        - Admin deactivating another admin needs extra care
        """
        user = self.get_by_id(db, user_id)
        
        if user.id == current_user.id:
            raise ForbiddenException(
                detail="You cannot deactivate your own account"
            )
        
        user.is_active = False
        db.flush()
        return user
    
    def reactivate(
        self,
        db: Session,
        user_id: UUID,
    ) -> User:
        """
        Reactivate a previously deactivated user.
        """
        user = self.get_by_id(db, user_id)
        user.is_active = True
        db.flush()
        return user


# Module-level instance
user_service = UserService()