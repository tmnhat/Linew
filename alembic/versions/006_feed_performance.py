"""
Add indexes for Smart Feed performance optimization

Revision ID: 006_feed_performance
Revises: 005_distributed_locks
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '006_feed_performance'
down_revision = '005_distributed_locks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for Smart Feed query performance.

    The Smart Feed queries articles by:
    1. state = 'PUBLISHED'
    2. published_at DESC
    3. category filter

    This migration adds:
    - Partial index on (state, published_at DESC) WHERE state = 'PUBLISHED'
    - Index on category for category filtering
    - Composite index on (state, category, published_at DESC)
    - Index on trend_score for missed articles ordering
    - Index for breaking news filtering
    """

    # Partial index for published articles - speeds up the main feed query
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_feed_published
        ON articles (state, published_at DESC)
        WHERE state = 'PUBLISHED'
    """)

    # Index on category for category filtering in feed
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_category
        ON articles (category)
        WHERE state = 'PUBLISHED'
    """)

    # Composite index for combined state + category + published_at queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_feed_category
        ON articles (state, category, published_at DESC)
        WHERE state = 'PUBLISHED'
    """)

    # Index for trend_score ordering (used in missed articles)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_trend_score
        ON articles (trend_score DESC NULLS LAST)
        WHERE state = 'PUBLISHED'
    """)

    # Index for article_type filtering (breaking news)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_breaking
        ON articles (article_type, published_at DESC)
        WHERE state = 'PUBLISHED' AND article_type = 'breaking'
    """)


def downgrade() -> None:
    """Remove Smart Feed indexes."""
    op.execute("DROP INDEX IF EXISTS idx_articles_breaking")
    op.execute("DROP INDEX IF EXISTS idx_articles_trend_score")
    op.execute("DROP INDEX IF EXISTS idx_articles_feed_category")
    op.execute("DROP INDEX IF EXISTS idx_articles_category")
    op.execute("DROP INDEX IF EXISTS idx_articles_feed_published")
