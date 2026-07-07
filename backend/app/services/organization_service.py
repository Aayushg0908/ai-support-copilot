"""
Organization business logic.

Handles all organization operations:
- Creating organizations with unique slugs
- Updating organization details
- Soft-deleting organizations
- Listing organizations with pagination
- Fetching organization with user count
"""

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.organization import Organization
from app.models.user import User
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
)


class OrganizationService:
    """
    Handles all organization-related operations.
    
    Like AuthService, each method takes a database session
    and the caller decides when to commit.
    """
    
    def create(
        self,
        db: Session,
        name: str,
        slug: Optional[str] = None,
    ) -> Organization:
        """
        Create a new organization.
        
        Args:
            name: Company name (e.g., "Acme Corp")
            slug: Optional URL-safe identifier. Auto-generated if not provided.
        
        Returns:
            The created Organization object
        """
        # Generate slug from name if not provided
        if slug:
            # Clean up user-provided slug
            slug = self._clean_slug(slug)
        else:
            slug = self._generate_slug(name, db)
        
        # Check if slug already exists
        existing = db.query(Organization).filter(
            Organization.slug == slug
        ).first()
        
        if existing:
            raise ConflictException(
                detail=f"Organization with slug '{slug}' already exists"
            )
        
        # Create the organization
        org = Organization(
            name=name.strip(),
            slug=slug,
        )
        db.add(org)
        db.flush()  # Get the ID without committing
        
        return org
    
    def get_by_id(
        self,
        db: Session,
        org_id: UUID,
    ) -> Organization:
        """
        Get an organization by its ID.
        
        Raises NotFoundException if the organization doesn't exist.
        """
        org = db.query(Organization).filter(
            Organization.id == org_id
        ).first()
        
        if not org:
            raise NotFoundException(resource="Organization", identifier=org_id)
        
        return org
    
    def get_by_slug(
        self,
        db: Session,
        slug: str,
    ) -> Organization:
        """
        Get an organization by its URL slug.
        
        Useful for looking up orgs from URLs like /organizations/acme-corp
        """
        org = db.query(Organization).filter(
            Organization.slug == slug
        ).first()
        
        if not org:
            raise NotFoundException(
                resource="Organization",
                identifier=slug
            )
        
        return org
    
    def get_with_user_count(
        self,
        db: Session,
        org_id: UUID,
    ) -> tuple[Organization, int]:
        """
        Get organization with its user count.
        
        Returns a tuple of (organization, user_count).
        Uses a single query with a JOIN to count users efficiently.
        """
        # Query that gets org + user count in one database call
        result = db.query(
            Organization,
            func.count(User.id).label("user_count")
        ).outerjoin(
            User, User.org_id == Organization.id
        ).filter(
            Organization.id == org_id
        ).group_by(
            Organization.id
        ).first()
        
        if not result:
            raise NotFoundException(
                resource="Organization",
                identifier=org_id
            )
        
        org, user_count = result
        return org, user_count
    
    def list_organizations(
        self,
        db: Session,
        page: int = 1,
        per_page: int = 20,
        active_only: bool = True,
    ) -> tuple[list[Organization], int]:
        """
        List organizations with pagination.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page (max 100)
            active_only: If True, only return active organizations
        
        Returns:
            Tuple of (organizations_list, total_count)
        """
        # Start with base query
        query = db.query(Organization)
        
        # Filter active only if requested
        if active_only:
            query = query.filter(Organization.is_active == True)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        organizations = query.order_by(
            Organization.created_at.desc()
        ).offset(offset).limit(per_page).all()
        
        return organizations, total
    
    def update(
        self,
        db: Session,
        org_id: UUID,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        is_active: Optional[bool] = None,
        settings: Optional[dict] = None,
    ) -> Organization:
        """
        Update organization fields.
        
        Only updates fields that are provided (not None).
        If slug is changed, checks for uniqueness.
        """
        org = self.get_by_id(db, org_id)
        
        # Update name if provided
        if name is not None:
            org.name = name.strip()
        
        # Update slug if provided (with uniqueness check)
        if slug is not None:
            clean_slug = self._clean_slug(slug)
            existing = db.query(Organization).filter(
                Organization.slug == clean_slug,
                Organization.id != org_id,  # Exclude current org
            ).first()
            if existing:
                raise ConflictException(
                    detail=f"Organization with slug '{clean_slug}' already exists"
                )
            org.slug = clean_slug
        
        # Update active status
        if is_active is not None:
            org.is_active = is_active
        
        # Update settings (merge with existing)
        if settings is not None:
            org.settings = {**org.settings, **settings}
        
        db.flush()
        return org
    
    def delete(
        self,
        db: Session,
        org_id: UUID,
    ) -> None:
        """
        Soft delete an organization.
        
        Sets is_active=False instead of actually deleting.
        This preserves all related data (users, tickets).
        """
        org = self.get_by_id(db, org_id)
        org.is_active = False
        db.flush()
    
    def _generate_slug(self, name: str, db: Session) -> str:
        """
        Generate a unique URL-safe slug from organization name.
        
        Example: "Acme Corp!" → "acme-corp"
        If "acme-corp" exists → "acme-corp-1"
        """
        slug = self._clean_slug(name)
        
        # Ensure uniqueness by appending number if needed
        base_slug = slug
        counter = 1
        while db.query(Organization).filter(
            Organization.slug == slug
        ).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def _clean_slug(self, text: str) -> str:
        """
        Convert text to a clean URL slug.
        
        Rules:
        - Lowercase
        - Replace non-alphanumeric chars with hyphens
        - Collapse multiple hyphens
        - Strip leading/trailing hyphens
        """
        slug = text.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[\s]+', '-', slug)         # Spaces to hyphens
        slug = re.sub(r'-+', '-', slug)            # Collapse multiple hyphens
        slug = slug.strip('-')                      # Remove edge hyphens
        return slug


# Module-level instance for importing
org_service = OrganizationService()