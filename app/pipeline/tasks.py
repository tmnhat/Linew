"""
Pipeline Celery tasks - state machine transitions.
"""
import logging
import os
from datetime import datetime
from typing import Optional

from celery import chain, group
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.redis import publish_event, CHANNEL_ARTICLE_EVENTS
from app.core.locks import article_lock, title_lock, is_article_locked, is_title_locked
from app.models.article import Article, ArticleState, ArticleMode
from app.models.setting import Setting
from app.pipeline.analyzer import categorize_article, score_article_trend
from app.pipeline.writer import write_article
from app.pipeline.governor import govern_article
from app.pipeline.queue_manager import expire_old_signals, calculate_priority
from app.signals.web_scraper import fetch_article_content

logger = logging.getLogger(__name__)

# Lock TTL for pipeline tasks (20 minutes)
PIPELINE_LOCK_TTL = 1200


async def get_active_categories(session: AsyncSession) -> list[str]:
    """Get active categories from settings."""
    try:
        result = await session.execute(
            select(Setting).where(Setting.key == "pipeline")
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value.get("active_categories", [
                "Politics", "World", "Business", "Technology", "Science", "Health", "Sports", "Entertainment", "Finance", "Education"
            ])
    except Exception as e:
        logger.warning(f"Failed to get active categories: {e}")
    return ["Politics", "World", "Business", "Technology", "Science", "Health", "Sports", "Entertainment", "Finance", "Education"]


async def is_setting_enabled(session: AsyncSession, key: str, default: bool = True) -> bool:
    """Get pipeline setting value."""
    try:
        result = await session.execute(
            select(Setting).where(Setting.key == "pipeline")
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value.get(key, default)
    except Exception as e:
        logger.warning(f"Failed to get setting {key}: {e}")
    return default


def get_worker_id() -> str:
    """Get unique worker identifier."""
    return os.environ.get('HOSTNAME', 'unknown')


def check_article_can_process(article_id: str, title_hash: Optional[str] = None) -> tuple[bool, str]:
    """
    Check if article can be processed (not locked by another worker).
    
    Returns:
        tuple of (can_process, reason)
    """
    # Check article lock
    if is_article_locked(article_id):
        return False, "Article is being processed by another worker"
    
    # Check title lock if provided
    if title_hash and is_title_locked(title_hash):
        return False, "Similar article is being processed"
    
    return True, ""


async def process_with_lock(
    article_id: str,
    title_hash: Optional[str],
    pipeline_func,
) -> dict:
    """
    Wrapper to process article with distributed locking.
    
    Uses Redis locks to prevent duplicate processing:
    1. Article lock: prevents same article from being processed multiple times
    2. Title lock: prevents articles with same title from being processed
    
    Args:
        article_id: UUID of the article
        title_hash: SHA-256 hash of normalized title (optional)
        pipeline_func: Async function to run the pipeline
    
    Returns:
        dict with status and result
    """
    worker_id = get_worker_id()
    
    # Check if can process (fast path - no lock needed)
    can_process, reason = check_article_can_process(article_id, title_hash)
    if not can_process:
        logger.info(f"Article {article_id[:8]}... skipped: {reason}")
        return {"status": "skipped", "reason": reason}
    
    # Acquire locks
    article_lock_acquired = False
    title_lock_acquired = False
    
    try:
        # Acquire article lock
        async with article_lock(article_id, worker_id, ttl=PIPELINE_LOCK_TTL) as acquired:
            article_lock_acquired = acquired
            if not acquired:
                return {"status": "skipped", "reason": "Article locked by another worker"}
            
            # Acquire title lock if provided
            if title_hash:
                async with title_lock(title_hash, worker_id, ttl=PIPELINE_LOCK_TTL) as title_acquired:
                    title_lock_acquired = title_acquired
                    if not title_acquired:
                        return {"status": "skipped", "reason": "Similar article locked"}
                    
                    # Run the actual pipeline
                    result = await pipeline_func(article_id)
                    return result
            else:
                # Run without title lock
                result = await pipeline_func(article_id)
                return result
                
    except Exception as e:
        logger.error(f"Pipeline error for {article_id[:8]}...: {e}")
        return {"status": "error", "reason": str(e)}
    finally:
        # Locks are automatically released by context managers
        pass


async def update_article_state(
    article_id: str,
    state: str,
    **kwargs,
) -> Article:
    """Update article state and fields."""
    async with get_db_context() as session:
        values = {
            "state": state,
            "last_step_at": datetime.utcnow(),
            **kwargs,
        }
        stmt = (
            update(Article)
            .where(Article.id == article_id)
            .values(**values)
        )
        await session.execute(stmt)

        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one()
        await session.commit()

        # Publish state change event
        await publish_event(CHANNEL_ARTICLE_EVENTS, {
            "type": "article_state_change",
            "data": {
                "id": str(article.id),
                "state": state,
                "title": article.original_title[:100],
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

        return article


async def task_categorize(article_id: str) -> dict:
    """Task: Categorize article using AI."""
    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one()

            # Get active categories
            active_categories = await get_active_categories(session)

            # Categorize
            cat_result = await categorize_article(session, article)

            # Update article
            article.category = cat_result["category"]
            article.category_confidence = cat_result["confidence"]

            # Check if category is active
            if cat_result["category"] not in active_categories:
                article.state = ArticleState.SKIPPED.value
                article.fail_reason = f"Category '{cat_result['category']}' not in active categories"
                await session.commit()
                logger.info(f"Article {article_id} skipped: category={cat_result['category']}")
                return {"status": "skipped", "category": cat_result["category"]}

            # Calculate priority
            article.state = ArticleState.CATEGORIZED.value
            article.priority = calculate_priority(
                trend_score=article.trend_score or 0,
                signal_frequency=1,
                article_age_hours=0,
                category_boost=True,
            )
            article.last_step_at = datetime.utcnow()
            await session.commit()

            # Publish event
            await publish_event(CHANNEL_ARTICLE_EVENTS, {
                "type": "article_state_change",
                "data": {
                    "id": str(article.id),
                    "state": ArticleState.CATEGORIZED.value,
                    "category": cat_result["category"],
                    "confidence": cat_result["confidence"],
                },
                "timestamp": datetime.utcnow().isoformat(),
            })

            logger.info(f"Article {article_id} categorized: {cat_result['category']}")
            return {"status": "categorized", "category": cat_result["category"]}

    except Exception as e:
        logger.error(f"task_categorize failed for {article_id}: {e}")
        await update_article_state(article_id, ArticleState.FAILED.value, fail_reason=str(e))
        raise


async def task_score_trend(article_id: str) -> dict:
    """Task: Score article trend."""
    try:
        trend_enabled = True
        async with get_db_context() as session:
            trend_enabled = await is_setting_enabled(session, "trend_scoring_enabled", True)
            if not trend_enabled:
                logger.info(f"Trend scoring disabled, skipping for {article_id}")
                return {"status": "skipped", "reason": "trend_scoring_disabled"}

            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one()

            # Score trend
            score_result = await score_article_trend(session, article)

            # Get threshold from settings
            from app.pipeline.queue_manager import get_pipeline_settings
            settings = await get_pipeline_settings(session)
            threshold = settings.get("min_trend_score", 0.5)

            # Check threshold - articles below threshold are skipped
            if score_result["trend_score"] < threshold:
                article.state = ArticleState.SKIPPED.value
                article.fail_reason = f"Trend score {score_result['trend_score']} below threshold"
                article.trend_score = score_result["trend_score"]
                await session.commit()
                logger.info(f"Article {article_id} skipped: trend={score_result['trend_score']}")
                return {"status": "skipped", "trend_score": score_result["trend_score"]}

            # Update article
            article.state = ArticleState.TRENDING.value
            article.trend_score = score_result["trend_score"]
            article.last_step_at = datetime.utcnow()
            await session.commit()

            logger.info(f"Article {article_id} scored: {score_result['trend_score']}")
            return {"status": "trending", "trend_score": score_result["trend_score"]}

    except Exception as e:
        logger.error(f"task_score_trend failed for {article_id}: {e}")
        await update_article_state(article_id, ArticleState.FAILED.value, fail_reason=str(e))
        raise


async def task_research(article_id: str) -> dict:
    """Task: Research article - fetch full content if needed."""
    import os
    worker_id = os.environ.get('HOSTNAME', 'unknown')
    logger.info(f"[{worker_id}] Starting research for article {article_id}")
    
    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one()

            # Get source
            source = None
            if article.source_id:
                from app.models.source import Source
                src_result = await session.execute(
                    select(Source).where(Source.id == article.source_id)
                )
                source = src_result.scalar_one_or_none()

            # Determine article type and fetch content (now returns content, type, images)
            result = await fetch_article_content(
                article, source, use_flaresolverr=source.requires_flaresolverr if source else False
            )
            content = result[0]
            article_type = result[1]
            images = result[2] if len(result) > 2 else []

            # Fallback: use original_image_url from RSS if no images extracted
            if not images and article.original_image_url:
                images = [{"url": article.original_image_url, "alt": "", "credit": ""}]
                logger.info(f"Using original_image_url as fallback for {article_id}")

            # Update article
            article.crawled_content = content
            article.crawled_images = images
            article.article_type = article_type
            article.state = ArticleState.RESEARCHED.value
            article.last_step_at = datetime.utcnow()
            await session.commit()

            logger.info(f"Article {article_id} researched: type={article_type}, content_len={len(content)}, images={len(images)}")
            return {"status": "researched", "article_type": article_type, "images_count": len(images)}

    except Exception as e:
        logger.error(f"task_research failed for {article_id}: {e}")
        await update_article_state(article_id, ArticleState.FAILED.value, fail_reason=str(e))
        raise


async def task_write(article_id: str) -> dict:
    """Task: Write article using AI."""
    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one()

            # Write article
            write_result = await write_article(session, article)

            # Update article
            article.body_html = write_result["body_html"]
            article.meta_title = write_result["meta_title"]
            article.meta_description = write_result["meta_description"]
            article.slug = write_result["slug"]
            article.tags = write_result["tags"]
            article.image_keywords = write_result["image_keywords"]
            article.word_count = write_result["word_count"]
            article.state = ArticleState.WRITTEN.value
            article.last_step_at = datetime.utcnow()
            
            logger.info(f"Article {article_id} tags from AI: {article.tags} (type: {type(article.tags)})")
            await session.commit()

            logger.info(f"Article {article_id} written: {write_result['word_count']} words")
            return {"status": "written", "word_count": write_result["word_count"]}

    except Exception as e:
        logger.error(f"task_write failed for {article_id}: {e}")
        await update_article_state(article_id, ArticleState.FAILED.value, fail_reason=str(e))
        raise


async def task_govern(article_id: str) -> dict:
    """Task: Governance check."""
    import os
    worker_id = os.environ.get('HOSTNAME', 'unknown')
    logger.info(f"[{worker_id}] Starting governance for article {article_id}")
    
    try:
        async with get_db_context() as session:
            governance_enabled = await is_setting_enabled(session, "governance_enabled", True)
            auto_publish = await is_setting_enabled(session, "auto_publish", True)

            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one()

            # Check mode
            is_allin = article.mode == ArticleMode.ALLIN.value

            if not governance_enabled:
                # Skip governance
                article.state = ArticleState.APPROVED.value if auto_publish else ArticleState.GOVERNED.value
                article.governance_result = "skipped"
                await session.commit()
                logger.info(f"Article {article_id} governance skipped (disabled)")
                return {"status": "approved", "governance": "skipped"}

            # Run governance
            gov_result = await govern_article(session, article)

            article.copyright_score = gov_result["copyright_score"]

            if gov_result["passed"]:
                article.governance_result = "pass"

                # Auto-approve in all-in mode or if auto_publish
                if is_allin or auto_publish:
                    article.state = ArticleState.APPROVED.value
                else:
                    article.state = ArticleState.GOVERNED.value

                await session.commit()
                logger.info(f"Article {article_id} governed: passed (auto_approve={is_allin or auto_publish})")
                return {
                    "status": "approved" if (is_allin or auto_publish) else "governed",
                    "governance": "passed",
                }
            else:
                # Check if this is a duplicate rejection
                if gov_result.get("duplicate"):
                    article.state = ArticleState.REJECTED.value
                    article.governance_result = "duplicate"
                    article.governance_reason = gov_result["reason"]
                    await session.commit()
                    logger.warning(f"Article {article_id} rejected: duplicate article detected")
                    return {
                        "status": "rejected",
                        "reason": gov_result["reason"],
                        "duplicate": True,
                        "existing_wp_url": gov_result.get("existing_wp_url"),
                    }

                article.state = ArticleState.REJECTED.value
                article.governance_result = "fail"
                article.governance_reason = gov_result["reason"]
                await session.commit()
                logger.warning(f"Article {article_id} rejected: {gov_result['reason']}")
                return {"status": "rejected", "reason": gov_result["reason"]}

    except Exception as e:
        logger.error(f"task_govern failed for {article_id}: {e}")
        await update_article_state(article_id, ArticleState.FAILED.value, fail_reason=str(e))
        raise


async def task_publish(article_id: str) -> dict:
    """Task: Publish article to WordPress."""
    try:
        from app.publisher.wordpress import publish_article_to_wordpress, get_wordpress_client
        from sqlalchemy.orm import selectinload

        async with get_db_context() as session:
            result = await session.execute(
                select(Article)
                .options(selectinload(Article.source))
                .where(Article.id == article_id)
            )
            article = result.scalar_one()

            # Get source name before passing to async function
            source_name = article.source.name if article.source else None

            # === FIX: Pre-check for duplicates BEFORE expensive processing ===
            # Check 1: Slug exists (original check)
            if article.slug:
                try:
                    client = get_wordpress_client()
                    slug_check = client.check_slug_exists(article.slug)
                    if slug_check and slug_check.get("exists"):
                        existing_url = slug_check.get("post_url")
                        existing_post_id = slug_check.get("post_id")
                        logger.warning(
                            f"Article {article_id} PRE-SKIPPED: duplicate slug detected. "
                            f"Slug: '{article.slug}'. Existing URL: {existing_url}"
                        )
                        article.state = ArticleState.SKIPPED.value
                        article.fail_reason = f"Duplicate slug: {existing_url}"
                        article.wp_url = existing_url
                        article.wp_post_id = existing_post_id
                        article.last_step_at = datetime.utcnow()
                        await session.commit()
                        return {
                            "status": "skipped",
                            "reason": "duplicate_slug_precheck",
                            "existing_wp_url": existing_url,
                            "existing_wp_post_id": existing_post_id,
                        }
                except Exception as slug_check_error:
                    logger.warning(f"Slug pre-check failed: {slug_check_error}, proceeding with publish")

            # Check 2: title_hash exists (NEW - prevents same news in different languages)
            if hasattr(article, 'title_hash') and article.title_hash:
                try:
                    client = get_wordpress_client()
                    meta_check = client.check_duplicate_by_meta("linew_title_hash", article.title_hash)
                    if meta_check and meta_check.get("exists"):
                        existing_url = meta_check.get("post_url")
                        existing_post_id = meta_check.get("post_id")
                        logger.warning(
                            f"Article {article_id} PRE-SKIPPED: duplicate title_hash detected. "
                            f"Same source news already published: {existing_url}"
                        )
                        article.state = ArticleState.SKIPPED.value
                        article.fail_reason = f"Duplicate source: {existing_url}"
                        article.wp_url = existing_url
                        article.wp_post_id = existing_post_id
                        article.last_step_at = datetime.utcnow()
                        await session.commit()
                        return {
                            "status": "skipped",
                            "reason": "duplicate_title_hash_precheck",
                            "existing_wp_url": existing_url,
                            "existing_wp_post_id": existing_post_id,
                        }
                except Exception as meta_check_error:
                    logger.warning(f"title_hash pre-check failed: {meta_check_error}, proceeding with publish")

            # Publish
            logger.info(f"=== PUBLISH START ===")
            logger.info(f"Article {article_id} tags BEFORE publish: {article.tags} (type: {type(article.tags)})")
            logger.info(f"Article {article_id} slug: {article.slug}")
            pub_result = await publish_article_to_wordpress(session, article, source_name=source_name)
            logger.info(f"=== PUBLISH END ===")

            # === FIX: Handle duplicate slug detection ===
            if pub_result.get("duplicate"):
                existing_url = pub_result.get("existing_wp_url")
                logger.warning(
                    f"Article {article_id} SKIPPED: duplicate post detected. "
                    f"Title: '{article.original_title[:60]}'. "
                    f"Existing URL: {existing_url}"
                )
                article.state = ArticleState.SKIPPED.value
                article.fail_reason = f"Duplicate: {existing_url}"
                article.wp_url = existing_url
                article.last_step_at = datetime.utcnow()
                await session.commit()
                return {
                    "status": "skipped",
                    "reason": "duplicate_slug",
                    "existing_wp_url": existing_url,
                }

            # Check if publish failed due to content too short
            if "error" in pub_result and pub_result.get("error") == "content_too_short":
                logger.warning(f"Article {article_id} skipped: content too short ({pub_result.get('word_count', 0)} words)")
                article.state = ArticleState.SKIPPED.value
                article.fail_reason = pub_result.get("reason")
                article.last_step_at = datetime.utcnow()
                await session.commit()
                return {
                    "status": "skipped",
                    "reason": pub_result.get("reason"),
                    "word_count": pub_result.get("word_count", 0),
                    "text_length": pub_result.get("text_length", 0),
                }

            # Update article
            article.wp_post_id = pub_result.get("wp_post_id")
            article.wp_url = pub_result.get("wp_url")
            article.featured_image_wp_id = pub_result.get("featured_image_wp_id")
            article.published_at = pub_result.get("published_at") or datetime.utcnow()
            article.state = ArticleState.PUBLISHED.value
            article.last_step_at = datetime.utcnow()
            await session.commit()

            # Log image info
            content_images_count = pub_result.get("content_images_count", 0)
            featured_id = pub_result.get("featured_image_wp_id")

            # Publish event
            await publish_event(CHANNEL_ARTICLE_EVENTS, {
                "type": "article_published",
                "data": {
                    "id": str(article.id),
                    "wp_url": article.wp_url,
                    "wp_post_id": article.wp_post_id,
                    "featured_image_wp_id": featured_id,
                    "content_images_count": content_images_count,
                },
                "timestamp": datetime.utcnow().isoformat(),
            })

            # === TRIGGER DISTRIBUTION ===
            # After successful publish, distribute to all enabled channels
            try:
                from app.distribution.service import DistributionService
                service = DistributionService()
                dist_results = await service.distribute_article(str(article.id))
                logger.info(f"Distribution triggered for {article_id}: {dist_results}")
            except Exception as dist_error:
                # Log but don't fail the publish task
                logger.error(f"Distribution failed for {article_id}: {dist_error}")

            # === PING SEARCH ENGINES ===
            # Notify Google and Bing about the new article
            try:
                from app.publisher.wordpress import ping_on_article_publish
                await ping_on_article_publish(article.wp_url)
            except Exception as ping_error:
                # Log but don't fail the publish task
                logger.error(f"Search engine ping failed for {article_id}: {ping_error}")

            # === TRIGGER INTERNAL LINKING ===
            # Schedule internal linking update for this article
            try:
                from app.seo.internal_linking import link_new_article_async
                link_new_article_async(str(article.id))
            except Exception as link_error:
                logger.error(f"Internal linking trigger failed for {article_id}: {link_error}")

            logger.info(f"Article {article_id} published: {article.wp_url}, featured={featured_id}, content_images={content_images_count}")
            return {
                "status": "published",
                "wp_url": article.wp_url,
                "featured_image_wp_id": featured_id,
                "content_images_count": content_images_count,
            }

    except Exception as e:
        logger.error(f"task_publish failed for {article_id}: {e}")
        await update_article_state(article_id, ArticleState.FAILED.value, fail_reason=str(e))
        raise


async def run_normal_pipeline(article_id: str, skip_lock_check: bool = False) -> dict:
    """
    Run full normal pipeline.
    
    NOTE: Distributed locking is handled by dispatch_pipeline_task.
    The skip_lock_check parameter is for backward compatibility when called directly.
    """
    worker_id = get_worker_id()
    logger.info(f"[{worker_id}] Starting normal pipeline for {article_id[:8]}...")
    
    # First, get article info including title_hash
    async with get_db_context() as session:
        result = await session.execute(
            select(Article.title_hash, Article.original_title).where(Article.id == article_id)
        )
        row = result.first()
        title_hash = row[0] if row else None
        original_title = row[1][:50] if row and row[1] else "Unknown"
    
    # Check if can process before acquiring lock (only if skip_lock_check is False)
    if not skip_lock_check:
        can_process, reason = check_article_can_process(article_id, title_hash)
        if not can_process:
            logger.info(f"Article {article_id[:8]}... skipped: {reason}")
            return {"status": "skipped", "reason": reason}
    
    # Run pipeline directly (lock already acquired by dispatch_pipeline_task)
    try:
        return await _execute_normal_pipeline(article_id)
    except Exception as e:
        logger.error(f"Normal pipeline error for {article_id[:8]}...: {e}")
        return {"status": "error", "reason": str(e)}


async def _execute_normal_pipeline(article_id: str) -> dict:
    """
    Internal function to execute the actual normal pipeline steps.
    Should only be called after locks are acquired.
    """
    try:
        await task_categorize(article_id)

        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                return {"status": "error", "reason": "Article not found"}
            if article.state == ArticleState.SKIPPED.value:
                return {"status": "skipped", "reason": article.fail_reason}

        await task_score_trend(article_id)

        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if article and article.state == ArticleState.SKIPPED.value:
                return {"status": "skipped", "reason": article.fail_reason}

        await task_research(article_id)
        await task_write(article_id)
        await task_govern(article_id)

        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if article and article.state == ArticleState.APPROVED.value:
                await task_publish(article_id)

        return {"status": "completed"}

    except Exception as e:
        logger.error(f"Normal pipeline failed for {article_id[:8]}...: {e}")
        raise


async def run_allin_pipeline(article_id: str, skip_lock_check: bool = False) -> dict:
    """
    Run all-in pipeline (skip trend scoring, auto-approve governance).
    
    NOTE: Distributed locking is handled by dispatch_pipeline_task.
    The skip_lock_check parameter is for backward compatibility when called directly.
    """
    worker_id = get_worker_id()
    logger.info(f"[{worker_id}] Starting all-in pipeline for {article_id[:8]}...")
    
    # First, get article info including title_hash
    async with get_db_context() as session:
        result = await session.execute(
            select(Article.title_hash, Article.original_title).where(Article.id == article_id)
        )
        row = result.first()
        title_hash = row[0] if row else None
        original_title = row[1][:50] if row and row[1] else "Unknown"
    
    # Check if can process before acquiring lock (only if skip_lock_check is False)
    if not skip_lock_check:
        can_process, reason = check_article_can_process(article_id, title_hash)
        if not can_process:
            logger.info(f"Article {article_id[:8]}... skipped: {reason}")
            return {"status": "skipped", "reason": reason}
    
    # Run pipeline directly (lock already acquired by dispatch_pipeline_task)
    try:
        return await _execute_allin_pipeline(article_id)
    except Exception as e:
        logger.error(f"All-in pipeline error for {article_id[:8]}...: {e}")
        return {"status": "error", "reason": str(e)}


async def _execute_allin_pipeline(article_id: str) -> dict:
    """
    Internal function to execute the actual all-in pipeline steps.
    """
    try:
        await task_categorize(article_id)

        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                return {"status": "error", "reason": "Article not found"}
            if article.state == ArticleState.SKIPPED.value:
                return {"status": "skipped", "reason": article.fail_reason}

        # Skip trend scoring in all-in mode
        async with get_db_context() as session:
            stmt = (
                update(Article)
                .where(Article.id == article_id)
                .values(state=ArticleState.TRENDING.value)
            )
            await session.execute(stmt)
            await session.commit()

        await task_research(article_id)
        await task_write(article_id)
        await task_govern(article_id)

        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if article and article.state == ArticleState.APPROVED.value:
                await task_publish(article_id)

        return {"status": "completed"}

    except Exception as e:
        logger.error(f"All-in pipeline failed for {article_id[:8]}...: {e}")
        raise


async def task_cleanup() -> dict:
    """Cleanup expired signals."""
    try:
        async with get_db_context() as session:
            # Get expiry hours from settings
            result = await session.execute(
                select(Setting).where(Setting.key == "pipeline")
            )
            setting = result.scalar_one_or_none()
            expiry_hours = 24
            if setting:
                expiry_hours = setting.value.get("signal_expiry_hours", 24)

            expired = await expire_old_signals(session, expiry_hours)
            logger.info(f"Cleanup: expired {expired} signals")
            return {"expired": expired}

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise


async def task_cleanup_failed_articles(
    older_than_days: int = 0,
    delete_skipped: bool = True,
    delete_rejected: bool = True,
    delete_failed: bool = True,
) -> dict:
    """
    Cleanup failed/rejected/skipped articles from the pipeline.

    This task removes articles that are stuck in terminal states and can never
    be processed successfully (usually due to persistent errors).

    Args:
        older_than_days: Only delete articles older than this many days (0 = all)
        delete_skipped: Include SKIPPED articles
        delete_rejected: Include REJECTED articles
        delete_failed: Include FAILED articles

    Returns:
        dict with counts of deleted articles by state
    """
    from sqlalchemy import delete, and_
    from app.models.raw_signal import RawSignal

    deleted = {"skipped": 0, "rejected": 0, "failed": 0}

    try:
        async with get_db_context() as session:
            # Calculate cutoff date if needed
            cutoff_date = None
            if older_than_days > 0:
                from datetime import timedelta
                cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

            # Delete SKIPPED articles
            if delete_skipped:
                conditions = [Article.state == ArticleState.SKIPPED.value]
                if cutoff_date:
                    conditions.append(Article.created_at < cutoff_date)

                stmt = delete(Article).where(and_(*conditions))
                result = await session.execute(stmt)
                deleted["skipped"] = result.rowcount
                logger.info(f"Deleted {deleted['skipped']} SKIPPED articles")

            # Delete REJECTED articles
            if delete_rejected:
                conditions = [Article.state == ArticleState.REJECTED.value]
                if cutoff_date:
                    conditions.append(Article.created_at < cutoff_date)

                stmt = delete(Article).where(and_(*conditions))
                result = await session.execute(stmt)
                deleted["rejected"] = result.rowcount
                logger.info(f"Deleted {deleted['rejected']} REJECTED articles")

            # Delete FAILED articles
            if delete_failed:
                conditions = [Article.state == ArticleState.FAILED.value]
                if cutoff_date:
                    conditions.append(Article.created_at < cutoff_date)

                stmt = delete(Article).where(and_(*conditions))
                result = await session.execute(stmt)
                deleted["failed"] = result.rowcount
                logger.info(f"Deleted {deleted['failed']} FAILED articles")

            # Also clean up orphaned RawSignals (signals not linked to any article)
            # These are signals that were never processed into articles
            if older_than_days > 0:
                from datetime import timedelta
                old_date = datetime.utcnow() - timedelta(days=older_than_days)
                stmt = delete(RawSignal).where(RawSignal.created_at < old_date)
                result = await session.execute(stmt)
                orphaned_signals = result.rowcount
                if orphaned_signals > 0:
                    logger.info(f"Deleted {orphaned_signals} orphaned raw signals")
                    deleted["orphaned_signals"] = orphaned_signals

            total = deleted["skipped"] + deleted["rejected"] + deleted["failed"]
            logger.info(f"Cleanup complete: deleted {total} failed articles")

            return {
                "total_deleted": total,
                "by_state": deleted,
                "older_than_days": older_than_days,
            }

    except Exception as e:
        logger.error(f"Cleanup failed articles task failed: {e}")
        raise


async def task_publish_approved_articles(limit: int = 20) -> dict:
    """
    Task: Publish all APPROVED articles that haven't been published yet.
    This fixes the bug where governance sets articles to APPROVED but
    no task was triggering the publish.
    
    FIX: Also check wp_post_id to avoid race condition where state changed
    but wp_url wasn't set yet (could cause duplicate publishing).
    
    FIX: Use get_celery_db_context() instead of get_db_context() to avoid
    "Future attached to a different loop" errors.
    """
    from app.core.database import get_celery_db_context
    
    try:
        async with get_celery_db_context() as session:
            # Find APPROVED articles without wp_url AND wp_post_id
            # This prevents race condition where state changed to APPROVED
            # but publish task hasn't set wp_url yet
            stmt = (
                select(Article)
                .where(Article.state == ArticleState.APPROVED.value)
                .where(Article.wp_url.is_(None))
                .where(Article.wp_post_id.is_(None))  # FIX: Also check wp_post_id
                .limit(limit)
            )
            result = await session.execute(stmt)
            approved_articles = result.scalars().all()

            if not approved_articles:
                logger.debug("No approved articles pending publish")
                return {"published": 0, "skipped": 0, "pending": 0}

            published_count = 0
            skipped_count = 0

            for article in approved_articles:
                try:
                    article_id = str(article.id)
                    logger.info(f"Auto-publishing approved article: {article_id}")

                    source_name = None
                    if article.source_id:
                        from app.models.source import Source
                        src_result = await session.execute(
                            select(Source).where(Source.id == article.source_id)
                        )
                        source = src_result.scalar_one_or_none()
                        source_name = source.name if source else None

                    # Import publish function
                    from app.publisher.wordpress import publish_article_to_wordpress
                    
                    # Publish
                    pub_result = await publish_article_to_wordpress(session, article, source_name=source_name)

                    # Handle duplicate
                    if pub_result.get("duplicate"):
                        article.state = ArticleState.SKIPPED.value
                        article.fail_reason = f"Duplicate: {pub_result.get('existing_wp_url')}"
                        article.wp_url = pub_result.get("existing_wp_url")
                        skipped_count += 1
                    else:
                        article.wp_post_id = pub_result.get("wp_post_id")
                        article.wp_url = pub_result.get("wp_url")
                        article.featured_image_wp_id = pub_result.get("featured_image_wp_id")
                        article.published_at = pub_result.get("published_at") or datetime.utcnow()
                        article.state = ArticleState.PUBLISHED.value
                        published_count += 1

                    article.last_step_at = datetime.utcnow()
                    await session.commit()

                    # Trigger distribution
                    try:
                        from app.distribution.service import DistributionService
                        service = DistributionService()
                        await service.distribute_article(article_id)
                    except Exception as dist_error:
                        logger.error(f"Distribution failed for {article_id}: {dist_error}")

                except Exception as e:
                    logger.error(f"Failed to publish approved article {article.id}: {e}")
                    skipped_count += 1

            logger.info(f"Approved articles task: published={published_count}, skipped={skipped_count}")
            return {"published": published_count, "skipped": skipped_count}

    except Exception as e:
        logger.error(f"task_publish_approved_articles failed: {e}")
        raise
