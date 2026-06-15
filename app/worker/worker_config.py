"""
Dynamic Worker Configuration Module.

Cho phép Celery worker đọc cấu hình từ database thay vì hardcoded values.
"""
import logging
from typing import Optional

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.setting import Setting

logger = logging.getLogger(__name__)

# Worker tier configurations
WORKER_TIER_CONFIG = {
    "standard": {
        "name": "Standard",
        "workers": 6,  # 1 worker per metric
        "rate_limits": {
            "research": "1/m",      # 60s per article
            "write": "1/m",         # 180s per article (bottleneck)
            "govern": "2/m",        # 30s per article
            "publish": "6/m",       # 10s per article
            "categorize": "60/m",   # 1s per article
            "score": "60/m",        # 1s per article
        },
        "estimated_throughput": 20,  # articles/hour (limited by Write)
    },
    "1": {
        "name": "Testing",
        "workers": 15,
        "rate_limits": {
            "research": "60/m",
            "write": "40/m",
            "govern": "100/m",
            "publish": "60/m",
            "categorize": "200/m",
            "score": "200/m",
        },
        "estimated_throughput": 200,
    },
    "2": {
        "name": "Light",
        "workers": 30,
        "rate_limits": {
            "research": "120/m",
            "write": "80/m",
            "govern": "200/m",
            "publish": "120/m",
            "categorize": "400/m",
            "score": "400/m",
        },
        "estimated_throughput": 600,
    },
    "3": {
        "name": "Normal",
        "workers": 45,
        "rate_limits": {
            "research": "180/m",
            "write": "120/m",
            "govern": "300/m",
            "publish": "180/m",
            "categorize": "600/m",
            "score": "600/m",
        },
        "estimated_throughput": 1200,
    },
    "4": {
        "name": "High",
        "workers": 60,
        "rate_limits": {
            "research": "240/m",
            "write": "160/m",
            "govern": "400/m",
            "publish": "240/m",
            "categorize": "800/m",
            "score": "800/m",
        },
        "estimated_throughput": 3000,
    },
}

# Cache key for worker config
WORKER_CONFIG_CACHE_KEY = "linew:worker:config"
WORKER_CONFIG_CACHE_TTL = 300  # 5 minutes


def get_worker_config() -> dict:
    """
    Get current worker configuration from Redis cache or defaults.
    This is called by Celery at startup.
    """
    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        
        # Try to get from cache first
        cached = r.get(WORKER_CONFIG_CACHE_KEY)
        if cached:
            import json
            config = json.loads(cached)
            logger.info(f"Worker config loaded from cache: tier={config.get('tier')}, workers={config.get('workers')}")
            return config
    except Exception as e:
        logger.warning(f"Failed to get worker config from Redis: {e}")
    
    # Return default Tier Standard (6 workers) for development
    return {
        "tier": "standard",
        "workers": 6,
        "rate_limits": WORKER_TIER_CONFIG["standard"]["rate_limits"],
    }


def get_worker_concurrency() -> int:
    """Get worker concurrency (number of concurrent workers)."""
    config = get_worker_config()
    return config.get("workers", 6)


def get_task_rate_limits() -> dict:
    """Get task rate limits for the current tier."""
    config = get_worker_config()
    return config.get("rate_limits", WORKER_TIER_CONFIG["standard"]["rate_limits"])


def update_worker_config_cache(tier: int, workers: int, rate_limits: dict):
    """Update the worker config cache in Redis."""
    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        import json
        
        config = {
            "tier": tier,
            "workers": workers,
            "rate_limits": rate_limits,
        }
        r.setex(WORKER_CONFIG_CACHE_KEY, WORKER_CONFIG_CACHE_TTL, json.dumps(config))
        logger.info(f"Worker config cache updated: tier={tier}, workers={workers}")
    except Exception as e:
        logger.warning(f"Failed to update worker config cache: {e}")


def invalidate_worker_config_cache():
    """Invalidate the worker config cache."""
    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.delete(WORKER_CONFIG_CACHE_KEY)
        logger.info("Worker config cache invalidated")
    except Exception as e:
        logger.warning(f"Failed to invalidate worker config cache: {e}")


async def get_current_tier_from_db(db: AsyncSession) -> str:
    """Get current worker tier from database."""
    try:
        result = await db.execute(
            select(Setting).where(Setting.key == "pipeline")
        )
        setting = result.scalar_one_or_none()
        if setting and setting.value and "worker_tier" in setting.value:
            tier = setting.value["worker_tier"]
            # Handle both string and int tiers
            if isinstance(tier, str):
                return tier
            return str(int(tier))
    except Exception as e:
        logger.warning(f"Error getting worker tier from database: {e}")
    return "standard"  # Default to Standard tier (6 workers)


def get_worker_tier_config(tier: str) -> dict:
    """Get configuration for a specific tier."""
    return WORKER_TIER_CONFIG.get(tier, WORKER_TIER_CONFIG.get("3", WORKER_TIER_CONFIG["standard"]))
