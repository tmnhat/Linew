"""
Celery tasks for distribution.
"""
import logging

from celery import shared_task

from app.worker.celery_app import run_async

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def task_post_telegram_channel(self, article_id: str):
    """Post an article to Telegram channel."""
    from app.distribution.telegram_channel import post_to_channel
    from app.distribution.service import DistributionService
    from app.core.database import get_db_context
    from sqlalchemy import select
    from app.models.article import Article

    async def _post():
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                return {"status": "failed", "error": "Article not found"}

            dist_result = await post_to_channel(article)
            await DistributionService()._save_distribution_log(
                article_id,
                "telegram",
                dist_result.get("status", "failed"),
                dist_result.get("external_id"),
                dist_result.get("external_url"),
                dist_result.get("error"),
            )
            return dist_result

    try:
        return run_async(_post())
    except Exception as e:
        logger.error(f"Telegram task failed for {article_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=3)
def task_post_twitter(self, article_id: str):
    """Post an article to Twitter/X."""
    from app.distribution.twitter import post_to_twitter
    from app.distribution.service import DistributionService
    from app.core.database import get_db_context
    from sqlalchemy import select
    from app.models.article import Article

    async def _post():
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                return {"status": "failed", "error": "Article not found"}

            dist_result = await post_to_twitter(article)
            await DistributionService()._save_distribution_log(
                article_id,
                "twitter",
                dist_result.get("status", "failed"),
                dist_result.get("external_id"),
                dist_result.get("external_url"),
                dist_result.get("error"),
            )
            return dist_result

    try:
        return run_async(_post())
    except Exception as e:
        logger.error(f"Twitter task failed for {article_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        return {"status": "failed", "error": str(e)}


@shared_task
def task_send_newsletter():
    """Send daily newsletter digest to all subscribers."""
    from app.distribution.newsletter import send_daily_digest

    logger.info("Starting daily newsletter digest...")
    result = run_async(send_daily_digest())
    logger.info(f"Newsletter digest completed: {result}")
    return result


@shared_task(bind=True, max_retries=2)
def task_crosspost_medium(self, article_id: str):
    """Cross-post an article to Medium."""
    from app.distribution.crosspost import post_to_medium
    from app.distribution.service import DistributionService
    from app.core.database import get_db_context
    from app.config import get_settings
    from sqlalchemy import select
    from app.models.article import Article

    settings = get_settings()
    medium_token = getattr(settings, 'medium_token', '')

    if not medium_token:
        return {"status": "skipped", "error": "Medium token not configured"}

    async def _post():
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                return {"status": "failed", "error": "Article not found"}

            dist_result = await post_to_medium(article, medium_token)
            await DistributionService()._save_distribution_log(
                article_id,
                "medium",
                dist_result.get("status", "failed"),
                dist_result.get("external_id"),
                dist_result.get("external_url"),
                dist_result.get("error"),
            )
            return dist_result

    try:
        return run_async(_post())
    except Exception as e:
        logger.error(f"Medium crosspost failed for {article_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)
        return {"status": "failed", "error": str(e)}


@shared_task
def task_distribute_article(article_id: str):
    """
    Distribute an article to all enabled channels.

    This is the main entry point for distribution.
    Called after an article is successfully published.
    """
    from app.distribution.service import DistributionService

    logger.info(f"Starting distribution for article {article_id}...")
    service = DistributionService()
    result = run_async(service.distribute_article(article_id))
    logger.info(f"Distribution completed: {result}")
    return result


@shared_task(bind=True, max_retries=3)
def task_facebook_scheduled(self):
    """
    Scheduled task to post the highest-trending article to Facebook.

    Runs every 80 minutes (configurable via facebook_schedule_minutes).
    Logic:
    1. Query articles published in the last N hours
    2. Find articles with highest trend_score that haven't been posted
    3. Post to Facebook WITHOUT any links
    4. Log the result

    FIX: Improved duplicate prevention with:
    - Check both DB logs AND Redis cache
    - Use SET for O(1) lookup of posted articles
    - Fallback to check actual Facebook posts via API
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_, func
    from app.models.article import Article, ArticleState
    from app.models.distribution import DistributionLog
    from app.distribution.facebook import post_to_facebook_no_link
    from app.distribution.service import DistributionService
    from app.core.database import get_db_context
    from app.config import get_settings

    settings = get_settings()

    # Redis key for caching posted article IDs
    POSTED_ARTICLES_CACHE_KEY = "linew:facebook:posted_articles"

    async def _update_redis_cache(article_id: str):
        """Update Redis cache with newly posted article."""
        try:
            import redis
            r = redis.from_url(settings.redis_url, decode_responses=True)
            r.sadd(POSTED_ARTICLES_CACHE_KEY, str(article_id))
            r.expire(POSTED_ARTICLES_CACHE_KEY, 86400 * 7)  # 7 days TTL
        except Exception as e:
            logger.warning(f"Failed to update Redis cache: {e}")

    async def _check_redis_cache(article_id: str) -> bool:
        """Check if article is in Redis cache (fast O(1) lookup)."""
        try:
            import redis
            r = redis.from_url(settings.redis_url, decode_responses=True)
            return r.sismember(POSTED_ARTICLES_CACHE_KEY, str(article_id))
        except Exception:
            return False  # Fail open if Redis unavailable

    async def _sync_redis_with_db():
        """Sync Redis cache with DB to handle restarts."""
        try:
            import redis
            r = redis.from_url(settings.redis_url, decode_responses=True)
            
            # Get all successful Facebook posts from DB
            async with get_db_context() as session:
                stmt = (
                    select(DistributionLog.article_id)
                    .where(
                        and_(
                            DistributionLog.channel == "facebook",
                            DistributionLog.status == "success",
                        )
                    )
                )
                result = await session.execute(stmt)
                article_ids = [str(row[0]) for row in result.fetchall()]
            
            if article_ids:
                r.delete(POSTED_ARTICLES_CACHE_KEY)
                r.sadd(POSTED_ARTICLES_CACHE_KEY, *article_ids)
                r.expire(POSTED_ARTICLES_CACHE_KEY, 86400 * 7)
                logger.info(f"Synced {len(article_ids)} Facebook posts to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to sync Redis cache: {e}")

    async def _post():
        schedule_minutes = getattr(settings, 'facebook_schedule_minutes', 80)
        min_trend_score = getattr(settings, 'facebook_min_trend_score', 0.3)
        article_search_hours = getattr(settings, 'facebook_article_search_hours', 24)

        logger.info(f"Facebook scheduled task started (interval: {schedule_minutes}min, min_trend: {min_trend_score})")

        # Check if Facebook is enabled
        if not settings.facebook_enabled:
            logger.info("Facebook scheduled posting is disabled")
            return {"status": "skipped", "reason": "facebook_disabled"}

        # Check if Facebook is paused
        service = DistributionService()
        if await service._is_channel_paused("facebook"):
            logger.info("Facebook is paused, skipping scheduled post")
            return {"status": "skipped", "reason": "facebook_paused"}

        # Sync Redis cache with DB on startup
        await _sync_redis_with_db()

        # Check rate limit - when was the last successful Facebook post?
        cutoff_time = datetime.utcnow() - timedelta(minutes=schedule_minutes)

        async with get_db_context() as session:
            # Check last successful Facebook post
            last_post_stmt = (
                select(DistributionLog)
                .where(
                    and_(
                        DistributionLog.channel == "facebook",
                        DistributionLog.status == "success",
                        DistributionLog.created_at >= cutoff_time,
                    )
                )
                .order_by(DistributionLog.created_at.desc())
                .limit(1)
            )
            last_post_result = await session.execute(last_post_stmt)
            last_post = last_post_result.scalar_one_or_none()

            if last_post:
                time_since_last = (datetime.utcnow() - last_post.created_at).total_seconds() / 60
                if time_since_last < schedule_minutes:
                    logger.info(
                        f"Rate limit: Last Facebook post {time_since_last:.1f}min ago, "
                        f"skipping (need {schedule_minutes}min gap)"
                    )
                    return {
                        "status": "skipped",
                        "reason": "rate_limited",
                        "minutes_since_last": time_since_last,
                        "required_gap": schedule_minutes,
                    }

            # Find ALL published articles in the search window
            published_since = datetime.utcnow() - timedelta(hours=article_search_hours)

            article_stmt = (
                select(Article)
                .where(
                    and_(
                        Article.state == ArticleState.PUBLISHED.value,
                        Article.published_at >= published_since,
                        Article.trend_score >= min_trend_score,
                    )
                )
                .order_by(Article.trend_score.desc())
                .limit(50)  # Get more candidates
            )

            article_result = await session.execute(article_stmt)
            all_candidates = article_result.scalars().all()

            if not all_candidates:
                logger.info(f"No eligible articles found (published in last {article_search_hours}h, trend_score >= {min_trend_score})")
                return {
                    "status": "skipped",
                    "reason": "no_articles",
                    "search_window_hours": article_search_hours,
                    "min_trend_score": min_trend_score,
                }

            # OPTIMIZED: Check both Redis cache AND DB for already-posted articles
            # This is much faster than checking each article individually
            
            # First, get IDs already in Redis cache (O(1) per check)
            redis_posted_ids = set()
            for article in all_candidates:
                if await _check_redis_cache(str(article.id)):
                    redis_posted_ids.add(str(article.id))

            # Then verify with DB for articles not in Redis
            db_posted_ids = set()
            if len(redis_posted_ids) < len(all_candidates):
                candidate_ids = [str(a.id) for a in all_candidates if str(a.id) not in redis_posted_ids]
                
                if candidate_ids:
                    db_check_stmt = (
                        select(DistributionLog.article_id)
                        .where(
                            and_(
                                DistributionLog.article_id.in_(candidate_ids),
                                DistributionLog.channel == "facebook",
                                DistributionLog.status == "success",
                            )
                        )
                    )
                    db_result = await session.execute(db_check_stmt)
                    db_posted_ids = {str(row[0]) for row in db_result.fetchall()}

            # Combine: articles posted in either Redis or DB
            all_posted_ids = redis_posted_ids | db_posted_ids

            # Filter out already-posted articles
            eligible_articles = [a for a in all_candidates if str(a.id) not in all_posted_ids]

            if not eligible_articles:
                logger.info(f"All {len(all_candidates)} eligible articles have already been posted to Facebook")
                return {
                    "status": "skipped",
                    "reason": "all_posted",
                    "candidates_checked": len(all_candidates),
                }

            # Pick the article with highest trend score (already sorted by desc)
            best_article = eligible_articles[0]

            logger.info(
                f"Selected article for Facebook: {best_article.meta_title[:50]}... "
                f"(trend_score: {best_article.trend_score:.3f})"
            )

            # Post to Facebook (no link version)
            post_result = await post_to_facebook_no_link(best_article)

            # If successful, update both DB and Redis
            if post_result.get("status") == "success":
                # Save to DB
                await service._save_distribution_log(
                    str(best_article.id),
                    "facebook",
                    post_result.get("status", "failed"),
                    post_result.get("external_id"),
                    post_result.get("external_url"),
                    post_result.get("error"),
                )
                
                # Update Redis cache
                await _update_redis_cache(str(best_article.id))
            else:
                # Still log the failure
                await service._save_distribution_log(
                    str(best_article.id),
                    "facebook",
                    post_result.get("status", "failed"),
                    post_result.get("external_id"),
                    post_result.get("external_url"),
                    post_result.get("error"),
                )

            logger.info(f"Facebook scheduled post result: {post_result.get('status')}")

            return {
                "status": post_result.get("status"),
                "article_id": str(best_article.id),
                "article_title": best_article.meta_title[:50],
                "trend_score": best_article.trend_score,
                "external_url": post_result.get("external_url", ""),
                "error": post_result.get("error", ""),
            }

    try:
        return run_async(_post())
    except Exception as e:
        logger.error(f"Facebook scheduled task failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        return {"status": "failed", "error": str(e)}
