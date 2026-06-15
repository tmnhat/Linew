"""
Queue manager - priority calculation and article selection.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleState
from app.models.setting import Setting

logger = logging.getLogger(__name__)

# States eligible for queue processing
QUEUABLE_STATES = {
    ArticleState.SIGNAL_COLLECTED.value,
    ArticleState.CATEGORIZED.value,
    ArticleState.TRENDING.value,
    ArticleState.RESEARCHED.value,  # Added to process articles stuck at RESEARCHED
}


def calculate_priority(
    trend_score: float,
    signal_frequency: int,
    article_age_hours: float,
    category_boost: bool = False,
    base: float = 15.0,
) -> int:
    """
    Calculate article priority (0-100).

    Factors:
    - trend_score > 0.7: +30
    - signal_frequency: +20
    - recency < 2h: +20
    - category_boost: +15
    - base: +15

    Returns integer priority (0-100).
    """
    score = base

    # Trend score boost
    if trend_score and trend_score > 0.7:
        score += 30

    # Signal frequency
    if signal_frequency > 1:
        score += min(signal_frequency * 5, 20)

    # Recency
    if article_age_hours < 2:
        score += 20
    elif article_age_hours < 6:
        score += 15
    elif article_age_hours < 12:
        score += 10

    # Category boost
    if category_boost:
        score += 15

    return min(int(score), 100)


async def get_pipeline_settings(session: AsyncSession) -> dict:
    """Get pipeline settings from database."""
    result = await session.execute(
        select(Setting).where(Setting.key == "pipeline")
    )
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        return setting.value
    return {}


async def should_skip_topic_due_to_cooldown(
    session: AsyncSession,
    category: str,
    cooldown_hours: int,
    max_articles: int,
) -> bool:
    """
    Check if we should skip a topic due to cooldown.
    Returns True if we should skip (too many recent articles in this topic).
    """
    cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)

    # Count recently published articles in this category
    stmt = (
        select(func.count(Article.id))
        .where(
            and_(
                Article.category == category,
                Article.state == ArticleState.PUBLISHED.value,
                Article.updated_at >= cutoff,
            )
        )
    )
    result = await session.execute(stmt)
    count = result.scalar() or 0

    return count >= max_articles


async def get_next_articles(
    session: AsyncSession,
    limit: int = 10,
    category: Optional[str] = None,
    mode: Optional[str] = None,
) -> list[Article]:
    """
    Get next articles to process from the queue.

    Orders by:
    1. Priority (descending)
    2. Queued at (ascending - FIFO within same priority)

    Filters by:
    - Article state (QUEUABLE_STATES)
    - Category (if specified)
    - Mode (if specified)
    - Trending only mode (if enabled)
    - Topic cooldown (if enabled)
    """
    # Get pipeline settings
    settings = await get_pipeline_settings(session)
    trending_only = settings.get("trending_only_mode", False)
    min_trend_score = settings.get("min_trend_score", 0.5)
    cooldown_hours = settings.get("topic_cooldown_hours", 2)
    max_articles_per_topic = settings.get("max_articles_per_topic_per_cooldown", 3)

    stmt = (
        select(Article)
        .where(Article.state.in_(QUEUABLE_STATES))
    )

    # Apply trending_only_mode filter
    if trending_only:
        logger.info(f"Trending only mode enabled, filtering by min_trend_score={min_trend_score}")
        stmt = stmt.where(Article.trend_score >= min_trend_score)

    if category:
        stmt = stmt.where(Article.category == category)

    if mode:
        stmt = stmt.where(Article.mode == mode)

    # Order by priority and queued_at
    stmt = stmt.order_by(Article.priority.desc(), Article.queued_at.asc().nullsfirst())
    stmt = stmt.limit(limit * 2)  # Fetch more to filter out cooldown topics

    result = await session.execute(stmt)
    all_articles = result.scalars().all()

    # Apply topic cooldown filter
    if cooldown_hours > 0:
        filtered_articles = []
        skipped_by_cooldown = 0

        for article in all_articles:
            article_category = article.category
            if article_category:
                should_skip = await should_skip_topic_due_to_cooldown(
                    session,
                    article_category,
                    cooldown_hours,
                    max_articles_per_topic,
                )
                if should_skip:
                    skipped_by_cooldown += 1
                    continue
            filtered_articles.append(article)

        if skipped_by_cooldown > 0:
            logger.info(f"Skipped {skipped_by_cooldown} articles due to topic cooldown")

        articles = filtered_articles[:limit]
    else:
        articles = all_articles[:limit]

    logger.debug(f"Got {len(articles)} articles from queue (filtered from {len(all_articles)})")
    return list(articles)


async def queue_articles(
    session: AsyncSession,
    article_ids: list[str],
    priority: Optional[int] = None,
) -> int:
    """
    Queue articles for processing.
    Updates queued_at timestamp and optionally priority.
    """
    now = datetime.utcnow()
    values = {"queued_at": now}
    if priority is not None:
        values["priority"] = priority

    stmt = (
        update(Article)
        .where(Article.id.in_(article_ids))
        .values(**values)
    )

    result = await session.execute(stmt)
    await session.commit()

    logger.info(f"Queued {result.rowcount} articles")
    return result.rowcount


async def expire_old_signals(
    session: AsyncSession,
    expiry_hours: int = 24,
) -> int:
    """
    Mark old signals as EXPIRED.
    Articles that have been in QUEUABLE_STATES for too long.
    """
    cutoff = datetime.utcnow() - timedelta(hours=expiry_hours)

    stmt = (
        update(Article)
        .where(
            and_(
                Article.state.in_(QUEUABLE_STATES),
                Article.created_at < cutoff,
            )
        )
        .values(
            state=ArticleState.EXPIRED.value,
            fail_reason="Signal expired - not processed within time window",
        )
    )

    result = await session.execute(stmt)
    await session.commit()

    expired_count = result.rowcount
    if expired_count > 0:
        logger.info(f"Expired {expired_count} old signals")

    return expired_count


async def get_queue_stats(session: AsyncSession) -> dict:
    """Get queue statistics."""
    from sqlalchemy import func

    # Count by state
    stmt = (
        select(Article.state, func.count(Article.id))
        .group_by(Article.state)
    )
    result = await session.execute(stmt)
    by_state = {row[0]: row[1] for row in result.all()}

    # Count pending (articles that can be processed)
    pending = sum(by_state.get(state, 0) for state in QUEUABLE_STATES)

    # Count queued (articles with queued_at set)
    stmt_queued = (
        select(func.count(Article.id))
        .where(Article.queued_at.isnot(None))
    )
    result_queued = await session.execute(stmt_queued)
    queued = result_queued.scalar() or 0

    # Count in_progress (articles currently being processed)
    in_progress_states = {
        ArticleState.RESEARCHED.value,
        ArticleState.WRITTEN.value,
        ArticleState.GOVERNED.value,
        ArticleState.CATEGORIZED.value,
        ArticleState.TRENDING.value,
    }
    in_progress = sum(by_state.get(state, 0) for state in in_progress_states)

    # Get oldest queued article
    stmt = (
        select(Article)
        .where(Article.queued_at.isnot(None))
        .order_by(Article.queued_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    oldest = result.scalar_one_or_none()

    return {
        "pending": pending,
        "queued": queued,
        "in_progress": in_progress,
        "by_state": by_state,
        "oldest_queued_at": oldest.queued_at.isoformat() if oldest else None,
        "total_articles": sum(by_state.values()),
    }
