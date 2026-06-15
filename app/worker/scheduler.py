"""
Celery Beat scheduler configuration.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Redis key for storing schedule settings
SCHEDULE_SETTINGS_KEY = "linew:schedule:settings"

# Cache for schedule with TTL
_cached_schedule: Optional[dict] = None
_cache_ttl: int = 60  # seconds

# Schedule definitions
SCHEDULE_DEFINITIONS = {
    # Fetch RSS feeds every 30 minutes
    "fetch_all_sources": {
        "task": "app.worker.scheduler_tasks.task_fetch_all_sources",
        "schedule": 30 * 60,  # 30 minutes in seconds
        "kwargs": {},
    },
    # Run pipeline every 60 minutes
    "run_pipeline": {
        "task": "app.worker.scheduler_tasks.task_run_pipeline",
        "schedule": 60 * 60,  # 60 minutes in seconds
        "kwargs": {"mode": "normal", "limit": 20},
    },
    # Cleanup old signals daily at 3 AM
    "cleanup_signals": {
        "task": "app.worker.scheduler_tasks.task_cleanup",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {},
    },
    # Health check every 5 minutes
    "health_check": {
        "task": "app.worker.scheduler_tasks.task_health_check",
        "schedule": 5 * 60,  # 5 minutes
        "kwargs": {},
    },
    # Prediction System Tasks
    # Fetch prices daily at 7:00 AM
    "fetch-prices": {
        "task": "app.prediction.tasks.task_fetch_all_prices",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {},
    },
    # Run model inference daily at 7:30 AM
    "run-model-inference": {
        "task": "app.prediction.tasks.task_run_model_inference",
        "schedule": crontab(hour=7, minute=30),
        "kwargs": {},
    },
    # Run AI analysis daily at 8:00 AM
    "run-ai-analysis": {
        "task": "app.prediction.tasks.task_run_ai_analysis",
        "schedule": crontab(hour=8, minute=0),
        "kwargs": {},
    },
    # Update accuracy metrics daily at 9:00 AM
    "update-accuracy": {
        "task": "app.prediction.tasks.task_update_accuracy",
        "schedule": crontab(hour=9, minute=0),
        "kwargs": {},
    },
    # Check price alerts every 2 hours
    "check-price-alerts": {
        "task": "app.prediction.tasks.task_check_alerts",
        "schedule": 2 * 60 * 60,  # 2 hours in seconds
        "kwargs": {},
    },
    # Prediction V3 Tasks
    # Update adaptive weights every Monday at 2:00 AM
    "update-adaptive-weights": {
        "task": "app.prediction.tasks.task_update_adaptive_weights",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Every Monday 2:00 AM
        "kwargs": {},
    },
    # Walk-forward backtest every Monday at 3:00 AM
    "weekly-backtest": {
        "task": "app.prediction.tasks.task_weekly_backtest",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Every Monday 3:00 AM
        "kwargs": {},
    },
    # Confidence calibration every Monday at 4:00 AM
    # Note: Celery crontab doesn't support "every 2 weeks", so we use weekly
    # To run biweekly, consider using external scheduler or custom logic
    "biweekly-calibration": {
        "task": "app.prediction.tasks.task_calibrate_confidence",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),  # Every Monday 4:00 AM
        "kwargs": {},
    },
    # Pipeline watchdog - check every 5 minutes to restart stalled pipelines
    # This is CRITICAL for keeping continuous mode running 24/7
    "pipeline_watchdog": {
        "task": "app.worker.maintenance_tasks.task_pipeline_watchdog",
        "schedule": 5 * 60,  # 5 minutes (reduced from 2 minutes to lower overhead)
        "kwargs": {},
    },
    # Pipeline heartbeat - check every 2 minutes to ensure continuous mode is alive
    "pipeline_heartbeat": {
        "task": "app.worker.maintenance_tasks.task_pipeline_heartbeat",
        "schedule": 2 * 60,  # 2 minutes (reduced from 1 minute to lower overhead)
        "kwargs": {},
    },
    # Facebook scheduled posting - every 80 minutes (configurable)
    # Posts the highest-trending article without any links
    "facebook_scheduled": {
        "task": "app.distribution.tasks.task_facebook_scheduled",
        "schedule": 80 * 60,  # 80 minutes
        "kwargs": {},
    },
    # Newsletter - send daily digest at 7:00 AM
    "send-newsletter": {
        "task": "app.distribution.tasks.task_send_newsletter",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {},
    },
    # Archive & Backup Tasks
    # Daily incremental archive at 2:00 AM
    "daily-archive": {
        "task": "app.archive.tasks.task_daily_archive",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {},
    },
    # Monthly full archive at 2:00 AM on 1st of month
    "monthly-archive": {
        "task": "app.archive.tasks.task_monthly_archive",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),
        "kwargs": {},
    },
    # Monthly PostgreSQL cleanup at 3:00 AM on 1st of month (after monthly archive)
    "monthly-cleanup": {
        "task": "app.archive.tasks.task_cleanup_postgres",
        "schedule": crontab(day_of_month=1, hour=3, minute=0),
        "kwargs": {},
    },
    # Daily Google Drive backup at 4:00 AM
    "daily-backup": {
        "task": "app.backup.tasks.task_daily_backup",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {},
    },
}


def get_beat_schedule() -> dict:
    """Get current Beat schedule, updated from database settings.

    This function reads scheduler settings from Redis cache (which is populated
    by background tasks) and applies them to the schedule.

    For Celery Beat to pick up changes, either:
    1. Restart Celery Beat, or
    2. Use dynamic scheduling with external scheduler (celery-redbeat)
    """
    global _cached_schedule

    # Try to get from Redis cache first
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        cached = r.get(SCHEDULE_SETTINGS_KEY)
        if cached:
            import json
            _cached_schedule = json.loads(cached)
            logger.info("Schedule loaded from Redis cache")
    except Exception as e:
        logger.warning(f"Failed to read schedule from Redis: {e}")

    # Build schedule with cached settings or defaults
    schedule = SCHEDULE_DEFINITIONS.copy()

    if _cached_schedule:
        # Apply RSS interval
        rss_minutes = _cached_schedule.get("scheduler", {}).get("rss_interval_minutes", 30)
        schedule["fetch_all_sources"]["schedule"] = rss_minutes * 60
        logger.info(f"RSS interval set to {rss_minutes} minutes")

        # Apply pipeline interval
        pipeline_minutes = _cached_schedule.get("scheduler", {}).get("pipeline_interval_minutes", 60)
        schedule["run_pipeline"]["schedule"] = pipeline_minutes * 60
        logger.info(f"Pipeline interval set to {pipeline_minutes} minutes")

        # Apply Facebook schedule interval if custom
        fb_minutes = _cached_schedule.get("distribution", {}).get("facebook_schedule_minutes")
        if fb_minutes:
            schedule["facebook_scheduled"]["schedule"] = fb_minutes * 60
            logger.info(f"Facebook schedule interval set to {fb_minutes} minutes")
    else:
        logger.info("Using default schedule intervals (no cache)")

    return schedule


async def load_schedule_settings_async() -> dict:
    """
    Load scheduler settings from database and cache to Redis.
    Call this from a background task or on startup.
    """
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.setting import Setting

    all_settings = {}
    async with async_session() as session:
        result = await session.execute(select(Setting))
        settings_list = result.scalars().all()
        for s in settings_list:
            all_settings[s.key] = s.value

    # Cache to Redis
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        import json
        r.setex(SCHEDULE_SETTINGS_KEY, _cache_ttl, json.dumps(all_settings))
        logger.info(f"Schedule settings cached to Redis: {list(all_settings.keys())}")
    except Exception as e:
        logger.warning(f"Failed to cache schedule to Redis: {e}")

    # Update global cache
    global _cached_schedule
    _cached_schedule = all_settings

    return all_settings


def load_schedule_settings_sync() -> dict:
    """
    Synchronous version of load_schedule_settings.
    Use this from Celery tasks.
    """
    import json
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.setting import Setting
    from app.config import get_settings

    settings = get_settings()

    # Create sync engine
    sync_engine = create_engine(
        settings.database_url.replace("+asyncpg", ""),  # Remove asyncpg prefix for sync
        pool_pre_ping=True,
    )

    all_settings = {}
    with Session(sync_engine) as session:
        result = session.execute(select(Setting))
        settings_list = result.scalars().all()
        for s in settings_list:
            all_settings[s.key] = s.value

    # Cache to Redis
    try:
        import redis
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.setex(SCHEDULE_SETTINGS_KEY, _cache_ttl, json.dumps(all_settings))
        logger.info(f"Schedule settings cached to Redis")
    except Exception as e:
        logger.warning(f"Failed to cache schedule to Redis: {e}")

    # Update global cache
    global _cached_schedule
    _cached_schedule = all_settings

    return all_settings


def update_schedule_from_settings(settings: dict) -> dict:
    """Update schedule intervals from settings dict.

    This function is kept for backward compatibility.
    The main flow now uses get_beat_schedule() which reads from cache.
    """
    schedule = SCHEDULE_DEFINITIONS.copy()

    # Update RSS interval
    rss_interval = settings.get("scheduler", {}).get("rss_interval_minutes", 30)
    schedule["fetch_all_sources"]["schedule"] = rss_interval * 60

    # Update pipeline interval
    pipeline_interval = settings.get("scheduler", {}).get("pipeline_interval_minutes", 60)
    schedule["run_pipeline"]["schedule"] = pipeline_interval * 60

    # Update Facebook schedule
    fb_interval = settings.get("distribution", {}).get("facebook_schedule_minutes", 80)
    schedule["facebook_scheduled"]["schedule"] = fb_interval * 60

    # Update newsletter schedule based on frequency
    newsletter_freq = settings.get("newsletter", {}).get("frequency", "daily")
    send_time = settings.get("newsletter", {}).get("send_time", "07:00")
    hour, minute = map(int, send_time.split(":"))

    if newsletter_freq == "weekly":
        # Send on Monday at specified time
        schedule["send-newsletter"] = {
            "task": "app.distribution.tasks.task_send_newsletter",
            "schedule": crontab(day_of_week=1, hour=hour, minute=minute),
            "kwargs": {},
        }
    else:
        # Send daily at specified time
        schedule["send-newsletter"] = {
            "task": "app.distribution.tasks.task_send_newsletter",
            "schedule": crontab(hour=hour, minute=minute),
            "kwargs": {},
        }

    return schedule
