"""
Distribution API routes.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.distribution import DistributionLog, NewsletterSubscriber
from app.distribution.models import (
    NewsletterSubscribeRequest,
    NewsletterSubscribeResponse,
    NewsletterUnsubscribeRequest,
    NewsletterStatsResponse,
    DistributionStatsResponse,
)
from app.distribution import newsletter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["distribution"])


# === Newsletter Endpoints ===

class UnsubscribeResponse(BaseModel):
    success: bool
    message: str


@router.post("/newsletter/subscribe", response_model=NewsletterSubscribeResponse)
async def subscribe_to_newsletter(
    data: NewsletterSubscribeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Subscribe an email to the newsletter."""
    success, message = await newsletter.subscribe(
        db=db,
        email=data.email,
        name=data.name,
        categories=data.categories,
        frequency=data.frequency,
    )

    return NewsletterSubscribeResponse(
        success=success,
        message=message,
    )


@router.post("/newsletter/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe_from_newsletter(
    data: NewsletterUnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe an email from the newsletter."""
    success, message = await newsletter.unsubscribe(db=db, email=data.email)

    return UnsubscribeResponse(success=success, message=message)


@router.get("/newsletter/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe_from_newsletter_get(
    email: str = Query(..., description="Email address to unsubscribe"),
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe an email from the newsletter (GET endpoint for link clicks)."""
    success, message = await newsletter.unsubscribe(db=db, email=email)

    return UnsubscribeResponse(success=success, message=message)


@router.get("/newsletter/stats", response_model=NewsletterStatsResponse)
async def get_newsletter_stats(db: AsyncSession = Depends(get_db)):
    """Get newsletter statistics."""
    # Count total, active, inactive
    total_stmt = select(func.count(NewsletterSubscriber.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    active_stmt = select(func.count(NewsletterSubscriber.id)).where(
        NewsletterSubscriber.is_active == True
    )
    active_result = await db.execute(active_stmt)
    active = active_result.scalar() or 0

    inactive = total - active

    # Count by category
    by_category = {}
    all_subs = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)
    )
    for sub in all_subs.scalars().all():
        for cat in (sub.categories or []):
            by_category[cat] = by_category.get(cat, 0) + 1

    return NewsletterStatsResponse(
        total=total,
        active=active,
        inactive=inactive,
        by_category=by_category,
    )


@router.get("/newsletter/subscribers")
async def get_subscribers(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """Get list of subscribers (admin endpoint)."""
    stmt = (
        select(NewsletterSubscriber)
        .order_by(NewsletterSubscriber.subscribed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    subscribers = result.scalars().all()

    return {
        "subscribers": [
            {
                "id": str(s.id),
                "email": s.email,
                "name": s.name,
                "is_active": s.is_active,
                "categories": s.categories,
                "frequency": s.frequency,
                "subscribed_at": s.subscribed_at.isoformat() if s.subscribed_at else None,
                "total_sent": s.total_sent,
                "total_opened": s.total_opened,
            }
            for s in subscribers
        ],
        "total": len(subscribers),
    }


# === Distribution Endpoints ===

@router.get("/distribution/stats")
async def get_distribution_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30),
):
    """Get distribution statistics."""
    from datetime import timedelta

    from app.distribution.service import DistributionService

    service = DistributionService()
    stats = await service.get_distribution_stats(db, days=days)

    # Count today's published articles
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    articles_stmt = select(func.count("*")).where(
        DistributionLog.created_at >= today_start
    )
    articles_result = await db.execute(articles_stmt)
    today_distributed = articles_result.scalar() or 0

    return {
        "stats": stats,
        "period_days": days,
        "today_distributed": today_distributed,
    }


@router.get("/distribution/logs")
async def get_distribution_logs(
    db: AsyncSession = Depends(get_db),
    article_id: str = Query(None),
    channel: str = Query(None),
    status: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """Get distribution logs."""
    conditions = []
    if article_id:
        conditions.append(DistributionLog.article_id == article_id)
    if channel:
        conditions.append(DistributionLog.channel == channel)
    if status:
        conditions.append(DistributionLog.status == status)

    stmt = (
        select(DistributionLog)
        .where(*conditions)
        .order_by(DistributionLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "article_id": str(log.article_id),
                "channel": log.channel,
                "status": log.status,
                "external_id": log.external_id,
                "external_url": log.external_url,
                "error": log.error,
                "retry_count": log.retry_count,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }


@router.post("/distribution/trigger/{article_id}")
async def trigger_distribution(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger distribution for an article."""
    from app.distribution.service import DistributionService

    service = DistributionService()
    result = await service.distribute_article(article_id)

    return {"article_id": article_id, "results": result}


# === Test Endpoints ===

@router.get("/distribution/test/telegram")
async def test_telegram():
    """Test Telegram connection."""
    from app.distribution.telegram_channel import test_telegram_connection

    return await test_telegram_connection()


@router.get("/distribution/test/facebook")
async def test_facebook():
    """Test Facebook connection."""
    from app.distribution.facebook import test_facebook_connection

    return await test_facebook_connection()


@router.get("/distribution/facebook/status")
async def get_facebook_rate_limit_status():
    """Get Facebook rate limit status and posting statistics."""
    import asyncio
    from app.distribution.facebook import check_facebook_rate_limit_status

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_facebook_rate_limit_status)


@router.get("/distribution/test/twitter")
async def test_twitter():
    """Test Twitter connection."""
    from app.distribution.twitter import test_twitter_connection

    return await test_twitter_connection()


@router.get("/distribution/test/newsletter")
async def test_newsletter():
    """Test newsletter SMTP connection."""
    return await newsletter.test_smtp_connection()


# === Pause/Resume Endpoints ===

@router.post("/distribution/pause/{channel}")
async def pause_channel(
    channel: str,
    db: AsyncSession = Depends(get_db),
):
    """Pause a distribution channel (facebook or twitter)."""
    from app.distribution.service import DistributionService

    try:
        service = DistributionService()
        await service.pause_channel(channel)
        return {"success": True, "channel": channel, "status": "paused"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to pause channel {channel}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/distribution/resume/{channel}")
async def resume_channel(
    channel: str,
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused distribution channel (facebook or twitter)."""
    from app.distribution.service import DistributionService

    try:
        service = DistributionService()
        await service.resume_channel(channel)
        return {"success": True, "channel": channel, "status": "resumed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resume channel {channel}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/distribution/channel-status")
async def get_channel_status(
    db: AsyncSession = Depends(get_db),
):
    """Get the pause/resume status of all distribution channels."""
    from app.distribution.service import DistributionService

    service = DistributionService()
    status = await service.get_channel_status()
    return status
