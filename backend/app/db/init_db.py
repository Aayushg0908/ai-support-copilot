"""
Database initialization and first-run setup.

This file handles:
1. Creating all tables defined in our models
2. Enabling required PostgreSQL extensions (uuid-ossp, pgvector)
3. Seeding initial data for development (optional)

When to use:
Called once when the application starts. If tables already exist,
SQLAlchemy skips them (no data loss).
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, SessionLocal


def enable_extensions() -> None:
    """
    Enable PostgreSQL extensions needed by our application.
    
    uuid-ossp: Required for UUID generation (used in base.py)
    pgvector: Required for AI embeddings (used later in tickets table)
    
    These only need to run once per database. Running them again
    is safe - PostgreSQL ignores IF NOT EXISTS.
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        # conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
        conn.commit()
    
    print("✅ PostgreSQL extensions enabled")


def create_tables() -> None:
    """
    Create all database tables from our SQLAlchemy models.
    
    Base.metadata contains information about every model that
    inherits from Base (User, Ticket, Comment, etc.).
    
    create_all() checks which tables exist and only creates
    missing ones. Existing tables with data are NOT touched.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ All database tables created")


def seed_initial_data() -> None:
    """
    Seed the database with initial data for development.
    
    This runs AFTER tables are created. It checks if data
    already exists before inserting to avoid duplicates.
    
    In production, this would be skipped or replaced with
    proper migration scripts.
    """
    db = SessionLocal()
    try:
        # Check if we already have data (don't seed twice)
        from app.models.organization import Organization
        
        existing_org = db.query(Organization).first()
        if existing_org:
            print("ℹ️  Database already contains data, skipping seed")
            return
        
        # Create a demo organization for testing
        demo_org = Organization(
            name="Demo Company",
            slug="demo-company",
        )
        db.add(demo_org)
        db.commit()
        
        print("✅ Demo organization created")
        print("   Email: admin@demo.com")
        print("   (User creation will happen after we build the User model)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
    finally:
        db.close()


def init_database() -> None:
    """
    Main initialization function called when app starts.
    
    Runs everything in order:
    1. Enable extensions (needed before table creation)
    2. Create tables
    3. Seed data (development only)
    """
    print("\n🔧 Initializing database...\n")
    
    enable_extensions()
    create_tables()
    
    # Only seed in development mode
    if settings.DEBUG:
        seed_initial_data()
    
    print("\n✅ Database initialization complete\n")


# Import settings at the bottom to avoid circular imports
# settings is needed to check DEBUG mode
from app.core.config import settings