#!/usr/bin/env python3
"""
Standalone migration script to add Smart Feed performance indexes.

Run with: python migrations/feed_performance_index.py up
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_migration():
    """Create indexes for Smart Feed performance."""
    logger.info("Starting Smart Feed index migration...")

    settings = get_settings()
    engine = create_async_engine(settings.database_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # Check if indexes already exist
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'articles'
            AND indexname IN (
                'idx_articles_feed_published',
                'idx_articles_category',
                'idx_articles_feed_category',
                'idx_articles_trend_score',
                'idx_articles_breaking'
            )
        """))
        existing_indexes = set(row[0] for row in result)

        indexes_sql = [
            ('idx_articles_feed_published', """
                CREATE INDEX IF NOT EXISTS idx_articles_feed_published
                ON articles (state, published_at DESC)
                WHERE state = 'PUBLISHED'
            """),
            ('idx_articles_category', """
                CREATE INDEX IF NOT EXISTS idx_articles_category
                ON articles (category)
                WHERE state = 'PUBLISHED'
            """),
            ('idx_articles_feed_category', """
                CREATE INDEX IF NOT EXISTS idx_articles_feed_category
                ON articles (state, category, published_at DESC)
                WHERE state = 'PUBLISHED'
            """),
            ('idx_articles_trend_score', """
                CREATE INDEX IF NOT EXISTS idx_articles_trend_score
                ON articles (trend_score DESC NULLS LAST)
                WHERE state = 'PUBLISHED'
            """),
            ('idx_articles_breaking', """
                CREATE INDEX IF NOT EXISTS idx_articles_breaking
                ON articles (article_type, published_at DESC)
                WHERE state = 'PUBLISHED' AND article_type = 'breaking'
            """),
        ]

        for idx_name, sql in indexes_sql:
            if idx_name in existing_indexes:
                logger.info(f"Index {idx_name} already exists, skipping...")
                continue

            try:
                logger.info(f"Creating index: {idx_name}...")
                await conn.execute(text(sql))
                logger.info(f"Successfully created index: {idx_name}")
            except Exception as e:
                logger.error(f"Failed to create index {idx_name}: {e}")
                raise

    await engine.dispose()
    logger.info("Smart Feed index migration completed successfully!")


async def rollback_migration():
    """Remove Smart Feed indexes."""
    logger.info("Rolling back Smart Feed indexes...")

    settings = get_settings()
    engine = create_async_engine(settings.database_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        indexes = [
            'idx_articles_breaking',
            'idx_articles_trend_score',
            'idx_articles_feed_category',
            'idx_articles_category',
            'idx_articles_feed_published',
        ]

        for idx_name in indexes:
            try:
                logger.info(f"Dropping index: {idx_name}...")
                await conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                logger.info(f"Successfully dropped index: {idx_name}")
            except Exception as e:
                logger.error(f"Failed to drop index {idx_name}: {e}")

    await engine.dispose()
    logger.info("Rollback completed!")


async def verify_indexes():
    """Verify that indexes were created successfully."""
    logger.info("Verifying Smart Feed indexes...")

    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'articles'
            AND indexname LIKE 'idx_articles_%'
            ORDER BY indexname
        """))

        logger.info("\nCreated Smart Feed indexes:")
        for row in result:
            logger.info(f"  - {row[0]}")

    await engine.dispose()
    logger.info("\nIndex verification complete!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Smart Feed Index Migration')
    parser.add_argument(
        'action',
        choices=['up', 'down', 'verify'],
        help='Action to perform: up (create), down (drop), verify (check)'
    )
    args = parser.parse_args()

    if args.action == 'up':
        asyncio.run(run_migration())
        asyncio.run(verify_indexes())
    elif args.action == 'down':
        asyncio.run(rollback_migration())
    elif args.action == 'verify':
        asyncio.run(verify_indexes())


if __name__ == '__main__':
    main()
