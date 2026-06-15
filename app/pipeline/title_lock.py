"""
Title Hash Lock - Prevent duplicate article processing using Redis locks with DB fallback.

This module provides distributed locking to prevent multiple workers from processing
articles with the same title_hash simultaneously.

Features:
- Primary: Redis-based locking (fast, distributed)
- Fallback: Database-based locking (when Redis is unavailable)
- Fail-closed: If neither Redis nor DB is available, processing is blocked
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.core.redis import get_redis_sync

logger = logging.getLogger(__name__)

# Lock configuration
DEFAULT_LOCK_TTL_SECONDS = 3600  # 1 hour
LOCK_PREFIX = "linew:lock:title:"

# Flag to track Redis availability
_redis_available = True


def acquire_title_lock(
    title_hash: str,
    article_id: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    """
    Acquire a lock for a title_hash.

    This prevents multiple workers from processing articles with the same
    title_hash simultaneously, which would cause duplicate publications.

    Strategy:
    1. Try Redis lock first (fast)
    2. If Redis fails, try DB lock (fallback)
    3. If both fail, return False (fail closed)

    Args:
        title_hash: The SHA-256 hash of the normalized article title
        article_id: The ID of the article acquiring the lock
        ttl_seconds: Lock expiration time in seconds (default 1 hour)

    Returns:
        True if lock was acquired, False if another worker holds the lock
        or if locking system is unavailable
    """
    global _redis_available
    
    # Try Redis lock first
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"

        # NX = only set if not exists, EX = expire time
        acquired = r.set(lock_key, article_id, nx=True, ex=ttl_seconds)

        if acquired:
            _redis_available = True
            logger.debug(f"Acquired title lock (Redis): {title_hash[:16]}... for article {article_id}")
            return True
        else:
            # Check who holds the lock
            holder = r.get(lock_key)
            logger.debug(
                f"Failed to acquire title lock (Redis): {title_hash[:16]}... "
                f"(held by {holder})"
            )
            return False

    except Exception as redis_error:
        logger.warning(f"Redis lock failed: {redis_error}")
        _redis_available = False
        
        # Fallback to DB lock
        return _acquire_db_lock_fallback(title_hash, article_id, ttl_seconds)


def _acquire_db_lock_fallback(
    title_hash: str,
    article_id: str,
    ttl_seconds: int,
) -> bool:
    """
    Acquire a database lock as fallback when Redis is unavailable.
    
    This provides a last-resort mechanism to prevent race conditions
    during article processing.
    """
    try:
        import asyncio
        from app.pipeline.db_lock import db_lock_manager
        from app.core.database import get_db_context
        
        async def try_db_lock():
            async with get_db_context() as session:
                return await db_lock_manager.acquire(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                    owner_id=article_id,
                    ttl_seconds=ttl_seconds,
                )
        
        # Run async DB lock in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(try_db_lock())
            if result:
                logger.debug(f"Acquired title lock (DB fallback): {title_hash[:16]}... for article {article_id}")
            else:
                logger.debug(f"Failed to acquire title lock (DB fallback): {title_hash[:16]}... held by another")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"FATAL: Both Redis and DB lock failed: {e}")
        # Fail closed - do NOT process if we can't verify lock
        return False


def release_title_lock(title_hash: str, article_id: str) -> bool:
    """
    Release a lock for a title_hash.

    Only releases the lock if the current article holds it.
    
    Tries both Redis and DB release.

    Args:
        title_hash: The SHA-256 hash of the normalized article title
        article_id: The ID of the article releasing the lock

    Returns:
        True if lock was released, False otherwise
    """
    global _redis_available
    
    # Try Redis release first
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"

        # Check if we hold the lock
        holder = r.get(lock_key)
        if holder and holder == article_id:
            r.delete(lock_key)
            logger.debug(f"Released title lock (Redis): {title_hash[:16]}...")
            return True
        else:
            logger.debug(
                f"Cannot release title lock (Redis): {title_hash[:16]}... "
                f"(holder={holder}, expected={article_id})"
            )
            return False

    except Exception as redis_error:
        logger.warning(f"Redis release failed: {redis_error}")
        _redis_available = False
        
        # Fallback to DB release
        return _release_db_lock_fallback(title_hash, article_id)


def _release_db_lock_fallback(title_hash: str, article_id: str) -> bool:
    """Release a database lock as fallback."""
    try:
        import asyncio
        from app.pipeline.db_lock import db_lock_manager
        from app.core.database import get_db_context
        
        async def try_db_unlock():
            async with get_db_context() as session:
                return await db_lock_manager.release(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                    owner_id=article_id,
                )
        
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(try_db_unlock())
        finally:
            loop.close()
            
    except Exception as e:
        logger.warning(f"DB release failed: {e}")
        return False


def check_title_lock(title_hash: str) -> Optional[str]:
    """
    Check who holds the lock for a title_hash.

    Args:
        title_hash: The SHA-256 hash of the normalized article title

    Returns:
        Article ID holding the lock, or None if lock is free
    """
    global _redis_available
    
    # Try Redis first
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"
        holder = r.get(lock_key)
        _redis_available = True
        return holder.decode() if holder else None

    except Exception as redis_error:
        logger.warning(f"Redis check failed: {redis_error}")
        _redis_available = False
        
        # Fallback to DB check
        return _check_db_lock_fallback(title_hash)


def _check_db_lock_fallback(title_hash: str) -> Optional[str]:
    """Check database lock as fallback."""
    try:
        import asyncio
        from app.pipeline.db_lock import db_lock_manager
        from app.core.database import get_db_context
        
        async def try_db_check():
            async with get_db_context() as session:
                return await db_lock_manager.check(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                )
        
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(try_db_check())
        finally:
            loop.close()
            
    except Exception as e:
        logger.warning(f"DB check failed: {e}")
        return None


def extend_title_lock(
    title_hash: str,
    article_id: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    """
    Extend the TTL of a title_hash lock.

    Useful for long-running tasks that need to extend their lock.

    Args:
        title_hash: The SHA-256 hash of the normalized article title
        article_id: The ID of the article extending the lock
        ttl_seconds: New lock expiration time in seconds

    Returns:
        True if lock was extended, False otherwise
    """
    global _redis_available
    
    # Try Redis first
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"

        # Check if we hold the lock
        holder = r.get(lock_key)
        if holder and holder == article_id:
            r.expire(lock_key, ttl_seconds)
            logger.debug(f"Extended title lock (Redis): {title_hash[:16]}... by {ttl_seconds}s")
            return True
        else:
            logger.debug(
                f"Cannot extend title lock (Redis): {title_hash[:16]}... "
                f"(holder={holder}, expected={article_id})"
            )
            return False

    except Exception as redis_error:
        logger.warning(f"Redis extend failed: {redis_error}")
        _redis_available = False
        
        # Fallback to DB extend
        return _extend_db_lock_fallback(title_hash, article_id, ttl_seconds)


def _extend_db_lock_fallback(title_hash: str, article_id: str, ttl_seconds: int) -> bool:
    """Extend database lock as fallback."""
    try:
        import asyncio
        from app.pipeline.db_lock import db_lock_manager
        from app.core.database import get_db_context
        
        async def try_db_extend():
            async with get_db_context() as session:
                return await db_lock_manager.extend(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                    owner_id=article_id,
                    ttl_seconds=ttl_seconds,
                )
        
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(try_db_extend())
        finally:
            loop.close()
            
    except Exception as e:
        logger.warning(f"DB extend failed: {e}")
        return False


def is_redis_available() -> bool:
    """Check if Redis is currently available."""
    return _redis_available


async def acquire_title_lock_async(
    title_hash: str,
    article_id: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> bool:
    """
    Async version of acquire_title_lock.
    
    This is the preferred async interface as it avoids event loop nesting.
    """
    global _redis_available
    
    # Try Redis lock first
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"
        acquired = r.set(lock_key, article_id, nx=True, ex=ttl_seconds)
        
        if acquired:
            _redis_available = True
            logger.debug(f"Acquired title lock (Redis): {title_hash[:16]}... for article {article_id}")
            return True
        else:
            holder = r.get(lock_key)
            logger.debug(f"Failed to acquire title lock (Redis): {title_hash[:16]}... (held by {holder})")
            return False
            
    except Exception as redis_error:
        logger.warning(f"Redis lock failed (async): {redis_error}")
        _redis_available = False
        
        # Fallback to DB lock
        try:
            from app.pipeline.db_lock import db_lock_manager
            from app.core.database import get_db_context
            
            async with get_db_context() as session:
                result = await db_lock_manager.acquire(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                    owner_id=article_id,
                    ttl_seconds=ttl_seconds,
                )
            
            if result:
                logger.debug(f"Acquired title lock (DB fallback): {title_hash[:16]}... for article {article_id}")
            return result
            
        except Exception as db_error:
            logger.error(f"FATAL: Both Redis and DB lock failed (async): {db_error}")
            return False


async def release_title_lock_async(title_hash: str, article_id: str) -> bool:
    """Async version of release_title_lock."""
    global _redis_available
    
    # Try Redis first
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"
        holder = r.get(lock_key)
        
        if holder and holder == article_id:
            r.delete(lock_key)
            logger.debug(f"Released title lock (Redis): {title_hash[:16]}...")
            return True
        return False
        
    except Exception as redis_error:
        logger.warning(f"Redis release failed (async): {redis_error}")
        _redis_available = False
        
        # Fallback to DB
        try:
            from app.pipeline.db_lock import db_lock_manager
            from app.core.database import get_db_context
            
            async with get_db_context() as session:
                return await db_lock_manager.release(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                    owner_id=article_id,
                )
        except Exception:
            return False


async def check_title_lock_async(title_hash: str) -> Optional[str]:
    """Async version of check_title_lock."""
    global _redis_available
    
    try:
        r = get_redis_sync()
        lock_key = f"{LOCK_PREFIX}{title_hash}"
        holder = r.get(lock_key)
        _redis_available = True
        return holder.decode() if holder else None
        
    except Exception:
        _redis_available = False
        
        try:
            from app.pipeline.db_lock import db_lock_manager
            from app.core.database import get_db_context
            
            async with get_db_context() as session:
                return await db_lock_manager.check(
                    session=session,
                    lock_type="title_hash",
                    lock_key=title_hash,
                )
        except Exception:
            return None
