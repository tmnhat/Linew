"""
Add unique constraint to prevent duplicate Facebook posts

Revision ID: 004_distribution_unique
Revises: 003_distribution_newsletter
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '004_distribution_unique'
down_revision = '003b_distribution_newsletter'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint for article_id + channel + status=success on distribution_logs."""
    
    # First, clean up any existing duplicate success entries
    # Keep only the first one (by created_at)
    op.execute("""
        DELETE FROM distribution_logs
        WHERE id NOT IN (
            SELECT DISTINCT ON (article_id, channel) id
            FROM distribution_logs
            WHERE status = 'success'
            ORDER BY article_id, channel, created_at ASC
        )
        AND status = 'success'
    """)
    
    # Add unique constraint using unique index
    # PostgreSQL partial unique index
    op.create_index(
        'idx_dist_logs_unique_success',
        'distribution_logs',
        ['article_id', 'channel'],
        unique=True,
        postgresql_where=sa.text("status = 'success'")
    )


def downgrade() -> None:
    """Remove unique constraint."""
    op.drop_index('idx_dist_logs_unique_success', table_name='distribution_logs')
