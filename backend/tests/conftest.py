"""
Test configuration and shared fixtures.

Provides:
- Test database (separate from development DB)
- FastAPI test client
- Helper functions for creating test data
"""

import pytest
from typing import Generator, Dict
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.core.security import create_access_token


# ──────────────────────────────────────────────
# Test Database Setup
# ──────────────────────────────────────────────

# Use a separate test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "support_copilot", "support_copilot_test"
)

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    """Replace the production DB with test DB."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Provide a clean database session for each test.
    
    Creates tables before test, drops them after.
    Each test gets a fresh database.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """
    Provide a FastAPI test client.
    
    Uses the test database via dependency override.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def test_user(db: Session) -> Dict:
    """
    Create a test user and return user data + auth header.
    
    Returns dict with:
    - user: User object
    - token: JWT access token
    - headers: Authorization headers for API calls
    """
    from app.models.user import User, UserRole
    from app.models.organization import Organization
    from app.core.security import hash_password
    
    # Create test organization
    org = Organization(
        name="Test Org",
        slug="test-org",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Create test user (admin)
    user = User(
        org_id=org.id,
        email="test@example.com",
        password_hash=hash_password("TestPass1"),
        full_name="Test User",
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    token = create_access_token(
        data={"sub": str(user.id), "org_id": str(org.id)}
    )
    
    return {
        "user": user,
        "organization": org,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture(scope="function")
def test_ticket(db: Session, test_user: Dict) -> Dict:
    """
    Create a test ticket and return ticket data.
    """
    from app.models.ticket import Ticket, TicketStatus, TicketPriority
    
    ticket = Ticket(
        org_id=test_user["organization"].id,
        created_by=test_user["user"].id,
        title="Test Ticket",
        description="This is a test ticket",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return {
        "ticket": ticket,
        "user": test_user["user"],
        "headers": test_user["headers"],
    }