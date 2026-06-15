"""
PostgreSQL Cleanup Service - cleans up old data after archiving.
IMPORTANT: Only deletes data that has been archived (is_archived=True).
NEVER deletes PUBLISHED articles.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_signal import RawSignal
from app.models.article import Article, ArticleState
from app.models.prediction_models import PredictionFinal, MarketResearch, TechnicalIndicator
from app.models.publish_log import PublishLog
from app.models.price_history import PriceHistory
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


class PostgresCleanup:
    """Cleanup old data from PostgreSQL after archiving."""

    async def cleanup_raw_signals(self, session: AsyncSession, keep_days: int = 60) -> int:
        """
        Delete raw_signals older than keep_days AND already archived.
        IMPORTANT: Only deletes if is_archived=True.
        """
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        stmt = delete(RawSignal).where(
            RawSignal.created_at < cutoff,
            RawSignal.is_archived == True,
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} raw_signals older than {keep_days} days (archived only)")
        return count

    async def cleanup_articles(self, session: AsyncSession, keep_days: int = 30) -> int:
        """
        Delete old articles that are NOT PUBLISHED.
        NEVER deletes articles in PUBLISHED state.
        """
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        # Never delete PUBLISHED articles - they stay forever in PostgreSQL
        non_published_states = [
            ArticleState.SIGNAL_COLLECTED.value,
            ArticleState.CATEGORIZED.value,
            ArticleState.TRENDING.value,
            ArticleState.SKIPPED.value,
            ArticleState.EXPIRED.value,
            ArticleState.RESEARCHED.value,
            ArticleState.WRITTEN.value,
            ArticleState.GOVERNED.value,
            ArticleState.APPROVED.value,
            ArticleState.REJECTED.value,
            ArticleState.FAILED.value,
        ]

        stmt = delete(Article).where(
            Article.created_at < cutoff,
            Article.state.in_(non_published_states),
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} non-published articles older than {keep_days} days")
        return count

    async def cleanup_predictions(self, session: AsyncSession, keep_days: int = 90) -> int:
        """Delete old predictions after archiving."""
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        stmt = delete(PredictionFinal).where(
            PredictionFinal.generated_at < cutoff,
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} predictions older than {keep_days} days")
        return count

    async def cleanup_market_research(self, session: AsyncSession, keep_days: int = 90) -> int:
        """Delete old market research after archiving."""
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        stmt = delete(MarketResearch).where(
            MarketResearch.generated_at < cutoff,
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} market research older than {keep_days} days")
        return count

    async def cleanup_technical_indicators(self, session: AsyncSession, keep_days: int = 90) -> int:
        """Delete old technical indicators."""
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        stmt = delete(TechnicalIndicator).where(
            TechnicalIndicator.created_at < cutoff,
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} technical indicators older than {keep_days} days")
        return count

    async def cleanup_price_history(self, session: AsyncSession, keep_days: int = 730) -> int:
        """
        Delete old price history data.
        Keep 2 years of data for historical analysis.
        """
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        stmt = delete(PriceHistory).where(
            PriceHistory.date < cutoff.date(),
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} price history older than {keep_days} days")
        return count

    async def cleanup_publish_logs(self, session: AsyncSession, keep_days: int = 90) -> int:
        """Delete old publish logs."""
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        stmt = delete(PublishLog).where(
            PublishLog.created_at < cutoff,
        )
        result = await session.execute(stmt)
        count = result.rowcount

        logger.info(f"Cleaned up {count} publish logs older than {keep_days} days")
        return count

    async def run_all_cleanup(
        self,
        raw_signals_days: int = 60,
        articles_days: int = 30,
        predictions_days: int = 90,
        market_research_days: int = 90,
        technical_indicators_days: int = 90,
        price_history_days: int = 730,
        publish_logs_days: int = 90,
    ) -> dict:
        """
        Run all cleanup operations.
        Returns dict with counts for each operation.
        """
        results = {}
        async with async_session_maker() as session:
            try:
                results["raw_signals"] = await self.cleanup_raw_signals(session, raw_signals_days)
                results["articles"] = await self.cleanup_articles(session, articles_days)
                results["predictions"] = await self.cleanup_predictions(session, predictions_days)
                results["market_research"] = await self.cleanup_market_research(session, market_research_days)
                results["technical_indicators"] = await self.cleanup_technical_indicators(session, technical_indicators_days)
                results["price_history"] = await self.cleanup_price_history(session, price_history_days)
                results["publish_logs"] = await self.cleanup_publish_logs(session, publish_logs_days)

                await session.commit()
                logger.info(f"All cleanup completed: {results}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Cleanup failed: {e}")
                results["error"] = str(e)

        return results

    async def get_counts(self, session: AsyncSession) -> dict:
        """Get current record counts for each table."""
        counts = {}

        # Raw signals
        result = await session.execute(select(func.count()).select_from(RawSignal))
        counts["raw_signals"] = result.scalar()

        # Raw signals archived
        result = await session.execute(
            select(func.count()).select_from(RawSignal).where(RawSignal.is_archived == True)
        )
        counts["raw_signals_archived"] = result.scalar()

        # Articles by state
        for state in ArticleState:
            result = await session.execute(
                select(func.count()).select_from(Article).where(Article.state == state.value)
            )
            counts[f"articles_{state.value.lower()}"] = result.scalar()

        # Total articles
        result = await session.execute(select(func.count()).select_from(Article))
        counts["articles_total"] = result.scalar()

        # Predictions
        result = await session.execute(select(func.count()).select_from(PredictionFinal))
        counts["predictions"] = result.scalar()

        # Market research
        result = await session.execute(select(func.count()).select_from(MarketResearch))
        counts["market_research"] = result.scalar()

        return counts
