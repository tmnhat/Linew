"""Add SEO tracking fields to articles table

Revision ID: 007
Revises: 006
Create Date: 2026-05-01

This migration adds fields for tracking SEO indexing status and internal linking.
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add SEO tracking columns to articles table
    op.add_column(
        'articles',
        sa.Column('indexed_google', sa.Boolean(), nullable=True, server_default='false')
    )
    op.add_column(
        'articles',
        sa.Column('indexed_bing', sa.Boolean(), nullable=True, server_default='false')
    )
    op.add_column(
        'articles',
        sa.Column('last_indexed_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'articles',
        sa.Column('internal_links_updated_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'articles',
        sa.Column('indexing_error', sa.String(length=500), nullable=True)
    )

    # Create index for faster queries
    op.create_index(
        'ix_articles_indexed_google',
        'articles',
        ['indexed_google'],
        unique=False
    )
    op.create_index(
        'ix_articles_indexed_bing',
        'articles',
        ['indexed_bing'],
        unique=False
    )
    op.create_index(
        'ix_articles_last_indexed_at',
        'articles',
        ['last_indexed_at'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_articles_last_indexed_at', 'articles')
    op.drop_index('ix_articles_indexed_bing', 'articles')
    op.drop_index('ix_articles_indexed_google', 'articles')
    op.drop_column('articles', 'indexing_error')
    op.drop_column('articles', 'internal_links_updated_at')
    op.drop_column('articles', 'last_indexed_at')
    op.drop_column('articles', 'indexed_bing')
    op.drop_column('articles', 'indexed_google')
