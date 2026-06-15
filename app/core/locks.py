"""
Distributed locking utilities for preventing race conditions.

Provides:
- Article-level locks (prevent duplicate article processing)
- Title-level locks (prevent duplicate title processing)
- Distribution locks (prevent duplicate distribution)
- Context managers for clean lock handling
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Lock prefixes
LOCK_PREFIX_ARTICLE = "linew:lock:article:"
LOCK_PREFIX_TITLE = "linew:lock:title:"
LOCK_PREFIX_DIST = "linew:dist:idempotency:"

# Default TTL
DEFAULT_LOCK_TTL = 3600  # 1 hour


class LockAcquisitionError(Exception):
    """Raised when lock cannot be acquired."""
    pass


class DistributedLock:
    """
    Distributed lock with atomic acquire/release.
    
    Uses Redis SETNX for atomic lock acquisition.
    Falls back to database lock if Redis unavailable.
    """
    
    def __init__(
        self,
        key: str,
        ttl: int = DEFAULT_LOCK_TTL,
        owner_id: Optional[str] = None,
    ):
        self.key = key
        self.ttl = ttl
        self.owner_id = owner_id or "unknown"
        self._redis_locked = False
        self._db_locked = False
    
    def acquire_redis(self) -> bool:
        """
        Acquire lock using Redis SETNX.
        Returns True if lock acquired, False otherwise.
        """
        try:
            from app.core.redis import get_redis_sync
            r = get_redis_sync()
            
            acquired = r.set(
                self.key,
                self.owner_id,
                nx=True,  # Only set if not exists
                ex=self.ttl,  # Expiration in seconds
            )
            self._redis_locked = acquired
            return acquired
        except Exception as e:
            logger.warning(f"Redis lock failed for {self.key}: {e}")
            return False
    
    def release_redis(self) -> bool:
        """Release Redis lock. Only releases if owner matches."""
        if not self._redis_locked:
            return True
            
        try:
            from app.core.redis import get_redis_sync
            r = get_redis_sync()
            
            # Check owner before deleting (Lua script for atomicity)
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = r.eval(lua_script, 1, self.key, self.owner_id)
            self._redis_locked = False
            return result == 1
        except Exception as e:
            logger.warning(f"Redis release failed for {self.key}: {e}")
            return False
    
    def extend_redis(self, additional_ttl: Optional[int] = None) -> bool:
        """Extend lock TTL. Only extends if owner matches."""
        if not self._redis_locked:
            return False
            
        try:
            from app.core.redis import get_redis_sync
            r = get_redis_sync()
            
            new_ttl = additional_ttl or self.ttl
            
            # Lua script for atomic check-and-extend
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = r.eval(lua_script, 1, self.key, self.owner_id, new_ttl)
            return result == 1
        except Exception as e:
            logger.warning(f"Redis extend failed for {self.key}: {e}")
            return False
    
    def check_redis(self) -> Optional[str]:
        """Check who holds the lock. Returns owner_id or None."""
        try:
            from app.core.redis import get_redis_sync
            r = get_redis_sync()
            return r.get(self.key)
        except Exception as e:
            logger.warning(f"Redis check failed for {self.key}: {e}")
            return None


@asynccontextmanager
async def article_lock(
    article_id: str,
    owner_id: str,
    ttl: int = DEFAULT_LOCK_TTL,
    raise_on_failure: bool = False,
):
    """
    Context manager for article-level lock.
    
    Usage:
        async with article_lock(article_id, worker_id) as acquired:
            if acquired:
                # Process article
            else:
                # Skip - article already being processed
    
    Args:
        article_id: UUID of the article
        owner_id: Worker/task identifier
        ttl: Lock expiration in seconds
        raise_on_failure: If True, raises exception instead of returning False
    
    Yields:
        bool: True if lock acquired, False otherwise
    """
    key = f"{LOCK_PREFIX_ARTICLE}{article_id}"
    lock = DistributedLock(key, ttl, owner_id)
    
    acquired = lock.acquire_redis()
    
    if not acquired and raise_on_failure:
        raise LockAcquisitionError(f"Cannot acquire lock for article {article_id}")
    
    try:
        yield acquired
    finally:
        if acquired:
            lock.release_redis()


@asynccontextmanager
async def title_lock(
    title_hash: str,
    owner_id: str,
    ttl: int = DEFAULT_LOCK_TTL,
    raise_on_failure: bool = False,
):
    """
    Context manager for title-level lock.
    
    Prevents duplicate processing of articles with the same title.
    
    Usage:
        async with title_lock(title_hash, worker_id) as acquired:
            if acquired:
                # Process article
            else:
                # Skip - similar title already being processed
    
    Args:
        title_hash: SHA-256 hash of normalized title
        owner_id: Worker/task identifier
        ttl: Lock expiration in seconds
        raise_on_failure: If True, raises exception instead of returning False
    
    Yields:
        bool: True if lock acquired, False otherwise
    """
    key = f"{LOCK_PREFIX_TITLE}{title_hash}"
    lock = DistributedLock(key, ttl, owner_id)
    
    acquired = lock.acquire_redis()
    
    if not acquired and raise_on_failure:
        raise LockAcquisitionError(f"Cannot acquire lock for title {title_hash[:16]}...")
    
    try:
        yield acquired
    finally:
        if acquired:
            lock.release_redis()


class DistributionLock:
    """
    Idempotency lock for distribution operations.
    
    Uses Redis SETNX to ensure only one distribution per article/channel.
    TTL is shorter than article locks since distributions are fast.
    """
    
    def __init__(
        self,
        article_id: str,
        channel: str,
        ttl: int = 300,  # 5 minutes default
    ):
        self.article_id = article_id
        self.channel = channel
        self.ttl = ttl
        self.key = f"{LOCK_PREFIX_DIST}{article_id}:{channel}"
    
    def try_acquire(self) -> bool:
        """
        Try to acquire idempotency lock.
        
        Returns True if this is the first distribution attempt,
        False if distribution already in progress or completed.
        """
        try:
            from app.core.redis import get_redis_sync
            import json
            
            r = get_redis_sync()
            
            # Check if already locked (in progress or done)
            existing = r.get(self.key)
            if existing:
                try:
                    data = json.loads(existing)
                    if data.get("status") == "done":
                        logger.info(
                            f"Distribution already completed for "
                            f"{self.channel}/{self.article_id[:8]}..."
                        )
                    else:
                        logger.info(
                            f"Distribution in progress for "
                            f"{self.channel}/{self.article_id[:8]}..."
                        )
                except json.JSONDecodeError:
                    pass
                return False
            
            # Acquire lock
            data = json.dumps({
                "status": "in_progress",
                "started_at": time.time(),
            })
            acquired = r.set(self.key, data, nx=True, ex=self.ttl)
            
            if acquired:
                logger.debug(
                    f"Distribution lock acquired for "
                    f"{self.channel}/{self.article_id[:8]}..."
                )
            
            return acquired
            
        except Exception as e:
            logger.error(f"Distribution lock error: {e}")
            # Fail open - allow distribution if lock system fails
            return True
    
    def mark_complete(self, result: Optional[dict] = None) -> None:
        """Mark distribution as complete."""
        try:
            from app.core.redis import get_redis_sync
            import json
            
            r = get_redis_sync()
            
            data = json.dumps({
                "status": "done",
                "completed_at": time.time(),
                "result": result or {},
            })
            
            # Extend TTL significantly for completed operations
            r.setex(self.key, 86400, data)  # 24 hours
            logger.debug(
                f"Distribution marked complete for "
                f"{self.channel}/{self.article_id[:8]}..."
            )
            
        except Exception as e:
            logger.error(f"Distribution mark_complete error: {e}")
    
    def mark_failed(self, error: Optional[str] = None) -> None:
        """Mark distribution as failed and release lock."""
        try:
            from app.core.redis import get_redis_sync
            import json
            
            r = get_redis_sync()
            
            data = json.dumps({
                "status": "failed",
                "failed_at": time.time(),
                "error": error,
            })
            
            # Keep for a while for debugging
            r.setex(self.key, 3600, data)  # 1 hour
            logger.warning(
                f"Distribution marked failed for "
                f"{self.channel}/{self.article_id[:8]}...: {error}"
            )
            
        except Exception as e:
            logger.error(f"Distribution mark_failed error: {e}")
    
    def is_completed(self) -> bool:
        """Check if distribution already completed."""
        try:
            from app.core.redis import get_redis_sync
            import json
            
            r = get_redis_sync()
            data = r.get(self.key)
            
            if data:
                try:
                    parsed = json.loads(data)
                    return parsed.get("status") == "done"
                except json.JSONDecodeError:
                    return False
            return False
            
        except Exception as e:
            logger.error(f"Distribution is_completed error: {e}")
            return False


def is_article_locked(article_id: str) -> bool:
    """Check if article is currently locked."""
    key = f"{LOCK_PREFIX_ARTICLE}{article_id}"
    lock = DistributedLock(key)
    holder = lock.check_redis()
    return holder is not None


def is_title_locked(title_hash: str) -> bool:
    """Check if title is currently locked."""
    key = f"{LOCK_PREFIX_TITLE}{title_hash}"
    lock = DistributedLock(key)
    holder = lock.check_redis()
    return holder is not None


def release_all_locks_for_owner(owner_id: str) -> int:
    """
    Release all locks held by a specific owner.
    Useful for cleanup when a worker crashes.
    
    Returns count of released locks.
    """
    try:
        from app.core.redis import get_redis_sync
        
        r = get_redis_sync()
        released = 0
        
        # Release article locks
        article_pattern = f"{LOCK_PREFIX_ARTICLE}*"
        for key in r.scan_iter(match=article_pattern):
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            if r.eval(lua_script, 1, key, owner_id):
                released += 1
        
        # Release title locks
        title_pattern = f"{LOCK_PREFIX_TITLE}*"
        for key in r.scan_iter(match=title_pattern):
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            if r.eval(lua_script, 1, key, owner_id):
                released += 1
        
        if released > 0:
            logger.info(f"Released {released} locks for owner {owner_id}")
        
        return released
        
    except Exception as e:
        logger.error(f"Release all locks error: {e}")
        return 0
