"""
Maintenance Celery tasks - watchdog, heartbeat, and health monitoring.

This module contains tasks for pipeline health monitoring:
- task_pipeline_watchdog: Robust continuous pipeline monitoring with auto-restart
- task_pipeline_heartbeat: Lightweight heartbeat for pipeline activity tracking
"""
import asyncio
import logging
import time

from app.worker.celery_app import celery_app, run_async
from app.core.database import get_db_context
from app.core.redis import get_redis
from app.pipeline.control import (
    get_pipeline_state,
    PipelineState,
    PipelineMode,
    get_pipeline_info,
    start_pipeline,
    PIPELINE_STATE_KEY,
)
from app.pipeline.queue_manager import get_queue_stats
from app.pipeline.stability import (
    pipeline_circuit_breaker,
    check_external_services_health,
    get_pipeline_activity_status,
    is_pipeline_stalled,
    update_pipeline_activity,
    record_pipeline_metrics,
)
from app.pipeline.hard_stop import get_stop_status, should_stop_pipeline

logger = logging.getLogger(__name__)


async def _check_worker_health() -> dict:
    """Check if Celery workers are healthy using inspect."""
    try:
        active = celery_app.control.inspect().active()
        if active is None:
            return {"workers_active": False, "active_tasks": 0, "workers": []}

        active_tasks = sum(len(tasks) for tasks in active.values())
        return {
            "workers_active": True,
            "active_tasks": active_tasks,
            "workers": list(active.keys()) if active else [],
        }
    except Exception as e:
        logger.warning(f"Failed to inspect workers: {e}")
        return {"workers_active": False, "error": str(e)}


@celery_app.task
def task_pipeline_watchdog():
    """
    ENHANCED Watchdog task for robust continuous pipeline execution.

    Key improvements over original:
    1. Circuit breaker pattern to prevent restart loops
    2. External service health checks before restart
    3. Stalled pipeline detection via heartbeat monitoring
    4. Better logging and metrics tracking
    5. Graceful handling of restart failures

    Runs every 2 minutes via Celery Beat.
    """
    async def _check():
        start_time = time.time()

        # === LẤY STOP STATUS TRƯỚC KHI QUYẾT ĐỊNH AUTO-RESTART ===
        # Đây là fix quan trọng nhất - đảm bảo không auto-restart khi user đã stop
        stop_status = get_stop_status()
        user_stopped = stop_status.get("is_stopped", False)
        stop_reason = stop_status.get("reason", "N/A")

        # === CHECK CIRCUIT BREAKER FIRST ===
        can_proceed, reason = await pipeline_circuit_breaker.can_proceed()
        if not can_proceed:
            logger.info(f"Pipeline watchdog: Circuit breaker open, skipping restart. {reason}")
            return {
                "action": "circuit_breaker_open",
                "reason": reason,
                "circuit_breaker": pipeline_circuit_breaker.get_status(),
            }

        # === NẾU USER ĐÃ STOP - KHÔNG LÀM GÌ CẢ ===
        if user_stopped:
            logger.info(f"Pipeline watchdog: User has stopped pipeline (reason: {stop_reason}) - NOT auto-restarting")
            await pipeline_circuit_breaker.record_success()
            return {
                "action": "user_stopped_no_restart",
                "reason": stop_reason,
                "stop_status": stop_status,
            }

        # === CHECK EXTERNAL SERVICES ===
        external_health = await check_external_services_health()

        # If critical services are down, don't restart - wait for recovery
        if not external_health["redis"]["healthy"]:
            logger.error("Pipeline watchdog: Redis unhealthy, waiting for recovery...")
            return {
                "action": "waiting_for_redis",
                "redis_health": external_health["redis"],
            }

        if not external_health["database"]["healthy"]:
            logger.error("Pipeline watchdog: Database unhealthy, waiting for recovery...")
            return {
                "action": "waiting_for_database",
                "database_health": external_health["database"],
            }

        async with get_db_context() as session:
            stats = await get_queue_stats(session)

            pending = stats.get("pending", 0)
            by_state = stats.get("by_state", {})

            in_progress = (
                by_state.get("researched", 0) +
                by_state.get("written", 0) +
                by_state.get("governed", 0) +
                by_state.get("approved", 0)
            )

            queued = stats.get("queued", 0)

            pipeline_info = await get_pipeline_info()
            pipeline_state = pipeline_info.get("state", PipelineState.STOPPED.value)
            is_continuous = pipeline_info.get("is_continuous", False)

            worker_health = await _check_worker_health()
            activity_status = await get_pipeline_activity_status()

            logger.info(
                f"Pipeline watchdog: state={pipeline_state}, "
                f"pending={pending}, in_progress={in_progress}, queued={queued}, "
                f"continuous={is_continuous}, workers_active={worker_health.get('workers_active')}, "
                f"heartbeat_age={activity_status.get('heartbeat_age_seconds', 'N/A')}s"
            )

            result = {
                "pipeline_state": pipeline_state,
                "pending": pending,
                "in_progress": in_progress,
                "queued": queued,
                "continuous": is_continuous,
                "worker_health": worker_health,
                "activity_status": activity_status,
                "external_health": external_health,
                "circuit_breaker": pipeline_circuit_breaker.get_status(),
            }

            # === AUTO-RESTART LOGIC ===
            # CHỈ auto-restart khi user KHÔNG stop và state = stopped + is_continuous = True

            # Case 1: Pipeline stopped but continuous mode was intended -> IMMEDIATE RESTART
            # (Chỉ khi user KHÔNG stop)
            if user_stopped:
                logger.info(f"Pipeline watchdog: User has stopped - skipping auto-restart")
                await pipeline_circuit_breaker.record_success()
                return {**result, "action": "user_stopped_skip_restart"}
            
            if pipeline_state == PipelineState.STOPPED.value and is_continuous:
                logger.warning("Pipeline watchdog: CRITICAL - continuous mode stopped unexpectedly!")
                logger.warning("Pipeline watchdog: IMMEDIATE RESTART initiated")

                try:
                    await start_pipeline(PipelineMode.CONTINUOUS)
                    task_run_pipeline_celery.delay(mode="continuous", limit=10)
                    logger.info("Pipeline watchdog: triggered continuous pipeline task")
                    await pipeline_circuit_breaker.record_success()
                    return {**result, "action": "restarted_continuous_immediate"}

                except Exception as e:
                    logger.error(f"Pipeline watchdog: FAILED to restart continuous: {e}")
                    await pipeline_circuit_breaker.record_failure(str(e))

                    # Retry immediately
                    try:
                        await start_pipeline(PipelineMode.CONTINUOUS)
                        task_run_pipeline_celery.delay(mode="continuous", limit=10)
                        logger.info("Pipeline watchdog: retry restart successful")
                        await pipeline_circuit_breaker.record_success()
                        return {**result, "action": "restarted_retry"}

                    except Exception as e2:
                        logger.error(f"Pipeline watchdog: retry restart also failed: {e2}")
                        await pipeline_circuit_breaker.record_failure(str(e2))
                        return {**result, "action": "restart_failed", "error": str(e2)}

            # Case 2: Workers not active but continuous mode is on -> Restart workers
            if is_continuous and not worker_health.get("workers_active", False):
                logger.warning("Pipeline watchdog: Workers not active but continuous mode is on!")
                try:
                    task_run_pipeline_celery.delay(mode="continuous", limit=10)
                    logger.info("Pipeline watchdog: triggered task to wake up workers")
                    await pipeline_circuit_breaker.record_success()
                    return {**result, "action": "woke_workers"}
                except Exception as e:
                    logger.error(f"Pipeline watchdog: Failed to wake workers: {e}")
                    await pipeline_circuit_breaker.record_failure(str(e))
                    return {**result, "action": "wake_failed", "error": str(e)}

            # Case 3: No active tasks, no in_progress, but continuous mode is supposed to be running
            # (Chỉ khi user KHÔNG stop)
            if not user_stopped and is_continuous and pipeline_state == PipelineState.RUNNING.value:
                heartbeat_time = activity_status.get("heartbeat_time")
                stalled, stall_reason = await is_pipeline_stalled(heartbeat_time, max_stall_seconds=300)

                if stalled:
                    logger.warning(f"Pipeline watchdog: Pipeline appears stalled. {stall_reason}")
                    try:
                        task_run_pipeline_celery.delay(mode="continuous", limit=10)
                        logger.info("Pipeline watchdog: triggered task to revive stalled pipeline")
                        await pipeline_circuit_breaker.record_success()
                        return {**result, "action": "revived_stalled_pipeline", "reason": stall_reason}
                    except Exception as e:
                        logger.error(f"Pipeline watchdog: Failed to revive stalled pipeline: {e}")
                        await pipeline_circuit_breaker.record_failure(str(e))
                        return {**result, "action": "revival_failed", "error": str(e)}

                elif worker_health.get("active_tasks", 0) == 0 and in_progress == 0:
                    logger.warning("Pipeline watchdog: Pipeline running but no active tasks")
                    task_run_pipeline_celery.delay(mode="continuous", limit=10)
                    return {**result, "action": "triggered_idle_pipeline"}

            # Case 4: Normal continuous mode - just monitoring
            if is_continuous and pipeline_state == PipelineState.RUNNING.value:
                if worker_health.get("workers_active") and worker_health.get("active_tasks", 0) > 0:
                    await pipeline_circuit_breaker.record_success()
                    return {**result, "action": "healthy"}
                return {**result, "action": "monitoring"}

            # Case 5: Pipeline stopped but there are pending articles
            # (Chỉ khi user KHÔNG stop)
            if not user_stopped and pipeline_state == PipelineState.STOPPED.value and pending > 10:
                logger.info(f"Pipeline watchdog: {pending} pending articles but pipeline stopped - restarting")
                try:
                    await start_pipeline(PipelineMode.NORMAL)
                    task_run_pipeline_celery.delay(mode="normal", limit=20)
                    await pipeline_circuit_breaker.record_success()
                    return {**result, "action": "restarted_normal_due_to_backlog"}
                except Exception as e:
                    logger.error(f"Pipeline watchdog: Failed to restart for backlog: {e}")
                    await pipeline_circuit_breaker.record_failure(str(e))
                    return {**result, "action": "backlog_restart_failed", "error": str(e)}

            await pipeline_circuit_breaker.record_success()
            return result

    return run_async(_check())


@celery_app.task
def task_pipeline_heartbeat():
    """
    ENHANCED Lightweight heartbeat task for continuous pipeline monitoring.

    Key improvements:
    1. Uses circuit breaker to prevent restart loops
    2. Checks external services before restart
    3. Better error handling and logging
    4. Updates activity timestamp for stall detection

    Runs every 1 minute via Celery Beat.
    """
    async def _heartbeat():
        start_time = time.time()

        try:
            redis = await get_redis()

            state = await redis.get(PIPELINE_STATE_KEY)
            mode = await redis.get("linew:pipeline:mode")

            is_running = state == PipelineState.RUNNING.value if state else False
            is_continuous = mode == PipelineMode.CONTINUOUS.value if mode else False

            heartbeat_key = "linew:pipeline:heartbeat"
            last_heartbeat = await redis.get(heartbeat_key)

            await update_pipeline_activity()

            # === FIX: Check user stop signal TRƯỚC KHI bất kỳ auto-restart nào ===
            stop_status = get_stop_status()
            user_stopped = stop_status.get("is_stopped", False)
            stop_reason = stop_status.get("reason", "N/A")

            # Nếu user đã stop - KHÔNG BAO GIỜ auto-restart
            if user_stopped:
                logger.info(f"PIPELINE HEARTBEAT: User has stopped (reason: {stop_reason}) - NOT auto-restarting")
                await pipeline_circuit_breaker.record_success()
                return {
                    "action": "user_stopped_no_restart",
                    "reason": stop_reason,
                    "stop_status": stop_status,
                }

            # === CHECK CIRCUIT BREAKER ===
            can_proceed, reason = await pipeline_circuit_breaker.can_proceed()

            # === CHỈ auto-restart khi user KHÔNG stop ===
            if is_continuous and not is_running:
                if not can_proceed:
                    logger.warning(f"PIPELINE HEARTBEAT: Circuit breaker open, cannot restart. {reason}")
                    return {
                        "action": "circuit_breaker_open",
                        "reason": reason,
                        "circuit_breaker": pipeline_circuit_breaker.get_status(),
                    }

                logger.warning(f"PIPELINE HEARTBEAT: Continuous mode stopped! State={state}, Mode={mode}")
                logger.warning("PIPELINE HEARTBEAT: IMMEDIATE RESTART!")

                # Check external services first
                external_health = await check_external_services_health()
                if not external_health["redis"]["healthy"]:
                    logger.error("PIPELINE HEARTBEAT: Redis unhealthy, cannot restart!")
                    return {
                        "action": "waiting_for_redis",
                        "redis_health": external_health["redis"],
                    }

                # Try to restart up to 3 times
                success = False
                for attempt in range(3):
                    try:
                        await start_pipeline(PipelineMode.CONTINUOUS)
                        task_run_pipeline_celery.delay(mode="continuous", limit=10)
                        logger.info(f"PIPELINE HEARTBEAT: Restart successful (attempt {attempt + 1})")
                        await pipeline_circuit_breaker.record_success()
                        success = True
                        return {
                            "action": "restarted",
                            "attempt": attempt + 1,
                            "state": state,
                            "mode": mode,
                            "latency_ms": (time.time() - start_time) * 1000,
                        }
                    except Exception as e:
                        logger.error(f"PIPELINE HEARTBEAT: Restart attempt {attempt + 1} failed: {e}")

                if not success:
                    logger.error("PIPELINE HEARTBEAT: All restart attempts failed!")
                    await pipeline_circuit_breaker.record_failure("All restart attempts failed")
                    return {
                        "action": "restart_failed",
                        "state": state,
                        "mode": mode,
                        "circuit_breaker": pipeline_circuit_breaker.get_status(),
                    }

            # All good - continuous mode running
            if is_continuous and is_running:
                await pipeline_circuit_breaker.record_success()
                return {
                    "action": "alive",
                    "state": state,
                    "mode": mode,
                    "heartbeat": last_heartbeat,
                    "latency_ms": (time.time() - start_time) * 1000,
                }

            return {
                "action": "ok",
                "state": state,
                "mode": mode,
            }

        except Exception as e:
            logger.error(f"PIPELINE HEARTBEAT: Error: {e}")
            await pipeline_circuit_breaker.record_failure(str(e))
            return {"action": "error", "error": str(e)}

    return run_async(_heartbeat())


# Import task_run_pipeline_celery for use in watchdog/heartbeat
from app.worker.pipeline_tasks import task_run_pipeline_celery
