"""
Scheduler Celery tasks (run periodically).
"""
import asyncio
import logging
from datetime import datetime

from app.worker.celery_app import celery_app, run_async

logger = logging.getLogger(__name__)


@celery_app.task
def task_fetch_all_sources():
    """
    Fetch RSS feeds from all active sources.
    
    This task is CRITICAL for keeping articles flowing into the pipeline.
    If it fails, the pipeline will eventually run out of articles.
    """
    from app.core.database import get_db_context

    async def _fetch():
        try:
            async with get_db_context() as session:
                from app.signals.service import fetch_all_sources
                result = await fetch_all_sources(session)
                logger.info(f"Scheduled fetch completed: {result}")
                return result
        except Exception as e:
            logger.error(f"Scheduled fetch failed: {e}")
            # Retry after 5 minutes
            raise task_fetch_all_sources.retry(exc=e, countdown=300)

    return run_async(_fetch())


@celery_app.task
def task_run_pipeline(mode: str = "normal", limit: int = 20):
    """
    Run the pipeline for pending articles.
    
    This task handles errors gracefully to prevent pipeline from stopping.
    Updated với Hard Stop mechanism.
    """
    from app.core.database import get_db_context
    from app.pipeline.queue_manager import get_next_articles, queue_articles
    from app.pipeline.tasks import run_normal_pipeline, run_allin_pipeline
    from app.pipeline.control import stop_pipeline, get_pipeline_state, PipelineState
    from app.pipeline.hard_stop import should_stop_pipeline_async

    async def _run():
        try:
            async with get_db_context() as session:
                # Get articles to process
                articles = await get_next_articles(session, limit=limit)

                if not articles:
                    logger.info("No articles to process in scheduled pipeline run")
                    return {"processed": 0}

                # Queue articles
                article_ids = [str(a.id) for a in articles]
                await queue_articles(session, article_ids)

                processed = 0
                failed = 0

                # Run pipeline for each article
                for article_id in article_ids:
                    try:
                        # === KIỂM TRA STOP SIGNAL ===
                        # Check hard stop signal
                        if await should_stop_pipeline_async():
                            logger.info("Scheduled pipeline: User stop signal received, halting")
                            break
                        
                        # Check pipeline state
                        state = await get_pipeline_state()
                        if state in [PipelineState.STOPPED, PipelineState.STOPPING]:
                            logger.info("Pipeline stop signal received, halting scheduled run")
                            break

                        if mode == "allin":
                            await run_allin_pipeline(article_id)
                        else:
                            await run_normal_pipeline(article_id)
                        processed += 1
                    except Exception as e:
                        logger.error(f"Pipeline failed for {article_id}: {e}")
                        failed += 1
                        continue

                # Stop pipeline state after batch completes (non-continuous mode)
                if mode != "continuous":
                    try:
                        await stop_pipeline()
                    except Exception as e:
                        logger.warning(f"Failed to stop pipeline state: {e}")

                logger.info(f"Scheduled pipeline run completed: processed={processed}, failed={failed}")
                return {"processed": processed, "failed": failed}

        except Exception as e:
            logger.error(f"Scheduled pipeline run failed: {e}")
            # Retry after 5 minutes
            raise task_run_pipeline.retry(exc=e, countdown=300)

    return run_async(_run())


@celery_app.task
def task_cleanup():
    """Cleanup old signals and data."""
    from app.core.database import get_db_context
    from app.pipeline.tasks import task_cleanup as cleanup_task
    from app.worker.cleanup_tasks import cleanup_old_data

    async def _cleanup():
        async with get_db_context() as session:
            # Run pipeline cleanup
            result1 = await cleanup_task()

            # Run data cleanup
            result2 = await cleanup_old_data(session)

            return {**result1, **result2}

    return run_async(_cleanup())


@celery_app.task
def task_health_check():
    """
    Check system health - Redis and Database connectivity.

    This task logs warnings but does NOT retry on failure.
    Failures are handled by watchdog and heartbeat tasks.
    """
    from app.core.redis import get_redis
    from app.core.database import async_engine

    async def _check():
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "redis": False,
            "database": False,
        }

        # Check Redis
        try:
            redis = await get_redis()
            await redis.ping()
            health["redis"] = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            health["redis_error"] = str(e)

        # Check Database
        try:
            async with async_engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
                health["database"] = True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            health["database_error"] = str(e)

        # Log overall status
        if health["redis"] and health["database"]:
            logger.info(f"Health check OK: Redis={health['redis']}, DB={health['database']}")
        else:
            logger.warning(f"Health check WARNING: Redis={health['redis']}, DB={health['database']}")

        return health

    return run_async(_check())


@celery_app.task
def task_fetch_prices():
    """Fetch latest price data for tracked symbols."""
    from app.prediction.tasks import task_fetch_prices as fetch_task
    return run_async(fetch_task())


@celery_app.task
def task_run_predictions():
    """Run price predictions for tracked symbols."""
    from app.prediction.tasks import task_run_predictions as predict_task
    return run_async(predict_task())


@celery_app.task(bind=True, max_retries=3)
def task_run_continuous_pipeline(self, limit: int = 20, batch_delay_seconds: int = 5):
    """
    Run the pipeline continuously until stopped.

    This task is designed for CONTINUOUS mode:
    - Loops indefinitely until user stops pipeline
    - NEVER calls stop_pipeline() - user must stop manually
    - Checks stop signals between batches
    - Auto-restarts after batch delay

    Use this instead of task_run_pipeline when running in continuous mode.
    """
    from app.core.database import get_db_context
    from app.pipeline.queue_manager import get_next_articles, queue_articles
    from app.pipeline.tasks import run_normal_pipeline, run_allin_pipeline
    from app.pipeline.control import (
        get_pipeline_state,
        PipelineState,
        get_pipeline_info,
    )
    from app.pipeline.hard_stop import should_stop_pipeline_async, get_stop_status

    async def _run_continuous():
        consecutive_empty_batches = 0
        max_empty_batches = 10  # Stop after 10 empty batches to prevent infinite loop

        while True:
            try:
                # === CHECK STOP SIGNALS ===
                stop_status = get_stop_status()
                if stop_status.get("is_stopped"):
                    logger.info(f"Continuous pipeline: User stop signal detected. Reason: {stop_status.get('reason')}")
                    break

                if await should_stop_pipeline_async():
                    logger.info("Continuous pipeline: Hard stop signal received, halting")
                    break

                # Check pipeline state
                state = await get_pipeline_state()
                if state in [PipelineState.STOPPED, PipelineState.STOPPING]:
                    logger.info("Continuous pipeline: Pipeline state is STOPPED, halting")
                    break

                # Check if mode changed away from continuous
                info = await get_pipeline_info()
                if not info.get("is_continuous"):
                    logger.info(f"Continuous pipeline: Mode changed to {info.get('mode')}, halting continuous loop")
                    break

                # === GET ARTICLES ===
                async with get_db_context() as session:
                    articles = await get_next_articles(session, limit=limit)

                    if not articles:
                        consecutive_empty_batches += 1
                        logger.debug(f"Continuous pipeline: No articles (empty batch #{consecutive_empty_batches})")

                        if consecutive_empty_batches >= max_empty_batches:
                            logger.info(f"Continuous pipeline: Stopping after {max_empty_batches} empty batches")
                            break

                        await asyncio.sleep(batch_delay_seconds * 2)
                        continue

                    consecutive_empty_batches = 0

                    # Queue articles
                    article_ids = [str(a.id) for a in articles]
                    await queue_articles(session, article_ids)

                    logger.info(f"Continuous pipeline: Processing batch of {len(article_ids)} articles")

                    # === PROCESS BATCH ===
                    processed = 0
                    failed = 0

                    for article_id in article_ids:
                        # Check stop signals before each article
                        if await should_stop_pipeline_async():
                            logger.info("Continuous pipeline: Stop signal received mid-batch, halting")
                            break

                        state = await get_pipeline_state()
                        if state in [PipelineState.STOPPED, PipelineState.STOPPING]:
                            logger.info("Continuous pipeline: State changed to STOPPED mid-batch")
                            break

                        try:
                            await run_normal_pipeline(article_id)
                            processed += 1
                        except Exception as e:
                            logger.error(f"Continuous pipeline: Failed to process {article_id}: {e}")
                            failed += 1
                            continue

                    logger.info(f"Continuous pipeline: Batch completed - processed={processed}, failed={failed}")

                    # Small delay between batches
                    await asyncio.sleep(batch_delay_seconds)

            except Exception as e:
                logger.error(f"Continuous pipeline: Batch error: {e}")
                await asyncio.sleep(batch_delay_seconds * 3)
                continue

        logger.info("Continuous pipeline: Loop ended")
        return {
            "status": "stopped",
            "reason": "stop_signal_or_empty",
            "consecutive_empty_batches": consecutive_empty_batches,
        }

    return run_async(_run_continuous())


@celery_app.task
def task_refresh_internal_links():
    """
    Refresh internal links for all recent articles.
    
    This task runs daily to update 'See Also' sections across the site.
    Runs at 6 AM UTC (low traffic time).
    """
    async def _refresh():
        try:
            from app.seo.internal_linking import get_linking_engine
            engine = get_linking_engine()
            stats = await engine.refresh_related_posts(limit=100)
            logger.info(f"Internal links refresh completed: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Internal links refresh failed: {e}")
            return {"error": str(e)}

    return run_async(_refresh())


@celery_app.task
def task_index_new_articles():
    """
    Ping search engines about recently published articles.
    
    Runs every 30 minutes to ensure new articles are indexed.
    """
    async def _index():
        try:
            from app.core.database import get_db_context
            from sqlalchemy import select, and_
            from datetime import timedelta
            from app.models.article import Article, ArticleState

            async with get_db_context() as session:
                # Get articles published in last hour without indexing
                recent = datetime.utcnow() - timedelta(hours=1)
                stmt = select(Article).where(
                    and_(
                        Article.state == ArticleState.PUBLISHED.value,
                        Article.published_at >= recent,
                        Article.wp_url.isnot(None)
                    )
                ).limit(20)

                result = await session.execute(stmt)
                articles = result.scalars().all()

                if not articles:
                    logger.debug("No new articles to index")
                    return {"indexed": 0}

                from app.seo.ping_service import ping_on_publish
                indexed = 0

                for article in articles:
                    try:
                        result = await ping_on_publish(article.wp_url)
                        if result.is_success:
                            indexed += 1
                    except Exception as e:
                        logger.warning(f"Failed to index {article.wp_url}: {e}")

                logger.info(f"Indexed {indexed}/{len(articles)} new articles")
                return {"indexed": indexed, "total": len(articles)}

        except Exception as e:
            logger.error(f"Article indexing task failed: {e}")
            return {"error": str(e)}

    return run_async(_index())
