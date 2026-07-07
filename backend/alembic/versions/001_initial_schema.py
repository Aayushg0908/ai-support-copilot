"""
Initial database schema.

Creates all core tables:
- organizations
- users
- tickets
- comments

Revision ID: 001
Revises: None (first migration)
Create Date: 2026-06-23
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply the migration - creates all tables.
    
    Run with: alembic upgrade head
    """
    
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    # op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    
    # ──────────────────────────────────────────
    # organizations table
    # ──────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('settings', postgresql.JSONB(), default={}, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('idx_organizations_slug', 'organizations', ['slug'], unique=True)
    
    # ──────────────────────────────────────────
    # users table
    # ──────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), default='agent', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_org_id', 'users', ['org_id'])
    
    # ──────────────────────────────────────────
    # tickets table
    # ──────────────────────────────────────────
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), default='open', nullable=False),
        sa.Column('priority', sa.String(20), default='medium', nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.JSONB(), default=[], nullable=True),
        sa.Column('ai_category', sa.String(50), nullable=True),
        sa.Column('ai_priority', sa.String(20), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('health_score', sa.Integer(), nullable=True),
        # sa.Column('embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('idx_tickets_org_id', 'tickets', ['org_id'])
    op.create_index('idx_tickets_status', 'tickets', ['status'])
    op.create_index('idx_tickets_priority', 'tickets', ['priority'])
    op.create_index('idx_tickets_assigned_to', 'tickets', ['assigned_to'])
    op.create_index('idx_tickets_created_by', 'tickets', ['created_by'])
    
    # ──────────────────────────────────────────
    # comments table
    # ──────────────────────────────────────────
    op.create_table(
        'comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tickets.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('comments.id', ondelete='CASCADE'),
                  nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('idx_comments_ticket_id', 'comments', ['ticket_id'])
    op.create_index('idx_comments_user_id', 'comments', ['user_id'])


def downgrade() -> None:
    """
    Undo the migration - removes all tables in reverse order.
    
    Run with: alembic downgrade -1
    """
    op.drop_table('comments')
    op.drop_table('tickets')
    op.drop_table('users')
    op.drop_table('organizations')