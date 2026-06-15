"""
Create distributed_locks table for database-based locking fallback

Revision ID: 005_distributed_locks
Revises: 004_distribution_unique
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '005_distributed_locks'
down_revision = '004_distribution_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create distributed_locks table."""
    op.create_table(
        'distributed_locks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('lock_type', sa.String(length=50), nullable=False),
        sa.Column('lock_key', sa.String(length=255), nullable=False),
        sa.Column('owner_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(
        'idx_distributed_locks_type_key',
        'distributed_locks',
        ['lock_type', 'lock_key']
    )
    op.create_index(
        'idx_distributed_locks_expires',
        'distributed_locks',
        ['expires_at']
    )


def downgrade() -> None:
    """Drop distributed_locks table."""
    op.drop_index('idx_distributed_locks_expires', table_name='distributed_locks')
    op.drop_index('idx_distributed_locks_type_key', table_name='distributed_locks')
    op.drop_table('distributed_locks')
