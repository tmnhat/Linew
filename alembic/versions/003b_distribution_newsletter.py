"""Alembic migration: Distribution logs và Newsletter subscribers.

Revision ID: 003
Revises: 002
Create Date: 2026-04-21
"""
from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003b_distribution_newsletter'
down_revision = '003a_raw_signals'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create distribution_logs table
    op.create_table(
        'distribution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('external_url', sa.String(2048), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.Index('idx_dist_logs_article', 'article_id'),
        sa.Index('idx_dist_logs_channel_status', 'channel', 'status'),
        sa.Index('idx_dist_logs_created', 'created_at'),
    )

    # 2. Create newsletter_subscribers table
    op.create_table(
        'newsletter_subscribers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('subscribed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('categories', postgresql.JSONB, nullable=False, server_default=sa.text("'[\"tech\", \"finance\"]'::jsonb")),
        sa.Column('frequency', sa.String(20), nullable=False, server_default='daily'),
        sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_opened', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Index('idx_newsletter_active', 'is_active', postgresql_where=sa.text('is_active = true')),
        sa.Index('idx_newsletter_email', 'email'),
    )


def downgrade() -> None:
    op.drop_table('newsletter_subscribers')
    op.drop_table('distribution_logs')
