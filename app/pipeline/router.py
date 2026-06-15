"""
Pipeline API routes.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.article import Article, ArticleState
from app.models.setting import Setting
from app.pipeline.queue_manager import get_queue_stats, queue_articles
from app.pipeline.analyzer import categorize_article, score_article_trend
from app.pipeline.governor import govern_article
from app.pipeline.tasks import task_cleanup_failed_articles
from app.worker.worker_config import (
    WORKER_TIER_CONFIG,
    get_current_tier_from_db,
    update_worker_config_cache,
    invalidate_worker_config_cache,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class PipelineRunRequest(BaseModel):
    category: Optional[str] = None
    limit: int = 20
    mode: str = "normal"


class PipelineStatus(BaseModel):
    is_running: bool
    mode: str
    in_progress: int
    queue_size: int
    last_run_at: Optional[str]
    queue_by_state: dict
    running: int
    failed_articles: list


@router.post("/run")
async def run_pipeline(
    data: PipelineRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the pipeline (normal mode) - dispatches to Celery worker.
    
    Returns 200 with status even if no articles found.
    Returns 500 only on critical errors.
    """
    from app.pipeline.queue_manager import get_next_articles
    from app.worker.pipeline_tasks import task_run_pipeline_celery

    try:
        articles = await get_next_articles(
            db,
            limit=data.limit,
            category=data.category,
            mode="normal",
        )

        if not articles:
            return {"message": "No articles to process", "articles_queued": 0, "success": True}

        # Queue articles
        article_ids = [str(a.id) for a in articles]
        await queue_articles(db, article_ids)

        # Dispatch to Celery worker for processing
        try:
            task_run_pipeline_celery.delay(mode="normal", limit=data.limit)
            celery_dispatched = True
        except Exception as celery_error:
            logger.error(f"Failed to dispatch Celery task: {celery_error}")
            celery_dispatched = False

        return {
            "message": f"Pipeline dispatched for {len(articles)} articles",
            "articles_queued": len(articles),
            "article_ids": article_ids,
            "celery_dispatched": celery_dispatched,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}")
        return {"message": f"Pipeline run error: {str(e)}", "articles_queued": 0, "success": False}


@router.post("/allin")
async def run_pipeline_allin(
    data: PipelineRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the all-in pipeline (skip trend scoring, auto-approve) - dispatches to Celery worker.
    
    Returns 200 with status even if no articles found.
    Returns 500 only on critical errors.
    """
    from app.pipeline.queue_manager import get_next_articles
    from app.worker.pipeline_tasks import task_run_pipeline_celery

    try:
        articles = await get_next_articles(
            db,
            limit=data.limit,
            category=data.category,
            mode="allin",
        )

        if not articles:
            # Also check normal mode articles
            articles = await get_next_articles(db, limit=data.limit, category=data.category)
            for article in articles:
                article.mode = "allin"

        if not articles:
            return {"message": "No articles to process", "articles_queued": 0, "success": True}

        # Queue articles
        article_ids = [str(a.id) for a in articles]
        await queue_articles(db, article_ids)

        # Dispatch to Celery worker for processing
        try:
            task_run_pipeline_celery.delay(mode="allin", limit=data.limit)
            celery_dispatched = True
        except Exception as celery_error:
            logger.error(f"Failed to dispatch Celery task: {celery_error}")
            celery_dispatched = False

        return {
            "message": f"All-in pipeline dispatched for {len(articles)} articles",
            "articles_queued": len(articles),
            "article_ids": article_ids,
            "celery_dispatched": celery_dispatched,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Pipeline allin failed: {e}")
        return {"message": f"Pipeline allin error: {str(e)}", "articles_queued": 0, "success": False}


@router.get("/status", response_model=PipelineStatus)
async def get_pipeline_status(db: AsyncSession = Depends(get_db)):
    """Get pipeline status and queue stats - optimized with parallel queries."""
    # Run queue stats and other queries in parallel
    import asyncio

    # Get queue stats
    stats = await get_queue_stats(db)

    # Get last run time and failed articles in parallel
    last_run_stmt = (
        select(Article.last_step_at)
        .where(Article.last_step_at.isnot(None))
        .order_by(Article.last_step_at.desc())
        .limit(1)
    )

    failed_stmt = (
        select(
            Article.id,
            Article.original_title,
            Article.state,
            Article.fail_reason,
            Article.retry_count,
        )
        .where(Article.state == ArticleState.FAILED.value)
        .order_by(Article.updated_at.desc())
        .limit(10)
    )

    # Execute both queries in parallel
    last_run_result, failed_result = await asyncio.gather(
        db.execute(last_run_stmt),
        db.execute(failed_stmt),
    )

    last_run = last_run_result.scalar_one_or_none()

    failed_articles = [
        {
            "id": str(row.id),
            "original_title": row.original_title,
            "state": row.state,
            "last_error": row.fail_reason,
            "retry_count": row.retry_count,
        }
        for row in failed_result.all()
    ]

    # Get mode from Redis for accurate status
    mode = "normal"  # Default fallback
    redis_state = "stopped"  # Default
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        redis_mode = await redis.get("linew:pipeline:mode")
        redis_state = await redis.get("linew:pipeline:state")
        if redis_mode:
            mode = redis_mode
    except Exception:
        pass

    # Check if pipeline is running based on Redis state OR in_progress count
    # Consider "running" and "stopping" as running states
    is_running = redis_state in ("running", "stopping") or (stats.get("in_progress", 0) > 0)

    return PipelineStatus(
        is_running=is_running,
        mode=mode,
        in_progress=stats.get("in_progress", 0),
        queue_size=stats.get("queued", 0),
        last_run_at=last_run.isoformat() if last_run else None,
        queue_by_state=stats.get("by_state", {}),
        running=stats.get("in_progress", 0),
        failed_articles=failed_articles,
    )


@router.post("/retry/{article_id}")
async def retry_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed article - dispatches to Celery worker."""
    from app.worker.pipeline_tasks import task_run_pipeline_celery

    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.state != ArticleState.FAILED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Article is in state {article.state}, not FAILED",
        )

    # Reset article
    article.state = ArticleState.SIGNAL_COLLECTED.value
    article.retry_count = article.retry_count + 1
    article.fail_reason = None
    await db.commit()

    # Dispatch to Celery worker
    task_run_pipeline_celery.delay(mode="normal", limit=1)

    return {
        "message": f"Retry scheduled for article {article_id}",
        "retry_count": article.retry_count,
    }


@router.post("/categorize/{article_id}")
async def categorize_single(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Categorize a single article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    cat_result = await categorize_article(db, article)

    article.category = cat_result["category"]
    article.category_confidence = cat_result["confidence"]
    article.state = ArticleState.CATEGORIZED.value
    await db.commit()

    return {
        "id": str(article.id),
        "category": cat_result["category"],
        "confidence": cat_result["confidence"],
    }


@router.post("/score/{article_id}")
async def score_single(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Score trend for a single article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    score_result = await score_article_trend(db, article)

    article.trend_score = score_result["trend_score"]
    article.state = ArticleState.TRENDING.value
    await db.commit()

    return {
        "id": str(article.id),
        "trend_score": score_result["trend_score"],
    }


@router.post("/govern/{article_id}")
async def govern_single(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Run governance check on a single article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    gov_result = await govern_article(db, article)

    article.governance_result = gov_result["result"]
    article.governance_reason = gov_result["reason"]
    article.copyright_score = gov_result["copyright_score"]

    if gov_result["passed"]:
        article.state = ArticleState.GOVERNED.value
    else:
        article.state = ArticleState.REJECTED.value

    await db.commit()

    return {
        "id": str(article.id),
        "governance_result": gov_result["result"],
        "reason": gov_result["reason"],
    }


@router.post("/cleanup")
async def run_cleanup(db: AsyncSession = Depends(get_db)):
    """Manually trigger cleanup of expired signals."""
    result = await task_cleanup()
    return {"message": "Cleanup completed", **result}


@router.post("/cleanup/failed")
async def cleanup_failed_articles(
    older_than_days: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Cleanup failed/rejected/skipped articles from the pipeline.

    This removes articles that are stuck in terminal states:
    - FAILED: Articles that encountered persistent errors
    - REJECTED: Articles rejected by governance
    - SKIPPED: Articles skipped due to duplicates or other reasons

    Args:
        older_than_days: Only delete articles older than this many days.
                       Use 0 to delete ALL failed articles (default).
                       Use 7 to only delete articles older than 1 week.

    Returns:
        dict with counts of deleted articles by state
    """
    result = await task_cleanup_failed_articles(
        older_than_days=older_than_days,
        delete_skipped=True,
        delete_rejected=True,
        delete_failed=True,
    )
    return {
        "message": f"Deleted {result['total_deleted']} failed articles",
        **result,
    }


# =============================================================================
# Pipeline Control Endpoints (Start/Stop/Continuous)
# =============================================================================

class PipelineControlRequest(BaseModel):
    mode: str = "normal"
    limit: int = 10


class PipelineControlResponse(BaseModel):
    success: bool
    message: str
    state: str
    mode: Optional[str] = None


class PipelineInfoResponse(BaseModel):
    state: str
    mode: str
    started_at: Optional[str]
    has_lock: bool
    is_running: bool
    is_continuous: bool
    stats: dict


@router.post("/start")
async def start_pipeline(
    data: PipelineControlRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """
    Start the pipeline in specified mode.
    
    Modes:
    - normal: Process a single batch of articles
    - allin: Process articles without trend scoring
    - continuous: Run continuously until stopped
    
    Returns 200 with status even if pipeline is already running or encounters minor errors.
    Returns 500 only on critical errors.
    """
    from app.pipeline.control import (
        start_pipeline as control_start,
        PipelineMode,
        is_pipeline_running,
    )
    from app.worker.pipeline_tasks import task_run_pipeline_celery
    
    try:
        # Check if already running
        try:
            is_running = await is_pipeline_running()
        except Exception as redis_error:
            logger.warning(f"Failed to check pipeline running status: {redis_error}")
            is_running = False
        
        if is_running:
            return PipelineControlResponse(
                success=False,
                message="Pipeline is already running",
                state="running",
            )
        
        # Map mode string to PipelineMode
        mode_map = {
            "normal": PipelineMode.NORMAL,
            "allin": PipelineMode.ALLIN,
            "continuous": PipelineMode.CONTINUOUS,
        }
        pipeline_mode = mode_map.get(data.mode, PipelineMode.NORMAL)
        
        # Start pipeline control
        try:
            result = await control_start(mode=pipeline_mode)
        except Exception as control_error:
            logger.error(f"Failed to start pipeline control: {control_error}")
            return PipelineControlResponse(
                success=False,
                message=f"Failed to start pipeline: {str(control_error)}",
                state="error",
                mode=data.mode,
            )
        
        celery_dispatched = False
        if result.get("success"):
            # Dispatch to Celery worker
            try:
                task_run_pipeline_celery.delay(
                    mode=data.mode,
                    limit=data.limit,
                    continuous=(data.mode == "continuous"),
                )
                celery_dispatched = True
            except Exception as celery_error:
                logger.error(f"Failed to dispatch Celery task: {celery_error}")
                # Pipeline state is set, but task dispatch failed
                # This is not critical - worker might pick up from DB
        
        return PipelineControlResponse(
            success=result.get("success", False),
            message=result.get("message", "Unknown error"),
            state=result.get("state", "unknown"),
            mode=data.mode,
        )
    except Exception as e:
        logger.error(f"Start pipeline critical error: {e}")
        return PipelineControlResponse(
            success=False,
            message=f"Critical error starting pipeline: {str(e)}",
            state="error",
            mode=data.mode,
        )


@router.post("/stop")
async def stop_pipeline(_auth: str = Depends(require_auth)):
    """
    Stop the running pipeline.

    Uses HARD STOP mechanism:
    - Sets Redis stop signal (immediate effect)
    - Revokes running Celery tasks
    - Clears is_continuous flag to prevent auto-restart
    - Pipeline stops after current article

    For continuous mode, this sends a stop signal that will be picked up
    on the next iteration. For batch mode, this cancels pending tasks.
    
    Returns 200 with status even if pipeline is already stopped.
    Returns 500 only on critical errors.
    """
    from app.pipeline.control import (
        stop_pipeline as control_stop,
        get_pipeline_state,
        PipelineState,
    )
    from app.pipeline.hard_stop import trigger_user_stop
    from app.worker.celery_app import celery_app

    try:
        # Get current state safely
        try:
            current_state = await get_pipeline_state()
        except Exception as state_error:
            logger.warning(f"Failed to get pipeline state: {state_error}")
            current_state = PipelineState.STOPPED

        if current_state == PipelineState.STOPPED:
            return PipelineControlResponse(
                success=True,
                message="Pipeline is already stopped",
                state="stopped",
            )

        # === TRIGGER HARD STOP FIRST ===
        try:
            stop_result = trigger_user_stop(reason="User requested stop from API")
            if not stop_result.get("success"):
                logger.warning(f"Failed to trigger hard stop: {stop_result}")
        except Exception as hard_stop_error:
            logger.warning(f"Hard stop error (non-critical): {hard_stop_error}")

        # === FIX: Xóa is_continuous flag để watchdog không auto-restart ===
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            await redis.delete("linew:pipeline:mode")
            logger.info("Cleared pipeline mode (is_continuous) flag")
        except Exception as e:
            logger.warning(f"Failed to clear pipeline mode: {e}")

        # Revoke any running pipeline tasks
        try:
            # Get active tasks and revoke them
            inspector = celery_app.control.inspect()
            active_tasks = inspector.active()
            if active_tasks:
                for worker, tasks in active_tasks.items():
                    for task in tasks:
                        if "pipeline" in task.get("name", ""):
                            celery_app.control.revoke(task.get("id", ""), terminate=True)
                            logger.info(f"Revoked task {task.get('id')} on {worker}")
        except Exception as e:
            logger.warning(f"Failed to revoke tasks (non-critical): {e}")

        # Stop pipeline control
        try:
            result = await control_stop(reason="User requested stop from API")
        except Exception as control_error:
            logger.error(f"Failed to stop pipeline control: {control_error}")
            result = {"success": False, "state": "error", "message": str(control_error)}

        return PipelineControlResponse(
            success=result.get("success", False),
            message=result.get("message", "Pipeline stopped"),
            state=result.get("state", "stopped"),
        )
    except Exception as e:
        logger.error(f"Stop pipeline critical error: {e}")
        return PipelineControlResponse(
            success=False,
            message=f"Critical error stopping pipeline: {str(e)}",
            state="error",
        )


@router.get("/info")
async def get_pipeline_info():
    """
    Get detailed pipeline information including state, mode, and statistics.
    """
    from app.pipeline.control import get_pipeline_info as control_get_info
    
    info = await control_get_info()
    return PipelineInfoResponse(**info)


@router.post("/continuous/start")
async def start_continuous_pipeline(
    data: PipelineControlRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """
    Start pipeline in continuous mode.
    Pipeline will run indefinitely until stopped.
    
    Returns 200 with status even if pipeline is already running.
    Returns 500 only on critical errors.
    """
    from app.pipeline.control import (
        start_pipeline as control_start,
        PipelineMode,
        is_pipeline_running,
    )
    from app.worker.pipeline_tasks import task_run_pipeline_celery
    
    try:
        is_running = await is_pipeline_running()
    except Exception as redis_error:
        logger.warning(f"Failed to check pipeline running status: {redis_error}")
        is_running = False
    
    if is_running:
        return PipelineControlResponse(
            success=False,
            message="Pipeline is already running",
            state="running",
        )
    
    try:
        result = await control_start(mode=PipelineMode.CONTINUOUS)
    except Exception as control_error:
        logger.error(f"Failed to start continuous pipeline: {control_error}")
        return PipelineControlResponse(
            success=False,
            message=f"Failed to start pipeline: {str(control_error)}",
            state="error",
            mode="continuous",
        )
    
    celery_dispatched = False
    if result.get("success"):
        try:
            task_run_pipeline_celery.delay(
                mode="continuous",
                limit=data.limit,
                continuous=True,
            )
            celery_dispatched = True
        except Exception as celery_error:
            logger.error(f"Failed to dispatch continuous pipeline task: {celery_error}")
    
    return PipelineControlResponse(
        success=result.get("success", False),
        message=result.get("message", "Continuous pipeline started"),
        state=result.get("state", "unknown"),
        mode="continuous",
    )


@router.post("/continuous/stop")
async def stop_continuous_pipeline(_auth: str = Depends(require_auth)):
    """
    Stop continuous pipeline mode.

    Uses HARD STOP mechanism - pipeline stops immediately after current article.
    Also clears is_continuous flag to prevent watchdog auto-restart.
    
    Returns 200 with status even if pipeline is not running.
    Returns 500 only on critical errors.
    """
    from app.pipeline.control import (
        set_pipeline_state,
        get_pipeline_state,
        PipelineState,
        PipelineMode,
    )
    from app.pipeline.hard_stop import trigger_user_stop

    try:
        current_state = await get_pipeline_state()
    except Exception as state_error:
        logger.warning(f"Failed to get pipeline state: {state_error}")
        current_state = PipelineState.STOPPED

    if current_state != PipelineState.RUNNING:
        return PipelineControlResponse(
            success=False,
            message=f"Cannot stop - pipeline is {current_state.value}",
            state=current_state.value,
        )

    # === TRIGGER HARD STOP ===
    try:
        stop_result = trigger_user_stop(reason="User requested continuous stop from API")
        if not stop_result.get("success"):
            logger.warning(f"Failed to trigger hard stop: {stop_result}")
    except Exception as hard_stop_error:
        logger.warning(f"Hard stop error (non-critical): {hard_stop_error}")

    # === FIX: Xóa is_continuous flag để watchdog không auto-restart ===
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.delete("linew:pipeline:mode")
        logger.info("Continuous stop: Cleared pipeline mode flag")
    except Exception as redis_error:
        logger.warning(f"Failed to clear pipeline mode: {redis_error}")

    try:
        await set_pipeline_state(PipelineState.STOPPED, PipelineMode.CONTINUOUS)
    except Exception as state_error:
        logger.warning(f"Failed to set pipeline state: {state_error}")

    return PipelineControlResponse(
        success=True,
        message="Stop signal sent. Pipeline will stop after current article.",
        state="stopping",
        mode="continuous",
    )


@router.get("/continuous/status")
async def get_continuous_status():
    """
    Get continuous mode status.
    """
    from app.pipeline.control import get_pipeline_info as control_get_info

    info = await control_get_info()
    return {
        "is_running": info.get("is_running", False),
        "is_continuous": info.get("is_continuous", False),
        "state": info.get("state", "unknown"),
        "mode": info.get("mode", "unknown"),
        "started_at": info.get("started_at"),
        "stats": info.get("stats", {}),
    }


@router.get("/ai-status")
async def get_ai_status():
    """
    Get AI Gateway availability status.

    Returns whether AI is currently available or experiencing issues.
    Pipeline will keep running even if AI is unavailable (graceful degradation).
    """
    from app.pipeline.stability import check_ai_availability
    from app.core.ai_gateway import circuit_breaker

    ai_status = await check_ai_availability()
    cb_status = circuit_breaker.get_status()

    return {
        "ai_available": ai_status.get("is_available", True),
        "ai_status": ai_status.get("status", "unknown"),
        "unavailable_since": ai_status.get("unavailable_since"),
        "unavailable_duration_seconds": ai_status.get("unavailable_duration_seconds"),
        "consecutive_failures": ai_status.get("consecutive_failures", 0),
        "circuit_breaker": cb_status,
        "note": "Pipeline keeps running even when AI is unavailable - graceful degradation",
    }


@router.get("/health")
async def get_pipeline_health():
    """
    Get comprehensive pipeline health status.
    
    Returns 200 with health status even if some services are unavailable.
    This endpoint is designed to be resilient - it will return health info
    even if Redis or other services have issues.
    """
    from app.pipeline.control import get_pipeline_info as control_get_info
    from app.pipeline.stability import check_ai_availability, get_pipeline_metrics
    from app.pipeline.hard_stop import get_stop_status_async
    from app.core.redis import check_redis_health

    health_issues = []
    
    # Check Redis
    redis_health = await check_redis_health()
    
    # Check Pipeline Info
    try:
        pipeline_info = await control_get_info()
    except Exception as pipeline_error:
        pipeline_info = {
            "state": "error",
            "mode": "unknown",
            "is_running": False,
            "is_continuous": False,
            "started_at": None,
            "stats": {},
            "error": str(pipeline_error),
        }
        health_issues.append(f"Pipeline info error: {str(pipeline_error)[:100]}")
    
    # Check AI Status
    try:
        ai_status = await check_ai_availability()
    except Exception as ai_error:
        ai_status = {
            "is_available": True,  # Assume available on error
            "status": "error",
            "error": str(ai_error),
        }
        health_issues.append(f"AI status check error: {str(ai_error)[:100]}")
    
    # Check Metrics
    try:
        metrics = await get_pipeline_metrics()
    except Exception as metrics_error:
        metrics = {}
        health_issues.append(f"Metrics error: {str(metrics_error)[:100]}")
    
    # Check Stop Status
    try:
        stop_status = await get_stop_status_async()
    except Exception as stop_error:
        stop_status = {
            "is_stopped": False,
            "reason": None,
            "timestamp": None,
            "error": str(stop_error),
        }
        health_issues.append(f"Stop status error: {str(stop_error)[:100]}")
    
    # Overall health assessment
    is_healthy = (
        redis_health.get("healthy", False) and
        pipeline_info.get("state") != "error" and
        ai_status.get("is_available", True) and
        not stop_status.get("is_stopped", False)
    )
    
    return {
        "healthy": is_healthy,
        "issues": health_issues,
        "redis": redis_health,
        "pipeline": {
            "state": pipeline_info.get("state", "unknown"),
            "mode": pipeline_info.get("mode", "unknown"),
            "is_running": pipeline_info.get("is_running", False),
            "is_continuous": pipeline_info.get("is_continuous", False),
            "started_at": pipeline_info.get("started_at"),
            "stats": pipeline_info.get("stats", {}),
        },
        "ai": {
            "available": ai_status.get("is_available", True),
            "status": ai_status.get("status", "unknown"),
            "unavailable_since": ai_status.get("unavailable_since"),
        },
        "metrics": metrics,
        "stop": {
            "is_stopped": stop_status.get("is_stopped", False),
            "reason": stop_status.get("reason"),
            "timestamp": stop_status.get("timestamp"),
        },
    }


@router.post("/publish-approved")
async def publish_approved_articles(limit: int = 20):
    """
    Publish all APPROVED articles that haven't been published yet.
    This fixes the bug where governance sets articles to APPROVED but
    no task was triggering the publish.

    Use this endpoint to clean up any stuck APPROVED articles.
    """
    from app.worker.celery_app import task_publish_approved_celery

    # Dispatch to Celery worker
    result = task_publish_approved_celery.delay(limit=limit)

    return {
        "message": f"Publish approved articles task dispatched",
        "task_id": result.id,
        "limit": limit,
    }


class WorkerTierRequest(BaseModel):
    tier: str = Field(..., description="Worker tier (standard, 1, 2, 3, or 4)")


class WorkerTierResponse(BaseModel):
    tier: str
    workers: int
    rate_limits: dict
    estimated_throughput: int
    message: str


@router.post("/config/worker-tier", response_model=WorkerTierResponse)
async def set_worker_tier(
    data: WorkerTierRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Set worker tier to adjust pipeline throughput.

    Tiers:
    - standard: 6 workers (1 per metric), ~20 articles/hour
    - 1 (Testing): 15 workers, ~200 articles/hour
    - 2 (Light): 30 workers, ~600 articles/hour
    - 3 (Normal): 45 workers, ~1,200 articles/hour ← DEFAULT
    - 4 (High): 60 workers, ~3,000 articles/hour

    ⚠️ IMPORTANT: Requires Docker restart to apply changes!
    """
    tier = data.tier
    config = WORKER_TIER_CONFIG[tier]
    
    # Check if setting exists
    result = await db.execute(
        select(Setting).where(Setting.key == "pipeline")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        # Get current value and merge with tier config
        current_value = dict(setting.value) if setting.value else {}
        current_value["worker_tier"] = tier
        current_value["worker_threads"] = config["workers"]
        
        # Use ORM to update - proper JSONB handling
        setting.value = current_value
        setting.updated_at = datetime.utcnow()
    else:
        # Create new setting with tier config
        new_value = {
            "worker_tier": tier,
            "worker_threads": config["workers"],
            "auto_publish": True,
            "trend_scoring_enabled": True,
            "governance_enabled": True,
            "default_mode": "normal",
        }
        new_setting = Setting(key="pipeline", value=new_value)
        db.add(new_setting)
    
    await db.commit()
    
    # Invalidate Redis cache so workers can pick up new config
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.publish("linew:worker:tier:changed", json.dumps({"tier": tier, "workers": config["workers"]}))
        logger.info(f"Published tier change event to Redis: tier={tier}, workers={config['workers']}")
    except Exception as e:
        logger.warning(f"Failed to publish tier change event: {e}")
    
    return WorkerTierResponse(
        tier=tier,
        workers=config["workers"],
        rate_limits=config["rate_limits"],
        estimated_throughput=config["estimated_throughput"],
        message=f"⚠️ Worker tier set to {tier}. Please restart Docker worker to apply: docker-compose restart worker",
    )


@router.get("/config/worker-tier", response_model=WorkerTierResponse)
async def get_worker_tier(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current worker tier configuration.
    """
    current_tier = await get_current_tier_from_db(db)
    config = WORKER_TIER_CONFIG.get(current_tier, WORKER_TIER_CONFIG["standard"])

    return WorkerTierResponse(
        tier=current_tier,
        workers=config["workers"],
        rate_limits=config["rate_limits"],
        estimated_throughput=config["estimated_throughput"],
        message=f"Current worker tier: {current_tier}",
    )


@router.get("/config/worker-tiers")
async def get_all_worker_tiers(db: AsyncSession = Depends(get_db)):
    """
    Get all available worker tier configurations.
    """
    current_tier = await get_current_tier_from_db(db)
    return {
        "current_tier": current_tier,
        "tiers": WORKER_TIER_CONFIG,
    }


class WorkerRestartResponse(BaseModel):
    success: bool
    message: str
    workers_restarted: int


@router.post("/config/worker-tier/restart", response_model=WorkerRestartResponse)
async def restart_workers(
    db: AsyncSession = Depends(get_db),
):
    """
    Restart Celery workers to apply new tier configuration.

    This sends a SIGHUP signal to all workers to gracefully restart them
    with the new configuration from the database.
    """
    from app.worker.celery_app import celery_app

    current_tier = await get_current_tier_from_db(db)
    config = WORKER_TIER_CONFIG[current_tier]

    # Update the cache with new config
    update_worker_config_cache(
        tier=current_tier,
        workers=config["workers"],
        rate_limits=config["rate_limits"],
    )

    # Publish restart event
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.publish("linew:worker:restart", json.dumps({
            "tier": current_tier,
            "workers": config["workers"],
            "rate_limits": config["rate_limits"],
        }))
        logger.info(f"Published worker restart event: tier={current_tier}")
    except Exception as e:
        logger.warning(f"Failed to publish restart event: {e}")

    # Try to restart workers gracefully
    workers_restarted = 0
    try:
        # Get active workers
        inspector = celery_app.control.inspect()
        active = inspector.active()

        if active:
            workers_restarted = len(active)

            # Send SIGHUP to gracefully restart workers
            # This tells workers to restart with new configuration
            celery_app.control.broadcast("shutdown", destination=None)
            logger.info(f"Sent shutdown signal to {workers_restarted} workers")

    except Exception as e:
        logger.warning(f"Failed to restart workers: {e}")

    return WorkerRestartResponse(
        success=True,
        message=f"Worker tier {current_tier} configuration applied. {workers_restarted} workers signaled to restart.",
        workers_restarted=workers_restarted,
    )
