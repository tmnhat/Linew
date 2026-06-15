"""
Redis connection for pub/sub and caching.
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
import redis as redis_sync

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Async Redis connection pool
redis_pool: Optional[redis.ConnectionPool] = None
redis_pool_initialized: bool = False

# Sync Redis connection pool for Celery tasks
redis_sync_pool: Optional[redis_sync.ConnectionPool] = None
redis_sync_pool_initialized: bool = False

# Connection retry settings
REDIS_MAX_RETRIES = 3
REDIS_RETRY_DELAY = 0.5  # seconds


def get_redis_sync_pool() -> redis_sync.ConnectionPool:
    """Get or create synchronous Redis connection pool for Celery."""
    global redis_sync_pool, redis_sync_pool_initialized
    
    if redis_sync_pool is None or not redis_sync_pool_initialized:
        try:
            redis_sync_pool = redis_sync.ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            test_client = redis_sync.Redis(connection_pool=redis_sync_pool)
            test_client.ping()
            redis_sync_pool_initialized = True
            logger.info("Redis sync pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis sync pool: {e}")
            # Return pool anyway - it might work later
            redis_sync_pool_initialized = True
            if redis_sync_pool is None:
                redis_sync_pool = redis_sync.ConnectionPool.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    max_connections=5,  # Reduced connections
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
    return redis_sync_pool


def get_redis_sync() -> redis_sync.Redis:
    """Get synchronous Redis client for Celery tasks."""
    try:
        return redis_sync.Redis(connection_pool=get_redis_sync_pool())
    except Exception as e:
        logger.error(f"Failed to get Redis sync client: {e}")
        raise


async def get_redis_pool() -> redis.ConnectionPool:
    """Get or create Redis connection pool with retry logic."""
    global redis_pool, redis_pool_initialized
    
    if redis_pool is None or not redis_pool_initialized:
        for attempt in range(REDIS_MAX_RETRIES):
            try:
                redis_pool = redis.ConnectionPool.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    max_connections=50,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                test_client = redis.Redis(connection_pool=redis_pool)
                await test_client.ping()
                redis_pool_initialized = True
                logger.info("Redis async pool initialized successfully")
                break
            except Exception as e:
                logger.warning(f"Redis pool initialization attempt {attempt + 1}/{REDIS_MAX_RETRIES} failed: {e}")
                if attempt == REDIS_MAX_RETRIES - 1:
                    logger.error(f"Redis pool initialization failed after {REDIS_MAX_RETRIES} attempts")
                    # Still return the pool - it might work later
                    redis_pool_initialized = True
                else:
                    import asyncio
                    await asyncio.sleep(REDIS_RETRY_DELAY)
    
    return redis_pool


async def get_redis() -> redis.Redis:
    """Get Redis client with automatic pool recovery."""
    global redis_pool, redis_pool_initialized
    
    try:
        pool = await get_redis_pool()
        client = redis.Redis(connection_pool=pool)
        
        # Test the connection
        try:
            await client.ping()
        except Exception as ping_error:
            logger.warning(f"Redis ping failed, reinitializing pool: {ping_error}")
            redis_pool = None
            redis_pool_initialized = False
            pool = await get_redis_pool()
            client = redis.Redis(connection_pool=pool)
            
        return client
    except Exception as e:
        logger.error(f"Failed to get Redis client: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connections."""
    global redis_pool, redis_pool_initialized, redis_sync_pool, redis_sync_pool_initialized
    
    if redis_pool is not None:
        await redis_pool.disconnect()
        redis_pool = None
        redis_pool_initialized = False
        logger.info("Redis async connections closed")
    
    if redis_sync_pool is not None:
        redis_sync_pool.disconnect()
        redis_sync_pool = None
        redis_sync_pool_initialized = False
        logger.info("Redis sync connections closed")


async def publish_event(channel: str, data: dict[str, Any]) -> None:
    """
    Publish event to Redis pub/sub channel.
    Used for WebSocket real-time updates.
    """
    try:
        client = await get_redis()
        await client.publish(channel, json.dumps(data, default=str))
        logger.debug(f"Published to {channel}: {data.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to publish event to {channel}: {e}")


async def set_cache(key: str, value: Any, expire_seconds: int = 300) -> bool:
    """
    Set a cache value with expiration.
    
    Returns True if successful, False otherwise.
    """
    try:
        client = await get_redis()
        await client.setex(key, expire_seconds, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.error(f"Failed to set cache {key}: {e}")
        return False


async def get_cache(key: str) -> Optional[Any]:
    """Get a cached value."""
    try:
        client = await get_redis()
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Failed to get cache {key}: {e}")
        return None


async def delete_cache(key: str) -> bool:
    """Delete a cached value."""
    try:
        client = await get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Failed to delete cache {key}: {e}")
        return False


async def check_redis_health() -> dict:
    """
    Check Redis health status.
    
    Returns dict with health information.
    """
    health = {
        "healthy": False,
        "latency_ms": None,
        "error": None,
        "pool_initialized": redis_pool_initialized,
        "sync_pool_initialized": redis_sync_pool_initialized,
    }
    
    try:
        client = await get_redis()
        import time
        start = time.time()
        await client.ping()
        health["latency_ms"] = (time.time() - start) * 1000
        health["healthy"] = True
    except Exception as e:
        health["error"] = str(e)
        logger.error(f"Redis health check failed: {e}")
    
    return health


# Pub/sub channels
CHANNEL_ARTICLE_EVENTS = "linew:article_events"
CHANNEL_SYSTEM_EVENTS = "linew:system_events"
