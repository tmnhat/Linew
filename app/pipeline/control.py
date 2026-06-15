"""
Pipeline control - manages pipeline state (start/stop/pause) via Redis.

Updated với Hard Stop mechanism:
- stop_pipeline() → Gọi trigger_user_stop() để set Redis stop signal
- start_pipeline() → Gọi clear_user_stop() để xóa signal
- Pipeline check should_stop_pipeline() trước mỗi batch
"""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# Redis keys
PIPELINE_STATE_KEY = "linew:pipeline:state"
PIPELINE_MODE_KEY = "linew:pipeline:mode"
PIPELINE_STARTED_AT_KEY = "linew:pipeline:started_at"
PIPELINE_STATS_KEY = "linew:pipeline:stats"
PIPELINE_LOCK_KEY = "linew:pipeline:lock"


class PipelineState(str, Enum):
    """Pipeline running states."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"


class PipelineMode(str, Enum):
    """Pipeline execution modes."""
    NORMAL = "normal"
    ALLIN = "allin"
    CONTINUOUS = "continuous"


async def get_pipeline_state() -> PipelineState:
    """Get current pipeline state from Redis."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        state = await redis.get(PIPELINE_STATE_KEY)
        if state and state in [s.value for s in PipelineState]:
            return PipelineState(state)
    except Exception as e:
        logger.error(f"Failed to get pipeline state: {e}")
    
    return PipelineState.STOPPED


async def set_pipeline_state(state: PipelineState, mode: PipelineMode = PipelineMode.NORMAL) -> None:
    """Set pipeline state in Redis."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        await redis.set(PIPELINE_STATE_KEY, state.value)
        await redis.set(PIPELINE_MODE_KEY, mode.value)
        
        if state == PipelineState.RUNNING:
            await redis.set(PIPELINE_STARTED_AT_KEY, datetime.utcnow().isoformat())
        
        logger.info(f"Pipeline state set to: {state.value} (mode: {mode.value})")
    except Exception as e:
        logger.error(f"Failed to set pipeline state: {e}")
        raise


async def is_pipeline_running() -> bool:
    """Check if pipeline is currently running."""
    state = await get_pipeline_state()
    return state == PipelineState.RUNNING


async def is_pipeline_stopped() -> bool:
    """Check if pipeline is stopped."""
    state = await get_pipeline_state()
    return state == PipelineState.STOPPED


async def acquire_pipeline_lock(timeout: int = 3600) -> bool:
    """
    Acquire pipeline lock to prevent concurrent pipeline runs.
    Returns True if lock acquired, False otherwise.
    """
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        # Use SET NX with expiration for atomic lock acquisition
        acquired = await redis.set(
            PIPELINE_LOCK_KEY, 
            datetime.utcnow().isoformat(),
            nx=True,  # Only set if not exists
            ex=timeout  # Auto-expire after timeout seconds
        )
        if acquired:
            logger.debug("Pipeline lock acquired")
        else:
            logger.debug("Pipeline lock not available")
        return bool(acquired)
    except Exception as e:
        logger.error(f"Failed to acquire pipeline lock: {e}")
        return False


async def release_pipeline_lock() -> None:
    """Release pipeline lock."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        await redis.delete(PIPELINE_LOCK_KEY)
        logger.debug("Pipeline lock released")
    except Exception as e:
        logger.error(f"Failed to release pipeline lock: {e}")


async def get_pipeline_stats() -> dict:
    """Get pipeline statistics."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        stats = await redis.hgetall(PIPELINE_STATS_KEY)
        return {k: int(v) if v.isdigit() else v for k, v in stats.items()}
    except Exception as e:
        logger.error(f"Failed to get pipeline stats: {e}")
        return {}


async def update_pipeline_stats(
    articles_processed: int = 0,
    articles_published: int = 0,
    articles_failed: int = 0,
) -> None:
    """Update pipeline statistics."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        pipe = redis.pipeline()
        
        if articles_processed > 0:
            pipe.hincrby(PIPELINE_STATS_KEY, "articles_processed", articles_processed)
        if articles_published > 0:
            pipe.hincrby(PIPELINE_STATS_KEY, "articles_published", articles_published)
        if articles_failed > 0:
            pipe.hincrby(PIPELINE_STATS_KEY, "articles_failed", articles_failed)
        
        pipe.hset(PIPELINE_STATS_KEY, "last_updated", datetime.utcnow().isoformat())
        await pipe.execute()
    except Exception as e:
        logger.error(f"Failed to update pipeline stats: {e}")


async def reset_pipeline_stats() -> None:
    """Reset pipeline statistics."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        await redis.delete(PIPELINE_STATS_KEY)
    except Exception as e:
        logger.error(f"Failed to reset pipeline stats: {e}")


async def get_pipeline_info() -> dict:
    """Get full pipeline information."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        
        # Get all values in parallel
        state = await redis.get(PIPELINE_STATE_KEY) or PipelineState.STOPPED.value
        mode = await redis.get(PIPELINE_MODE_KEY) or PipelineMode.NORMAL.value
        started_at = await redis.get(PIPELINE_STARTED_AT_KEY)
        has_lock = await redis.exists(PIPELINE_LOCK_KEY)
        
        # Get stats
        stats = await redis.hgetall(PIPELINE_STATS_KEY)
        
        return {
            "state": state,
            "mode": mode,
            "started_at": started_at,
            "has_lock": bool(has_lock),
            "is_running": state == PipelineState.RUNNING.value,
            "is_continuous": mode == PipelineMode.CONTINUOUS.value,
            "stats": {k: int(v) if v.isdigit() else v for k, v in stats.items()},
        }
    except Exception as e:
        logger.error(f"Failed to get pipeline info: {e}")
        return {
            "state": PipelineState.STOPPED.value,
            "mode": PipelineMode.NORMAL.value,
            "started_at": None,
            "has_lock": False,
            "is_running": False,
            "is_continuous": False,
            "stats": {},
        }


# Convenience functions for scheduler_tasks and celery_app
async def start_pipeline(mode: PipelineMode = PipelineMode.NORMAL) -> dict:
    """
    Start the pipeline with specified mode.
    
    Fixed race condition: Use atomic lock acquisition with retry.
    """
    # === CLEAR USER STOP SIGNAL ===
    from app.pipeline.hard_stop import clear_user_stop
    try:
        clear_result = clear_user_stop()
        if not clear_result.get("success"):
            logger.warning(f"Failed to clear user stop: {clear_result}")
    except Exception as clear_error:
        logger.warning(f"Error clearing user stop: {clear_error}")
    
    # === FIX: Atomic lock acquisition with retry to prevent race condition ===
    # Previously there was a race condition where:
    # 1. Thread A checks lock - not acquired
    # 2. Thread B checks lock - not acquired
    # 3. Thread A releases lock (if exists)
    # 4. Thread B releases lock (removes Thread A's lock!)
    # 5. Thread A acquires lock
    # 6. Thread B acquires lock - CONFLICT!
    
    max_retries = 3
    for attempt in range(max_retries):
        lock_acquired = await acquire_pipeline_lock()
        
        if lock_acquired:
            break
            
        # Lock not acquired, check current state
        current_state = await get_pipeline_state()
        if current_state == PipelineState.RUNNING:
            return {"success": False, "message": "Pipeline already running", "state": current_state.value}
        
        # Lock exists but state is not running - lock might be stale
        # Wait briefly and retry
        logger.warning(f"Pipeline lock exists but state is {current_state.value}, retrying ({attempt + 1}/{max_retries})")
        await asyncio.sleep(0.5)
    
    if not lock_acquired:
        # After retries, try force acquire
        logger.warning("Force acquiring pipeline lock after retries")
        await release_pipeline_lock()
        await asyncio.sleep(0.1)  # Brief pause
        lock_acquired = await acquire_pipeline_lock()
        if not lock_acquired:
            return {"success": False, "message": "Failed to acquire pipeline lock", "state": "error"}
    
    try:
        await set_pipeline_state(PipelineState.RUNNING, mode)
        await reset_pipeline_stats()
        
        return {
            "success": True,
            "message": f"Pipeline started in {mode.value} mode",
            "state": PipelineState.RUNNING.value,
            "mode": mode.value,
        }
    except Exception as e:
        logger.error(f"Failed to set pipeline state: {e}")
        await release_pipeline_lock()
        return {"success": False, "message": f"Failed to start pipeline: {str(e)}", "state": "error"}


async def stop_pipeline(reason: str = "User requested stop") -> dict:
    """
    Stop the pipeline.
    
    Args:
        reason: Lý do dừng pipeline
    
    Fixed: Better error handling for Redis operations.
    """
    try:
        current_state = await get_pipeline_state()
    except Exception as state_error:
        logger.warning(f"Failed to get pipeline state: {state_error}")
        current_state = PipelineState.STOPPED
    
    if current_state == PipelineState.STOPPED:
        return {"success": True, "message": "Pipeline already stopped", "state": current_state.value}
    
    # === TRIGGER HARD STOP ===
    from app.pipeline.hard_stop import trigger_user_stop
    try:
        stop_result = trigger_user_stop(reason)
        if not stop_result.get("success"):
            logger.warning(f"Failed to trigger hard stop: {stop_result}")
    except Exception as hard_stop_error:
        logger.warning(f"Hard stop error (non-critical): {hard_stop_error}")
        stop_result = {"success": False}
    
    # === FIX: XÓA is_continuous FLAG để watchdog/heartbeat không auto-restart ===
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.delete("linew:pipeline:mode")  # Xóa mode để is_continuous = False
    except Exception as redis_error:
        logger.warning(f"Failed to clear pipeline mode: {redis_error}")
    
    # === Set state and release lock ===
    try:
        await set_pipeline_state(PipelineState.STOPPED)
    except Exception as state_error:
        logger.warning(f"Failed to set pipeline state: {state_error}")
    
    try:
        await release_pipeline_lock()
    except Exception as lock_error:
        logger.warning(f"Failed to release pipeline lock: {lock_error}")
    
    return {
        "success": True,
        "message": "Pipeline stopped",
        "state": PipelineState.STOPPED.value,
        "stop_signal": stop_result,
    }


async def pause_pipeline() -> dict:
    """Pause the pipeline (stops after current article)."""
    current_state = await get_pipeline_state()
    
    if current_state != PipelineState.RUNNING:
        return {"success": False, "message": f"Cannot pause - pipeline is {current_state.value}"}
    
    await set_pipeline_state(PipelineState.PAUSED)
    
    return {
        "success": True,
        "message": "Pipeline paused (will stop after current article)",
        "state": PipelineState.PAUSED.value,
    }


async def resume_pipeline() -> dict:
    """Resume a paused pipeline."""
    current_state = await get_pipeline_state()
    
    if current_state != PipelineState.PAUSED:
        return {"success": False, "message": f"Cannot resume - pipeline is {current_state.value}"}
    
    mode_str = await get_redis_mode()
    mode = PipelineMode(mode_str) if mode_str in [m.value for m in PipelineMode] else PipelineMode.CONTINUOUS
    await set_pipeline_state(PipelineState.RUNNING, mode)
    
    return {
        "success": True,
        "message": "Pipeline resumed",
        "state": PipelineState.RUNNING.value,
    }


async def get_redis_mode() -> str:
    """Get current pipeline mode from Redis."""
    from app.core.redis import get_redis
    
    try:
        redis = await get_redis()
        mode = await redis.get(PIPELINE_MODE_KEY)
        return mode or PipelineMode.NORMAL.value
    except Exception:
        return PipelineMode.NORMAL.value
