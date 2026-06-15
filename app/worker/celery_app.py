"""
Celery application configuration.
"""
import asyncio
import logging
import os
import threading
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.config import get_settings
from app.worker.worker_config import (
    get_worker_concurrency,
    get_task_rate_limits,
    get_worker_config,
    WORKER_TIER_CONFIG,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Thread-local storage for event loops - MUST be defined before run_async
_thread_local = threading.local()


def run_async(coro):
    """
    Run an async coroutine in a Celery worker.

    Uses threading.local() to avoid memory leak - loops are automatically
    garbage collected when the thread ends.
    """
    loop = getattr(_thread_local, 'loop', None)

    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _thread_local.loop = loop

    try:
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        if "attached to a different loop" in str(e):
            # Create fresh loop for this specific call
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            _thread_local.loop = new_loop
            return new_loop.run_until_complete(coro)
        raise


# Parse Redis URL for Celery
redis_host = "localhost"
redis_port = 6379
redis_db = 0

try:
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    redis_host = parsed.hostname or "localhost"
    redis_port = parsed.port or 6379
    redis_db = int(parsed.path.lstrip("/") or 0)
except Exception:
    pass

# Import scheduler after settings
from app.worker.scheduler import get_beat_schedule

# Get dynamic worker config
_worker_config = get_worker_config()
_worker_concurrency = _worker_config.get("workers", 6)
_task_rate_limits = _worker_config.get("rate_limits", WORKER_TIER_CONFIG["standard"]["rate_limits"])

logger.info(f"Worker configuration: concurrency={_worker_concurrency}, tier={_worker_config.get('tier', 'standard')}")

# Create Celery app
celery_app = Celery(
    "linew",
    broker=f"redis://{redis_host}:{redis_port}/{redis_db}",
    backend=f"redis://{redis_host}:{redis_port}/{redis_db}",
    include=[
        "app.pipeline.tasks",
        "app.prediction.tasks",
        "app.worker.scheduler_tasks",
        "app.worker.prediction_tasks",
        "app.worker.pipeline_tasks",
        "app.worker.maintenance_tasks",
        "app.distribution.tasks",
        "app.archive.tasks",
        "app.backup.tasks",
    ],
)

# Build task_routes with rate limits from config
task_routes = {
    "app.pipeline.tasks.task_research": {"rate_limit": _task_rate_limits.get("research", "180/m")},
    "app.pipeline.tasks.task_write": {"rate_limit": _task_rate_limits.get("write", "120/m")},
    "app.pipeline.tasks.task_govern": {"rate_limit": _task_rate_limits.get("govern", "300/m")},
    "app.pipeline.tasks.task_categorize": {"rate_limit": _task_rate_limits.get("categorize", "600/m")},
    "app.pipeline.tasks.task_score_trend": {"rate_limit": _task_rate_limits.get("score", "600/m")},
    "app.pipeline.tasks.task_publish": {"rate_limit": _task_rate_limits.get("publish", "180/m")},
}

# Celery configuration - uses dynamic values from database/cache
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # === DYNAMIC WORKER CONCURRENCY ===
    worker_concurrency=_worker_concurrency,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,
    # === TASK RATE LIMITS - DYNAMIC ===
    task_routes=task_routes,
    # Result backend - results expire after 24 hours
    result_expires=86400,
    # Beat schedule - load from scheduler module
    beat_schedule=get_beat_schedule(),
)


# === PIPELINE TASK WRAPPERS ===

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_categorize_celery(self, article_id: str):
    """Celery wrapper for categorize task."""
    from app.pipeline.tasks import task_categorize
    return run_async(task_categorize(article_id))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_score_trend_celery(self, article_id: str):
    """Celery wrapper for trend scoring."""
    from app.pipeline.tasks import task_score_trend
    return run_async(task_score_trend(article_id))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_research_celery(self, article_id: str):
    """Celery wrapper for research task."""
    from app.pipeline.tasks import task_research
    return run_async(task_research(article_id))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def task_write_celery(self, article_id: str):
    """Celery wrapper for write task."""
    from app.pipeline.tasks import task_write
    return run_async(task_write(article_id))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_govern_celery(self, article_id: str):
    """Celery wrapper for governance task."""
    from app.pipeline.tasks import task_govern
    return run_async(task_govern(article_id))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_publish_celery(self, article_id: str):
    """Celery wrapper for publish task."""
    from app.pipeline.tasks import task_publish
    return run_async(task_publish(article_id))


@celery_app.task
def task_cleanup_celery():
    """Celery wrapper for cleanup task."""
    from app.pipeline.tasks import task_cleanup
    return run_async(task_cleanup())


@celery_app.task
def task_publish_approved_celery(limit: int = 20):
    """
    Celery task to auto-publish all APPROVED articles.
    This fixes the bug where governance sets articles to APPROVED but
    no task was triggering the publish.
    """
    from app.pipeline.tasks import task_publish_approved_articles
    return run_async(task_publish_approved_articles(limit=limit))


# === LEGACY TASK DEFINITIONS ===
# These are kept for backward compatibility.
# New code should use the tasks in app.worker.pipeline_tasks and app.worker.maintenance_tasks
#
# Note: Task imports are removed to avoid circular imports.
# Tasks are registered via the include list in celery_app.conf.update()
# and can be called directly via their full path (e.g., app.worker.pipeline_tasks.task_run_pipeline_celery)
