"""
Pipeline stability module - provides robust continuous pipeline execution.

Key features:
1. Circuit breaker pattern (NHẸ - không stop pipeline)
2. Pipeline guardian for health monitoring
3. Graceful degradation when external services fail
4. Redis-based coordination for distributed workers
5. AI unavailable tracking (KHÔNG BAO GIỜ stop pipeline vì AI)
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerState:
    """Tracks circuit breaker state for pipeline restarts."""
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    is_open: bool = False
    
    # Configuration
    failure_threshold: int = 10  # Tăng từ 5 lên 10 - ít nghiêm ngặt hơn
    recovery_timeout_seconds: int = 60  # 1 phút trước khi retry
    reset_success_count: int = 3  # Reset circuit after this many successes


class PipelineCircuitBreaker:
    """
    Pipeline Circuit Breaker - NHẸ hơn so với original.

    Key difference:
    - KHÔNG BAO GIỜ stop pipeline vì circuit breaker
    - Chỉ log warnings và brief pauses
    - Tự động recover sau recovery_timeout
    - Vẫn track failures để monitoring
    """
    
    def __init__(
        self,
        failure_threshold: int = 10,  # Tăng từ 5
        recovery_timeout_seconds: int = 60,
        reset_success_count: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.reset_success_count = reset_success_count
        
        # Mutable state
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()
    
    @property
    def consecutive_failures(self) -> int:
        return self._state.consecutive_failures
    
    @property
    def is_open(self) -> bool:
        # Circuit breaker luôn cho phép proceed - KHÔNG stop pipeline
        return False
    
    async def record_success(self) -> None:
        """Record a successful pipeline run."""
        async with self._lock:
            now = datetime.utcnow()
            self._state.last_success_time = now
            
            # Reset failure counter on success
            if self._state.consecutive_failures > 0:
                self._state.consecutive_failures = 0
                logger.info("Pipeline circuit breaker: reset failure count on success")
            
            # Close circuit if it was open
            if self._state.is_open:
                self._state.is_open = False
                logger.info("Pipeline circuit breaker: closed after successful run")
    
    async def record_failure(self, error: str = "") -> None:
        """Record a failed pipeline run."""
        async with self._lock:
            now = datetime.utcnow()
            self._state.consecutive_failures += 1
            self._state.last_failure_time = now
            
            # Log warning nhưng KHÔNG stop pipeline
            if self._state.consecutive_failures >= self.failure_threshold:
                if not self._state.is_open:
                    self._state.is_open = True
                    logger.warning(
                        f"Pipeline circuit breaker: HIGH FAILURES ({self._state.consecutive_failures}). "
                        f"Will pause briefly but continue running. Error: {error[:100]}"
                    )
                    # Set timeout để tự động recover
                    # KHÔNG dùng recovery_timeout dài vì không muốn stop pipeline
    
    async def can_proceed(self) -> tuple[bool, str]:
        """
        Check if pipeline can proceed.
        
        LUÔN LUÔN trả về True - KHÔNG BAO GIỜ stop pipeline.
        Chỉ log warnings nếu có nhiều failures.
        """
        if self._state.consecutive_failures >= self.failure_threshold:
            elapsed = 0
            if self._state.last_failure_time:
                elapsed = (datetime.utcnow() - self._state.last_failure_time).total_seconds()
            
            # Nếu đã qua recovery_timeout, tự động reset
            if elapsed >= self.recovery_timeout:
                async with self._lock:
                    self._state.is_open = False
                    self._state.consecutive_failures = 0
                    logger.info("Pipeline circuit breaker: auto-reset after recovery timeout")
                    return True, "OK"
            
            # Vẫn cho phép proceed nhưng log
            remaining = max(0, self.recovery_timeout - elapsed)
            return True, f"High failures, will continue with caution. Reset in {remaining:.0f}s"
        
        return True, "OK"
    
    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        elapsed = 0
        if self._state.last_failure_time:
            elapsed = (datetime.utcnow() - self._state.last_failure_time).total_seconds()
        
        return {
            "is_open": self._state.is_open,
            "consecutive_failures": self._state.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_remaining": max(0, self.recovery_timeout - elapsed),
            "last_failure": self._state.last_failure_time.isoformat() if self._state.last_failure_time else None,
            "last_success": self._state.last_success_time.isoformat() if self._state.last_success_time else None,
            "allow_proceed": True,  # Luôn cho phép proceed
        }


# Global circuit breaker instance
pipeline_circuit_breaker = PipelineCircuitBreaker()


async def check_external_services_health() -> dict:
    """
    Check health of external services that pipeline depends on.
    Returns dict with service health status.
    """
    health = {
        "redis": {"healthy": False, "latency_ms": None},
        "database": {"healthy": False, "latency_ms": None},
        "wordpress": {"healthy": False, "error": None},
    }
    
    # Check Redis
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        start = time.time()
        await redis.ping()
        health["redis"]["healthy"] = True
        health["redis"]["latency_ms"] = (time.time() - start) * 1000
    except Exception as e:
        health["redis"]["error"] = str(e)
        logger.error(f"Redis health check failed: {e}")
    
    # Check Database
    try:
        from app.core.database import get_db_context
        from sqlalchemy import text
        start = time.time()
        async with get_db_context() as session:
            await session.execute(text("SELECT 1"))
        health["database"]["healthy"] = True
        health["database"]["latency_ms"] = (time.time() - start) * 1000
    except Exception as e:
        health["database"]["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health


async def is_pipeline_stalled(
    last_activity_time: Optional[datetime],
    max_stall_seconds: int = 300,  # 5 minutes
) -> tuple[bool, str]:
    """
    Check if pipeline appears to be stalled.
    
    A pipeline is considered stalled if:
    - No heartbeat received in max_stall_seconds
    - No articles processed recently
    
    Returns (is_stalled, reason).
    """
    if last_activity_time is None:
        return False, "No activity recorded yet"
    
    elapsed = (datetime.utcnow() - last_activity_time).total_seconds()
    
    if elapsed > max_stall_seconds:
        return True, f"No activity for {elapsed:.0f}s (max: {max_stall_seconds}s)"
    
    return False, "OK"


async def get_pipeline_activity_status() -> dict:
    """
    Get current pipeline activity status from Redis.
    """
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        
        # Get heartbeat timestamp
        heartbeat = await redis.get("linew:pipeline:heartbeat")
        last_activity = await redis.get("linew:pipeline:last_activity")
        
        # Parse timestamps
        heartbeat_time = None
        activity_time = None
        
        if heartbeat:
            try:
                heartbeat_time = datetime.fromisoformat(heartbeat)
            except:
                pass
        
        if last_activity:
            try:
                activity_time = datetime.fromisoformat(last_activity)
            except:
                pass
        
        return {
            "heartbeat_time": heartbeat_time,
            "last_activity_time": activity_time,
            "heartbeat_age_seconds": (
                (datetime.utcnow() - heartbeat_time).total_seconds()
                if heartbeat_time else None
            ),
            "activity_age_seconds": (
                (datetime.utcnow() - activity_time).total_seconds()
                if activity_time else None
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get pipeline activity status: {e}")
        return {"error": str(e)}


async def update_pipeline_activity() -> None:
    """Update pipeline last activity timestamp."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        now = datetime.utcnow()
        await redis.set("linew:pipeline:last_activity", now.isoformat())
        await redis.set("linew:pipeline:heartbeat", now.isoformat())
    except Exception as e:
        logger.warning(f"Failed to update pipeline activity: {e}")


async def record_pipeline_metrics(
    articles_processed: int = 0,
    articles_published: int = 0,
    batch_duration_seconds: float = 0,
) -> None:
    """
    Record pipeline metrics for monitoring and alerting.
    """
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        pipe = redis.pipeline()
        
        # Increment counters
        if articles_processed > 0:
            pipe.hincrby("linew:pipeline:metrics", "articles_processed", articles_processed)
        if articles_published > 0:
            pipe.hincrby("linew:pipeline:metrics", "articles_published", articles_published)
        if articles_published > 0:
            pipe.hincrby("linew:pipeline:metrics", "batches_completed", 1)
        
        # Track batch duration
        if batch_duration_seconds > 0:
            pipe.hset("linew:pipeline:metrics", "last_batch_duration", str(batch_duration_seconds))
        
        # Update timestamp
        pipe.hset("linew:pipeline:metrics", "last_update", datetime.utcnow().isoformat())
        
        await pipe.execute()
    except Exception as e:
        logger.warning(f"Failed to record pipeline metrics: {e}")


async def get_pipeline_metrics() -> dict:
    """Get pipeline metrics for monitoring."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        metrics = await redis.hgetall("linew:pipeline:metrics")
        
        return {
            "articles_processed": int(metrics.get("articles_processed", 0)),
            "articles_published": int(metrics.get("articles_published", 0)),
            "batches_completed": int(metrics.get("batches_completed", 0)),
            "last_batch_duration": float(metrics.get("last_batch_duration", 0)),
            "last_update": metrics.get("last_update"),
        }
    except Exception as e:
        logger.error(f"Failed to get pipeline metrics: {e}")
        return {}


# === AI AVAILABILITY TRACKING ===

AI_UNAVAILABLE_KEY = "linew:ai:unavailable_since"
AI_CONSECUTIVE_FAILURES_KEY = "linew:ai:consecutive_failures"


async def check_ai_availability() -> dict:
    """
    Kiểm tra AI availability status từ Redis.
    Returns dict với thông tin AI có đang unavailable không.
    """
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        
        unavailable_since = await redis.get(AI_UNAVAILABLE_KEY)
        failures = await redis.get(AI_CONSECUTIVE_FAILURES_KEY)
        
        is_unavailable = unavailable_since is not None
        consecutive_failures = int(failures) if failures else 0
        
        # Calculate how long AI has been unavailable
        unavailable_duration = None
        if unavailable_since:
            try:
                unavailable_time = datetime.fromisoformat(unavailable_since)
                unavailable_duration = (datetime.utcnow() - unavailable_time).total_seconds()
            except:
                pass
        
        return {
            "is_available": not is_unavailable,
            "is_unavailable": is_unavailable,
            "unavailable_since": unavailable_since,
            "unavailable_duration_seconds": unavailable_duration,
            "consecutive_failures": consecutive_failures,
            "status": "healthy" if not is_unavailable else "degraded",
        }
    except Exception as e:
        logger.error(f"Failed to check AI availability: {e}")
        return {
            "is_available": True,  # Assume available if can't check
            "is_unavailable": False,
            "error": str(e),
        }


async def is_ai_available() -> bool:
    """
    Quick check xem AI có available không.
    Sử dụng trong pipeline để skip AI-dependent tasks khi cần.
    """
    status = await check_ai_availability()
    return status.get("is_available", True)


async def set_ai_unavailable() -> None:
    """Mark AI as unavailable in Redis."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        await redis.set(AI_UNAVAILABLE_KEY, datetime.utcnow().isoformat(), ex=3600)
        logger.warning("AI marked as unavailable in Redis")
    except Exception as e:
        logger.error(f"Failed to set AI unavailable: {e}")


async def set_ai_available() -> None:
    """Mark AI as available in Redis."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        await redis.delete(AI_UNAVAILABLE_KEY)
        await redis.delete(AI_CONSECUTIVE_FAILURES_KEY)
        logger.info("AI marked as available in Redis")
    except Exception as e:
        logger.error(f"Failed to set AI available: {e}")
