"""
Database-based distributed lock fallback for when Redis is unavailable.

This module provides a fallback locking mechanism using the database
when Redis operations fail, ensuring we can still prevent duplicate processing.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributed_lock import DistributedLock
from app.core.database import get_db_context

logger = logging.getLogger(__name__)

# Lock configuration
DEFAULT_LOCK_TTL_SECONDS = 3600  # 1 hour
LOCK_PREFIX = "linew:db:lock:"


class DBLockManager:
    """
    Database-based distributed lock manager.
    
    This is a fallback mechanism when Redis locking is unavailable.
    It uses the database to store lock state and provides atomic operations.
    """
    
    def __init__(self, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
    
    async def acquire(
        self,
        session: AsyncSession,
        lock_type: str,
        lock_key: str,
        owner_id: str,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Acquire a database lock.
        
        Args:
            session: Database session
            lock_type: Type of lock (e.g., "title_hash", "article")
            lock_key: The key to lock (e.g., hash value, article ID)
            owner_id: ID of the worker acquiring the lock
            ttl_seconds: Lock TTL in seconds (optional, uses default if not provided)
        
        Returns:
            True if lock acquired, False if lock held by another owner
        """
        ttl = ttl_seconds or self.ttl_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        try:
            # Clean up expired locks first
            await self._cleanup_expired(session)
            
            # Check if lock already exists and is not expired
            existing = await self._get_lock(session, lock_type, lock_key)
            
            if existing:
                # Check if it's expired
                if existing.expires_at and existing.expires_at > datetime.utcnow():
                    # Lock is held by someone else
                    logger.debug(
                        f"DB lock held: {lock_type}:{lock_key} by {existing.owner_id}"
                    )
                    return False
                else:
                    # Lock expired, delete it
                    await session.delete(existing)
                    await session.commit()
            
            # Create new lock
            new_lock = DistributedLock(
                lock_type=lock_type,
                lock_key=lock_key,
                owner_id=owner_id,
                expires_at=expires_at,
            )
            session.add(new_lock)
            await session.commit()
            
            logger.debug(f"Acquired DB lock: {lock_type}:{lock_key} by {owner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acquire DB lock: {e}")
            await session.rollback()
            return False
    
    async def release(
        self,
        session: AsyncSession,
        lock_type: str,
        lock_key: str,
        owner_id: str,
    ) -> bool:
        """
        Release a database lock.
        
        Only releases if the current owner holds the lock.
        
        Args:
            session: Database session
            lock_type: Type of lock
            lock_key: The key that was locked
            owner_id: ID of the worker releasing the lock
        
        Returns:
            True if lock released, False otherwise
        """
        try:
            existing = await self._get_lock(session, lock_type, lock_key)
            
            if existing and existing.owner_id == owner_id:
                await session.delete(existing)
                await session.commit()
                logger.debug(f"Released DB lock: {lock_type}:{lock_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to release DB lock: {e}")
            await session.rollback()
            return False
    
    async def check(
        self,
        session: AsyncSession,
        lock_type: str,
        lock_key: str,
    ) -> Optional[str]:
        """
        Check who holds the lock.
        
        Args:
            session: Database session
            lock_type: Type of lock
            lock_key: The key to check
        
        Returns:
            Owner ID if lock is held, None if lock is free
        """
        try:
            existing = await self._get_lock(session, lock_type, lock_key)
            
            if existing:
                # Check if expired
                if existing.expires_at and existing.expires_at > datetime.utcnow():
                    return existing.owner_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check DB lock: {e}")
            return None
    
    async def extend(
        self,
        session: AsyncSession,
        lock_type: str,
        lock_key: str,
        owner_id: str,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Extend the TTL of a lock.
        
        Args:
            session: Database session
            lock_type: Type of lock
            lock_key: The key that was locked
            owner_id: ID of the worker extending the lock
            ttl_seconds: New TTL in seconds
        
        Returns:
            True if extended, False otherwise
        """
        ttl = ttl_seconds or self.ttl_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        try:
            existing = await self._get_lock(session, lock_type, lock_key)
            
            if existing and existing.owner_id == owner_id:
                existing.expires_at = expires_at
                await session.commit()
                logger.debug(f"Extended DB lock: {lock_type}:{lock_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to extend DB lock: {e}")
            await session.rollback()
            return False
    
    async def _get_lock(
        self,
        session: AsyncSession,
        lock_type: str,
        lock_key: str,
    ) -> Optional[DistributedLock]:
        """Get lock by type and key."""
        stmt = select(DistributedLock).where(
            DistributedLock.lock_type == lock_type,
            DistributedLock.lock_key == lock_key,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _cleanup_expired(self, session: AsyncSession) -> int:
        """Delete all expired locks. Returns count of deleted locks."""
        try:
            stmt = delete(DistributedLock).where(
                DistributedLock.expires_at < datetime.utcnow()
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        except Exception as e:
            logger.warning(f"Failed to cleanup expired locks: {e}")
            return 0


# Global instance
db_lock_manager = DBLockManager()


async def acquire_db_lock(
    lock_type: str,
    lock_key: str,
    owner_id: str,
    ttl_seconds: Optional[int] = None,
) -> bool:
    """
    Convenience function to acquire a database lock.
    
    Args:
        lock_type: Type of lock (e.g., "title_hash", "article")
        lock_key: The key to lock
        owner_id: ID of the worker
        ttl_seconds: Lock TTL
    
    Returns:
        True if lock acquired
    """
    async with get_db_context() as session:
        return await db_lock_manager.acquire(
            session, lock_type, lock_key, owner_id, ttl_seconds
        )


async def release_db_lock(
    lock_type: str,
    lock_key: str,
    owner_id: str,
) -> bool:
    """Convenience function to release a database lock."""
    async with get_db_context() as session:
        return await db_lock_manager.release(session, lock_type, lock_key, owner_id)
