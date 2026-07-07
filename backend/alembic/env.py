"""
Alembic migration environment configuration.

This file is run by Alembic to:
1. Connect to the database
2. Import all SQLAlchemy models
3. Generate and run migrations

Run migrations with:
    alembic revision --autogenerate -m "description"  # Create migration
    alembic upgrade head                               # Apply migrations
    alembic downgrade -1                               # Undo last migration
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the backend directory to Python path so we can import our app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import all models so Alembic can detect them
from app.db.base import Base
from app.models.user import User
from app.models.organization import Organization
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.core.config import settings

# Alembic Config object
config = context.config

# Set the database URL from our application settings
# This replaces the %(DB_URL)s placeholder in alembic.ini
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("%", "%%")
)

# Set up Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata - tells Alembic what tables to track
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL without connecting to the database.
    Useful for:
    - Reviewing SQL before applying
    - Running migrations manually by a DBA
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Connects to the actual database and applies migrations.
    This is the normal mode used during development and deployment.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Run in online or offline mode based on Alembic command
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()