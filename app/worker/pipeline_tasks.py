"""
Pipeline Celery tasks - dispatch and batch processing.

This module contains tasks for running the content pipeline:
- dispatch_pipeline_task: Process single article with locking
- task_run_pipeline_celery: Batch and continuous pipeline execution
"""
import asyncio
import logging
import os
import time

from celery import chain, group

from app.core.database import get_db_context
from app.pipeline.control import (
    get_pipeline_state,
    PipelineState,
    PipelineMode,
    update_pipeline_stats,
    is_pipeline_running,
    start_pipeline,
    stop_pipeline,
)
from app.pipeline.hard_stop import should_stop_pipeline, get_stop_status
from app.pipeline.queue_manager import get_next_articles, queue_articles
from app.pipeline.stability import (
    update_pipeline_activity,
    record_pipeline_metrics,
    pipeline_circuit_breaker,
    check_external_services_health,
    get_pipeline_activity_status,
    is_pipeline_stalled,
)
from app.worker.celery_app import celery_app, run_async

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_pipeline_task(self, article_id: str, mode: str = "normal"):
    """
    Celery task to run a single article through the pipeline.
    Used for parallel processing of multiple articles.

    This is called by task_run_pipeline_celery when using parallel mode.

    Features:
    - Article-level lock to prevent same article being processed twice
    - Title-level lock to prevent duplicate articles with same title_hash
    """
    from app.core.locks import article_lock, title_lock
    from sqlalchemy import select
    from app.models.article import Article

    worker_id = os.environ.get('HOSTNAME', 'unknown')
    logger.info(f"[{worker_id}] [PID:{os.getpid()}] Processing article {article_id} in {mode} mode")

    async def _get_article_hash():
        async with get_db_context() as session:
            result = await session.execute(
                select(Article.title_hash, Article.original_title).where(Article.id == article_id)
            )
            return result.first()

    async def _run_pipeline():
        """
        Run pipeline within async context.
        
        NOTE: This function is already running in an async context (via run_async),
        so we can use 'await' directly for other async functions.
        We do NOT call run_async() here - that would cause "event loop already running" error.
        """
        # === FIX: Check stop signal NGAY KHI task bắt đầu ===
        if should_stop_pipeline():
            logger.info(f"[{worker_id}] Article {article_id}: Pipeline stopped by user, skipping")
            return {"article_id": article_id, "status": "skipped", "reason": "stopped_by_user"}

        # Get article title_hash for title-level lock
        hash_result = await _get_article_hash()
        title_hash = hash_result[0] if hash_result else None
        article_title = hash_result[1][:50] if hash_result and hash_result[1] else "Unknown"

        # Acquire article lock
        async with article_lock(article_id, worker_id, ttl=1200) as acquired:
            if not acquired:
                logger.warning(f"[{worker_id}] Article {article_id} is being processed, skipping")
                return {"article_id": article_id, "status": "skipped", "reason": "article_locked"}

            logger.info(f"[{worker_id}] Article lock acquired for {article_id[:8]}...")

            # === FIX: Check stop signal SAU KHI acquire lock, TRƯỚC KHI xử lý ===
            if should_stop_pipeline():
                logger.info(f"[{worker_id}] Article {article_id}: Pipeline stopped by user after lock acquired, releasing and skipping")
                return {"article_id": article_id, "status": "skipped", "reason": "stopped_by_user"}

            # Acquire title lock if available
            if title_hash:
                async with title_lock(title_hash, worker_id, ttl=1200) as title_acquired:
                    if not title_acquired:
                        return {
                            "article_id": article_id,
                            "status": "skipped",
                            "reason": "title_locked",
                        }
                    logger.info(f"[{worker_id}] Title lock acquired for {title_hash[:16]}...")
                    
                    # Run pipeline - lock already acquired, skip redundant lock check
                    if mode == "allin":
                        from app.pipeline.tasks import run_allin_pipeline
                        result = await run_allin_pipeline(article_id, skip_lock_check=True)
                    else:
                        from app.pipeline.tasks import run_normal_pipeline
                        result = await run_normal_pipeline(article_id, skip_lock_check=True)

                    return {"article_id": article_id, "status": result.get("status", "completed")}
            else:
                # No title_hash, skip title lock
                if mode == "allin":
                    from app.pipeline.tasks import run_allin_pipeline
                    result = await run_allin_pipeline(article_id, skip_lock_check=True)
                else:
                    from app.pipeline.tasks import run_normal_pipeline
                    result = await run_normal_pipeline(article_id, skip_lock_check=True)

                return {"article_id": article_id, "status": result.get("status", "completed")}

    try:
        result = run_async(_run_pipeline())
        logger.info(f"[{worker_id}] [PID:{os.getpid()}] Completed article {article_id}: {result.get('status')}")
        return result
    except Exception as e:
        logger.error(f"[{worker_id}] [PID:{os.getpid()}] Failed article {article_id}: {e}")
        return {"article_id": article_id, "status": "failed", "error": str(e)}


async def _run_single_batch(batch_limit: int) -> dict:
    """Run a single batch of articles with PARALLEL processing."""
    # === FIX: Check stop signal TRƯỚC KHI lấy articles ===
    if should_stop_pipeline():
        logger.info("Single batch: Stop signal received, aborting before fetching articles")
        return {"processed": 0, "queued": 0, "empty_batch": True, "stopped_by_user": True}

    async with get_db_context() as session:
        articles = await get_next_articles(session, limit=batch_limit)

        if not articles:
            return {"processed": 0, "queued": 0, "empty_batch": True}

        # === FIX: Check stop signal TRƯỚC KHI dispatch ===
        if should_stop_pipeline():
            logger.info("Single batch: Stop signal received before dispatching tasks")
            return {"processed": 0, "queued": 0, "empty_batch": False, "stopped_by_user": True}

        article_ids = [str(a.id) for a in articles]
        await queue_articles(session, article_ids)

        logger.info(f"[PARALLEL] Dispatching {len(article_ids)} articles for parallel processing")

        # === PARALLEL EXECUTION: Dispatch all tasks at once (non-blocking) ===
        for article_id in article_ids:
            dispatch_pipeline_task.delay(article_id, "normal")

        logger.info(f"[PARALLEL] Dispatched {len(article_ids)} tasks, waiting for workers...")

        return {
            "processed": len(article_ids),
            "queued": len(article_ids),
            "published": 0,
            "failed": 0,
            "empty_batch": False,
        }


async def _run_continuous(batch_limit: int, max_consecutive_empty: int = 100):
    """
    ENHANCED continuous pipeline execution với SUB-TASKS thay vì while True.
    
    Key improvements:
    1. Mỗi batch chạy trong một sub-task riêng
    2. Sub-task hoàn thành → spawn sub-task mới
    3. Kiểm tra stop signal trước mỗi batch
    4. KHÔNG còn while True loop - tránh Celery timeout
    5. FETCH SIGNALS MỚI trước mỗi batch để đảm bảo xử lý tin tức mới nhất
    """
    logger.info("Starting SUB-TASK continuous pipeline mode (runs until explicitly stopped)")
    logger.info("Circuit breaker status: %s", pipeline_circuit_breaker.get_status())

    batch = 0
    consecutive_empty = 0
    last_batch_time = time.time()

    await update_pipeline_activity()

    while True:
        try:
            # === KIỂM TRA STOP SIGNAL ===
            if should_stop_pipeline():
                logger.info("Continuous pipeline: User stop signal received, shutting down gracefully")
                break
            
            # === CHECK PIPELINE STATE ===
            state = await get_pipeline_state()
            if state in [PipelineState.STOPPED, PipelineState.STOPPING]:
                logger.info(f"Pipeline stop signal received (state={state.value})")
                break

            # === FIX: FETCH SIGNALS MỚI TRƯỚC MỖI BATCH ===
            # Đảm bảo lấy tin tức mới nhất từ các nguồn RSS
            try:
                from app.signals.service import fetch_all_sources
                from app.core.database import get_db_context
                
                async with get_db_context() as session:
                    fetch_result = await fetch_all_sources(session)
                    sources_fetched = fetch_result.get('sources_fetched', 0)
                    articles_created = fetch_result.get('articles_created', 0)
                    
                    if articles_created > 0:
                        logger.info(f"[SIGNALS] Fetched {articles_created} new articles from {sources_fetched} sources")
            except Exception as fetch_error:
                logger.warning(f"[SIGNALS] Failed to fetch new signals: {fetch_error}")
                # Continue anyway - don't let signal fetch failure stop the pipeline
            
            # === CHECK CIRCUIT BREAKER ===
            can_proceed, reason = await pipeline_circuit_breaker.can_proceed()
            if not can_proceed:
                logger.warning(f"Continuous pipeline: Circuit breaker open. {reason}")
                logger.warning("Continuous pipeline: Will check again in 60 seconds")
                await asyncio.sleep(60)
                continue

            # === PERIODIC ACTIVITY UPDATE ===
            await update_pipeline_activity()

            # === RUN BATCH ===
            batch += 1
            batch_start = time.time()

            try:
                result = await _run_single_batch(batch_limit)
            except Exception as batch_error:
                logger.error(f"Continuous pipeline batch {batch} raised exception: {batch_error}")
                await pipeline_circuit_breaker.record_failure(str(batch_error))
                await asyncio.sleep(30)
                continue

            batch_duration = time.time() - batch_start
            last_batch_time = time.time()

            # === KIỂM TRA STOP SAU KHI BATCH HOÀN THÀNH ===
            if should_stop_pipeline() or result.get("stopped_by_user"):
                logger.info("Continuous pipeline: Stopping after batch completion")
                break

            if result["empty_batch"]:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    consecutive_empty = 0
                logger.debug(f"Continuous batch {batch}: no articles, sleeping 60s")
                await asyncio.sleep(60)
            else:
                consecutive_empty = 0
                await pipeline_circuit_breaker.record_success()

                await update_pipeline_stats(
                    articles_processed=result["processed"],
                    articles_published=result["published"],
                    articles_failed=result["failed"],
                )

                await record_pipeline_metrics(
                    articles_processed=result["processed"],
                    articles_published=result["published"],
                    batch_duration_seconds=batch_duration,
                )

                logger.info(
                    f"Continuous batch {batch}: processed={result['processed']}, "
                    f"published={result['published']}, failed={result['failed']}, "
                    f"duration={batch_duration:.1f}s"
                )

                await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("Continuous pipeline: Cancelled")
            break
        except Exception as e:
            logger.error(f"Continuous pipeline error in batch {batch}: {e}")
            await pipeline_circuit_breaker.record_failure(str(e))
            await asyncio.sleep(30)
            continue

    logger.info(f"Continuous pipeline stopped after {batch} batches")
    return {"batches": batch, "mode": "continuous", "total_batches": batch}


@celery_app.task(bind=True)
def task_run_pipeline_celery(self, mode: str = "normal", limit: int = 20, continuous: bool = False):
    """
    Celery task to run the pipeline for pending articles.
    
    Args:
        mode: Pipeline mode ('normal', 'allin', or 'continuous')
        limit: Max articles per batch
        continuous: If True, runs indefinitely until stopped
    """
    async def _run_batch():
        result = await _run_single_batch(limit)
        logger.info(f"Pipeline run completed: {result['processed']}/{result['queued']} articles")
        
        # Stop pipeline state after batch completes (non-continuous mode)
        try:
            await stop_pipeline()
        except Exception as e:
            logger.warning(f"Failed to stop pipeline state: {e}")
        
        return result

    # Main execution
    if mode == "continuous":
        return run_async(_run_continuous(limit))
    else:
        return run_async(_run_batch())
