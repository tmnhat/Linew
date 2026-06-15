"""
Stats API routes.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.article import Article, ArticleState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics - optimized with minimal queries."""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # Single query for all today stats using conditional aggregation
    today_stmt = select(
        func.count(case((Article.state == ArticleState.SIGNAL_COLLECTED.value, 1))).label('collected_today'),
        func.count(case((Article.state == ArticleState.WRITTEN.value, 1))).label('written_today'),
        func.count(case((Article.state == ArticleState.PUBLISHED.value, 1))).label('published_today'),
        func.count(case((Article.state == ArticleState.FAILED.value, 1))).label('failed_today'),
    ).where(
        Article.created_at >= today_start,
        Article.created_at <= today_end,
    )
    today_result = await db.execute(today_stmt)
    today_row = today_result.one()

    # Also get published and failed counts using updated_at/published_at for today
    # This is needed because those fields track when the state changed
    published_stmt = select(func.count(Article.id)).where(
        Article.published_at >= today_start,
        Article.published_at <= today_end,
    )
    failed_stmt = select(func.count(Article.id)).where(
        Article.last_step_at >= today_start,
        Article.last_step_at <= today_end,
        Article.state == ArticleState.FAILED.value,
    )

    # Run both queries in parallel
    pub_result = await db.execute(published_stmt)
    fail_result = await db.execute(failed_stmt)

    published_today = pub_result.scalar() or 0
    failed_today = fail_result.scalar() or 0

    # Single query for by_state
    state_stmt = select(Article.state, func.count(Article.id)).group_by(Article.state)
    state_result = await db.execute(state_stmt)
    by_state = {row[0]: row[1] for row in state_result.all()}

    # Single query for by_category
    cat_stmt = select(
        Article.category,
        func.count(Article.id)
    ).where(
        Article.category.isnot(None)
    ).group_by(Article.category)
    cat_result = await db.execute(cat_stmt)
    by_category = {row[0]: row[1] for row in cat_result.all() if row[0]}

    # Single query for total
    total_stmt = select(func.count(Article.id))
    total_result = await db.execute(total_stmt)
    total_articles = total_result.scalar() or 0

    return {
        "today": {
            "collected": today_row.collected_today or 0,
            "written": today_row.written_today or 0,
            "published": published_today,
            "failed": failed_today,
        },
        "by_state": by_state,
        "by_category": by_category,
        "total": total_articles,
    }
