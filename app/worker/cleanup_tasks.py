"""
Cleanup tasks for old data.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleState
from app.models.price_history import PriceHistory
from app.models.prediction import Prediction
from app.models.publish_log import PublishLog

logger = logging.getLogger(__name__)


async def cleanup_old_data(session: AsyncSession) -> dict:
    """Clean up old data based on retention policies."""
    results = {}

    try:
        now = datetime.utcnow()

        # Cleanup articles: EXPIRED, FAILED, REJECTED > 30 days
        cutoff_expired = now - timedelta(days=30)
        stmt = delete(Article).where(
            and_(
                Article.state.in_([
                    ArticleState.EXPIRED.value,
                    ArticleState.FAILED.value,
                    ArticleState.REJECTED.value,
                ]),
                Article.created_at < cutoff_expired,
            )
        )
        result = await session.execute(stmt)
        results["articles_old"] = result.rowcount

        # Cleanup articles: SKIPPED > 7 days
        cutoff_skipped = now - timedelta(days=7)
        stmt = delete(Article).where(
            and_(
                Article.state == ArticleState.SKIPPED.value,
                Article.created_at < cutoff_skipped,
            )
        )
        result = await session.execute(stmt)
        results["articles_skipped"] = result.rowcount

        # Cleanup price_history > 2 years
        cutoff_price = now - timedelta(days=730)  # 2 years
        stmt = delete(PriceHistory).where(
            PriceHistory.date < cutoff_price
        )
        result = await session.execute(stmt)
        results["price_history"] = result.rowcount

        # Cleanup predictions > 90 days
        cutoff_pred = now - timedelta(days=90)
        stmt = delete(Prediction).where(
            Prediction.generated_at < cutoff_pred
        )
        result = await session.execute(stmt)
        results["predictions"] = result.rowcount

        # Cleanup publish_logs > 90 days
        cutoff_logs = now - timedelta(days=90)
        stmt = delete(PublishLog).where(
            PublishLog.created_at < cutoff_logs
        )
        result = await session.execute(stmt)
        results["publish_logs"] = result.rowcount

        await session.commit()

        total = sum(results.values())
        logger.info(f"Cleanup completed: removed {total} old records")
        logger.debug(f"Cleanup details: {results}")

        return results

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        await session.rollback()
        raise
