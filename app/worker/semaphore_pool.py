"""
Redis-based semaphore pool for limiting concurrent task execution.

This allows parallel processing while maintaining a maximum number of concurrent
tasks for each pipeline stage (research, govern, etc.).
"""
import asyncio
import logging
import time
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Default pool sizes
DEFAULT_POOL_SIZES = {
    'research': 5,   # 5 concurrent research tasks
    'govern': 5,     # 5 concurrent governance tasks
    'write': 3,      # 3 concurrent write tasks
    'publish': 3,    # 3 concurrent publish tasks
}


class SemaphorePool:
    """
    Redis-based semaphore pool for controlling concurrent task execution.
    
    Uses Redis SETNX for distributed locking to ensure only N tasks
    can run concurrently across all workers.
    """
    
    def __init__(self, pool_name: str, pool_size: int, lock_timeout: int = 300):
        """
        Initialize semaphore pool.
        
        Args:
            pool_name: Name of the pool (e.g., 'research', 'govern')
            pool_size: Maximum concurrent tasks
            lock_timeout: Seconds before lock expires (default 5 minutes)
        """
        self.pool_name = pool_name
        self.pool_size = pool_size
        self.lock_timeout = lock_timeout
        self._local_slots: Dict[str, bool] = {}  # For local tracking
    
    def _get_slot_key(self, slot_id: int) -> str:
        """Get Redis key for a slot."""
        return f"linew:pool:{self.pool_name}:slot-{slot_id}"
    
    def _get_info_key(self) -> str:
        """Get Redis key for pool info."""
        return f"linew:pool:{self.pool_name}:info"
    
    async def acquire(self) -> Optional[int]:
        """
        Try to acquire a slot in the pool.
        
        Returns:
            Slot ID (0-based) if successful, None if pool is full
        """
        from app.core.redis import get_redis
        
        redis = await get_redis()
        
        # Try each slot
        for slot_id in range(self.pool_size):
            key = self._get_slot_key(slot_id)
            # Try to set with NX (only if not exists) and EX (expiry)
            acquired = await redis.set(
                key, 
                "locked", 
                nx=True, 
                ex=self.lock_timeout
            )
            if acquired:
                logger.info(f"Pool '{self.pool_name}': Acquired slot {slot_id}")
                return slot_id
        
        # Pool is full
        logger.debug(f"Pool '{self.pool_name}': All {self.pool_size} slots occupied")
        return None
    
    async def acquire_with_wait(
        self, 
        timeout: float = 300, 
        poll_interval: float = 1.0
    ) -> Optional[int]:
        """
        Try to acquire a slot, waiting if pool is full.
        
        Args:
            timeout: Maximum seconds to wait
            poll_interval: Seconds between polls
            
        Returns:
            Slot ID if successful, None if timeout
        """
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout:
            slot_id = await self.acquire()
            if slot_id is not None:
                return slot_id
            
            attempts += 1
            if attempts % 10 == 0:
                logger.info(f"Pool '{self.pool_name}': Waiting for slot ({attempts} attempts)")
            
            await asyncio.sleep(poll_interval)
        
        logger.warning(f"Pool '{self.pool_name}': Timeout waiting for slot after {timeout}s")
        return None
    
    async def release(self, slot_id: int) -> bool:
        """
        Release a slot back to the pool.
        
        Args:
            slot_id: The slot ID to release
            
        Returns:
            True if released, False if slot was not held
        """
        from app.core.redis import get_redis
        
        redis = await get_redis()
        key = self._get_slot_key(slot_id)
        
        # Delete the key
        deleted = await redis.delete(key)
        
        if deleted:
            logger.info(f"Pool '{self.pool_name}': Released slot {slot_id}")
        else:
            logger.warning(f"Pool '{self.pool_name}': Slot {slot_id} was already released")
        
        return bool(deleted)
    
    async def get_status(self) -> Dict:
        """
        Get current status of the pool.
        
        Returns:
            Dict with pool status info
        """
        from app.core.redis import get_redis
        
        redis = await get_redis()
        
        occupied_slots = []
        available_count = 0
        
        for slot_id in range(self.pool_size):
            key = self._get_slot_key(slot_id)
            exists = await redis.exists(key)
            if exists:
                ttl = await redis.ttl(key)
                occupied_slots.append({
                    'slot_id': slot_id,
                    'ttl': ttl
                })
            else:
                available_count += 1
        
        return {
            'pool_name': self.pool_name,
            'pool_size': self.pool_size,
            'occupied': len(occupied_slots),
            'available': available_count,
            'is_full': available_count == 0,
            'occupied_slots': occupied_slots,
        }
    
    async def release_all(self) -> int:
        """
        Release all slots in the pool (for cleanup).
        
        Returns:
            Number of slots released
        """
        from app.core.redis import get_redis
        
        redis = await get_redis()
        released = 0
        
        for slot_id in range(self.pool_size):
            key = self._get_slot_key(slot_id)
            deleted = await redis.delete(key)
            released += int(deleted)
        
        logger.info(f"Pool '{self.pool_name}': Released {released}/{self.pool_size} slots")
        return released


class PoolManager:
    """
    Manages multiple semaphore pools.
    
    Singleton pattern to ensure consistent pool management across the application.
    """
    
    _instance = None
    _pools: Dict[str, SemaphorePool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._pools = {}
    
    def get_pool(self, pool_name: str, pool_size: int = None) -> SemaphorePool:
        """
        Get or create a semaphore pool.
        
        Args:
            pool_name: Name of the pool
            pool_size: Size of pool (uses DEFAULT_POOL_SIZES if not specified)
            
        Returns:
            SemaphorePool instance
        """
        if pool_name not in self._pools:
            size = pool_size or DEFAULT_POOL_SIZES.get(pool_name, 1)
            self._pools[pool_name] = SemaphorePool(pool_name, size)
            logger.info(f"Created pool '{pool_name}' with size {size}")
        
        return self._pools[pool_name]
    
    async def get_all_status(self) -> List[Dict]:
        """Get status of all pools."""
        status = []
        for name, pool in self._pools.items():
            pool_status = await pool.get_status()
            status.append(pool_status)
        return status
    
    async def release_all_pools(self) -> Dict[str, int]:
        """Release all slots in all pools."""
        results = {}
        for name, pool in self._pools.items():
            released = await pool.release_all()
            results[name] = released
        return results


# Global instance
pool_manager = PoolManager()


async def get_pool(pool_name: str, pool_size: int = None) -> SemaphorePool:
    """Get a semaphore pool."""
    return pool_manager.get_pool(pool_name, pool_size)


async def with_pool_semaphore(
    pool_name: str,
    pool_size: int = None,
    timeout: float = 300,
):
    """
    Decorator/context manager for running code within a pool semaphore.
    
    Usage as decorator:
        @with_pool_semaphore('research')
        async def my_task():
            ...
    
    Usage as context manager:
        async with with_pool_semaphore('research'):
            # do work
    """
    pool = get_pool(pool_name, pool_size)
    
    class PoolContext:
        def __init__(self, p):
            self.pool = p
            self.slot_id = None
        
        async def __aenter__(self):
            self.slot_id = await self.pool.acquire_with_wait(timeout=timeout)
            if self.slot_id is None:
                raise TimeoutError(f"Timeout waiting for pool '{self.pool_name}' slot")
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.slot_id is not None:
                await self.pool.release(self.slot_id)
            return False
    
    return PoolContext(pool)
