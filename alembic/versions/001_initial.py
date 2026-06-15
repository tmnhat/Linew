"""Alembic migration script: Initial migration with all model changes.

Creates all tables with proper schema and adds necessary indexes.
"""

from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create sources table
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('feed_url', sa.String(2048), nullable=False, unique=True),
        sa.Column('site_url', sa.String(2048), nullable=True),
        sa.Column('category_hint', sa.String(100), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('fetch_interval', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('crawl_difficulty', sa.String(10), nullable=False, server_default='easy'),
        sa.Column('requires_flaresolverr', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('requires_proxy', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_paywall', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('custom_headers', postgresql.JSONB, nullable=True),
        sa.Column('content_selector', sa.String(255), nullable=True),
        sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.Index('idx_sources_active', 'is_active', postgresql_where=sa.text('is_active = true')),
    )

    # 2. Create articles table
    op.create_table(
        'articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_url', sa.String(2048), nullable=False),
        sa.Column('original_title', sa.String(500), nullable=False),
        sa.Column('title_hash', sa.String(64), nullable=False, index=True),
        sa.Column('slug', sa.String(500), nullable=True, unique=True),
        sa.Column('original_summary', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('original_image_url', sa.String(2048), nullable=True),
        sa.Column('crawled_images', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('featured_image_wp_id', sa.Integer(), nullable=True),
        sa.Column('signal_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta_title', sa.String(500), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('state', sa.String(30), nullable=False, index=True),
        sa.Column('pipeline_status', sa.String(30), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.Column('wp_post_id', sa.Integer(), nullable=True, unique=True),
        sa.Column('wp_url', sa.String(2048), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_articles_source', 'articles', ['source_id'])
    op.create_index('idx_articles_state', 'articles', ['state'])
    op.create_index('idx_articles_created', 'articles', ['created_at'])
    op.create_index('idx_articles_slug', 'articles', ['slug'])

    # 3. Create signal_queue table
    op.create_table(
        'signal_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('queue_name', sa.String(50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('payload', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.Index('idx_signal_queue_priority', 'priority'),
    )

    # 4. Create token_usage table
    op.create_table(
        'token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('task_type', sa.String(50), nullable=False, index=True),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated_cost', sa.Numeric(10, 6), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True, index=True),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('extra_data', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='SET NULL'),
    )

    # 5. Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(20, 8), nullable=True),
        sa.Column('high', sa.Numeric(20, 8), nullable=True),
        sa.Column('low', sa.Numeric(20, 8), nullable=True),
        sa.Column('close', sa.Numeric(20, 8), nullable=True),
        sa.Column('adjusted_close', sa.Numeric(20, 8), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='yahoo'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('symbol', 'date', name='uq_price_history_symbol_date'),
        sa.Index('idx_price_history_symbol_date', 'symbol', 'date'),
        sa.Index('idx_price_history_created', 'created_at'),
    )

    # 6. Create predictions table
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('prediction_date', sa.Date(), nullable=False),
        sa.Column('predicted_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('low_bound', sa.Numeric(20, 8), nullable=False),
        sa.Column('high_bound', sa.Numeric(20, 8), nullable=False),
        sa.Column('model_used', sa.String(50), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('actual_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('symbol', 'prediction_date', 'model_used', name='uq_predictions_symbol_date_model'),
        sa.Index('idx_predictions_symbol_date', 'symbol', 'prediction_date'),
        sa.Index('idx_predictions_generated', 'generated_at'),
    )


def downgrade() -> None:
    op.drop_table('predictions')
    op.drop_table('price_history')
    op.drop_table('token_usage')
    op.drop_table('signal_queue')
    op.drop_table('articles')
    op.drop_table('sources')
