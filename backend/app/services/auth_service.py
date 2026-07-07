"""
Authentication business logic.

This service handles all auth operations:
- User registration (with organization creation)
- User login (password verification + token generation)
- Token refresh
- Getting current user from token

It orchestrates between models, security utils, and database.
API routes should only call these methods, not contain logic.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import (
    ConflictException,
    UnauthorizedException,
)


class AuthService:
    """Handles all authentication-related operations."""
    
    def register(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: str,
        organization_name: str,
    ) -> Tuple[User, Organization, str, str]:
        """
        Register a new user AND create their organization.
        
        Returns:
            (user, organization, access_token, refresh_token)
        """
        # Check for existing user
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ConflictException(
                detail=f"A user with email '{email}' already exists"
            )
        
        # Create organization
        org = Organization(
            name=organization_name,
            slug=self._generate_slug(organization_name, db),
        )
        db.add(org)
        db.flush()
        
        # Create user (first user is admin)
        user = User(
            org_id=org.id,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.flush()
        
        # Generate tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "org_id": str(org.id)}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return user, org, access_token, refresh_token
    
    def login(
        self,
        db: Session,
        email: str,
        password: str,
    ) -> Tuple[User, str, str]:
        """
        Authenticate a user and return tokens.
        """
        user = db.query(User).filter(
            User.email == email.lower().strip()
        ).first()
        
        if not user:
            raise UnauthorizedException(detail="Invalid email or password")
        
        if not user.is_active:
            raise UnauthorizedException(
                detail="Account is deactivated. Contact your administrator."
            )
        
        if not verify_password(password, user.password_hash):
            raise UnauthorizedException(detail="Invalid email or password")
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        db.flush()
        
        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "org_id": str(user.org_id),
                "role": user.role.value,
            }
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return user, access_token, refresh_token
    
    def refresh_token(
        self,
        db: Session,
        refresh_token: str,
    ) -> Tuple[str, str]:
        """
        Use a refresh token to get new access and refresh tokens.
        """
        payload = decode_token(refresh_token)
        
        if not payload:
            raise UnauthorizedException(detail="Invalid or expired refresh token")
        
        if payload.get("type") != "refresh":
            raise UnauthorizedException(detail="Invalid token type")
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            raise UnauthorizedException(detail="User not found or deactivated")
        
        new_access_token = create_access_token(
            data={
                "sub": str(user.id),
                "org_id": str(user.org_id),
                "role": user.role.value,
            }
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return new_access_token, new_refresh_token
    
    def get_current_user(
        self,
        db: Session,
        token: str,
    ) -> User:
        """
        Get the currently authenticated user from a JWT token.
        """
        payload = decode_token(token)
        
        if not payload:
            raise UnauthorizedException(detail="Invalid or expired token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(detail="Invalid token payload")
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise UnauthorizedException(detail="User not found")
        
        if not user.is_active:
            raise UnauthorizedException(detail="Account is deactivated")
        
        return user
    
    def _generate_slug(self, name: str, db: Session) -> str:
        """Generate a URL-safe slug from organization name."""
        import re
        
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = slug.strip('-')
        
        base_slug = slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug


# Module-level instance for importing
auth_service = AuthService()