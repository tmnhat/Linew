"""Alembic migration script: Raw Signals table.

Creates raw_signals table to store all crawled RSS items in original form.
This is the "gold mine" for analytics - we save EVERYTHING, including duplicates.
"""
from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003a_raw_signals'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'raw_signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        # Source reference
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Source metadata
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('feed_url', sa.String(2048), nullable=True),
        sa.Column('feed_title', sa.String(255), nullable=True),
        # Original data from RSS (NEVER modified)
        sa.Column('original_url', sa.String(2048), nullable=False),
        sa.Column('original_title', sa.String(1024), nullable=False),
        sa.Column('original_summary', sa.Text(), nullable=True),
        sa.Column('original_content', sa.Text(), nullable=True),
        sa.Column('original_html', sa.Text(), nullable=True),
        sa.Column('original_image_url', sa.String(2048), nullable=True),
        sa.Column('original_author', sa.String(255), nullable=True),
        sa.Column('original_language', sa.String(10), nullable=True),
        sa.Column('original_tags', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        # Hashing for dedup & tracking
        sa.Column('url_hash', sa.String(64), nullable=False),
        sa.Column('title_hash', sa.String(64), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        # Content metrics
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('has_image', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        # Processing tracking
        sa.Column('was_processed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processing_result', sa.String(30), nullable=True),
        sa.Column('processing_note', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        # Archive tracking
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Indexes
        sa.Index('idx_raw_signals_created', 'created_at'),
        sa.Index('idx_raw_signals_source', 'source_id', 'created_at'),
        sa.Index('idx_raw_signals_url_hash', 'url_hash'),
        sa.Index('idx_raw_signals_title_hash', 'title_hash'),
        sa.Index('idx_raw_signals_processed', 'was_processed', 'created_at'),
        sa.Index('idx_raw_signals_language', 'original_language'),
        sa.Index('idx_raw_signals_result', 'processing_result'),
        sa.Index('idx_raw_signals_archived', 'is_archived'),
    )


def downgrade() -> None:
    op.drop_table('raw_signals')
