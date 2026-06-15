"""
Health check API route.
"""
import logging
import time
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["system"])

_start_time = time.time()

# Thread pool for sync operations
_executor = ThreadPoolExecutor(max_workers=2)


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: int
    checks: dict
    timestamp: str


class CircuitBreakerStatus(BaseModel):
    is_open: bool
    failures: int
    failure_threshold: int
    last_failure_time: str | None


async def _check_database_async() -> tuple[bool, dict]:
    """Check database connection asynchronously."""
    try:
        from app.core.database import async_engine
        async with async_engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        return True, {}
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False, {"error": str(e)[:100]}


async def _check_redis_async() -> tuple[bool, dict]:
    """Check Redis connection asynchronously."""
    try:
        from app.core.redis import get_redis
        client = await get_redis()
        await client.ping()
        return True, {}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False, {"error": str(e)[:100]}


async def _check_wordpress_async() -> tuple[bool, str | dict]:
    """Check WordPress connection asynchronously (runs in thread pool with timeout)."""
    loop = asyncio.get_event_loop()
    try:
        # Add 5 second timeout for WordPress check
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                _test_wordpress_sync
            ),
            timeout=5.0
        )
        return True, result
    except asyncio.TimeoutError:
        logger.warning("WordPress health check timed out after 5s")
        return False, {"error": "Connection timeout (5s)"}
    except Exception as e:
        logger.warning(f"WordPress health check failed: {e}")
        return False, {"error": str(e)[:100]}


def _test_wordpress_sync() -> dict:
    """Test WordPress connection synchronously (for thread pool)."""
    try:
        from app.publisher.wordpress import get_wordpress_client
        client = get_wordpress_client()
        result = client.test_connection()
        return result
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.get("", response_model=HealthResponse)
async def health_check():
    """Check system health - optimized with parallel checks."""
    status = "ok"
    checks = {}

    # Run all checks in parallel for better performance
    db_task = _check_database_async()
    redis_task = _check_redis_async()
    wp_task = _check_wordpress_async()

    db_ok, db_info = await db_task
    redis_ok, redis_info = await redis_task
    wp_ok, wp_info = await wp_task

    checks["database"] = db_ok
    if db_info:
        checks["database_info"] = db_info

    checks["redis"] = redis_ok
    if redis_info:
        checks["redis_info"] = redis_info

    if isinstance(wp_info, dict):
        checks["wordpress"] = wp_info.get("connected", False)
        if not wp_info.get("connected"):
            checks["wordpress_error"] = wp_info.get("error", "Unknown error")
        if wp_info.get("password_format"):
            checks["wordpress_password"] = wp_info.get("password_format")
        if wp_info.get("password_hint"):
            checks["wordpress_hint"] = wp_info.get("password_hint")
    else:
        checks["wordpress"] = "not_installed"

    # Determine overall status
    if not db_ok or not redis_ok:
        status = "degraded"
    elif not checks.get("wordpress"):
        status = "degraded"

    uptime = int(time.time() - _start_time)

    return HealthResponse(
        status=status,
        version="1.0.0",
        uptime_seconds=uptime,
        checks=checks,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/circuit-breaker", response_model=CircuitBreakerStatus)
async def get_circuit_breaker_status():
    """Get AI Gateway circuit breaker status."""
    from app.core.ai_gateway import circuit_breaker
    
    return CircuitBreakerStatus(
        is_open=circuit_breaker.is_open,
        failures=circuit_breaker.failures,
        failure_threshold=circuit_breaker.failure_threshold,
        last_failure_time=datetime.fromtimestamp(circuit_breaker.last_failure_time).isoformat() 
            if circuit_breaker.last_failure_time else None,
    )


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Reset AI Gateway circuit breaker."""
    from app.core.ai_gateway import circuit_breaker

    circuit_breaker.is_open = False
    circuit_breaker.failures = 0
    circuit_breaker.last_failure_time = None

    return {
        "message": "Circuit breaker reset successfully",
        "is_open": False,
        "failures": 0,
    }


@router.get("/ping")
async def health_ping():
    """
    Lightweight health check for dashboard - no WordPress check.
    Returns quickly without external service dependencies.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/pipeline")
async def pipeline_health():
    """
    Detailed pipeline health check for monitoring.
    Returns comprehensive information about pipeline status.
    """
    from app.pipeline.control import get_pipeline_info, get_pipeline_stats
    from app.pipeline.stability import (
        pipeline_circuit_breaker,
        get_pipeline_activity_status,
        get_pipeline_metrics,
        check_external_services_health,
    )

    # Get all status in parallel
    pipeline_info = await get_pipeline_info()
    pipeline_stats = await get_pipeline_stats()
    activity_status = await get_pipeline_activity_status()
    pipeline_metrics = await get_pipeline_metrics()
    circuit_status = pipeline_circuit_breaker.get_status()
    external_health = await check_external_services_health()

    # Determine overall health
    is_healthy = True
    health_issues = []

    # Check circuit breaker
    if circuit_status["is_open"]:
        is_healthy = False
        health_issues.append("Circuit breaker is OPEN - too many restart failures")

    # Check external services
    if not external_health["redis"]["healthy"]:
        is_healthy = False
        health_issues.append("Redis is unhealthy")

    if not external_health["database"]["healthy"]:
        is_healthy = False
        health_issues.append("Database is unhealthy")

    # Check heartbeat age
    heartbeat_age = activity_status.get("heartbeat_age_seconds")
    if heartbeat_age and heartbeat_age > 300:  # 5 minutes
        is_healthy = False
        health_issues.append(f"Heartbeat stale ({heartbeat_age:.0f}s old)")

    # Determine status
    if not is_healthy:
        status = "unhealthy"
    elif pipeline_info.get("state") == "running":
        status = "healthy"
    else:
        status = "stopped"

    return {
        "status": status,
        "health_issues": health_issues,
        "timestamp": datetime.utcnow().isoformat(),
        "pipeline": {
            "state": pipeline_info.get("state"),
            "mode": pipeline_info.get("mode"),
            "is_running": pipeline_info.get("is_running"),
            "is_continuous": pipeline_info.get("is_continuous"),
            "started_at": pipeline_info.get("started_at"),
            "has_lock": pipeline_info.get("has_lock"),
        },
        "circuit_breaker": circuit_status,
        "activity": {
            "heartbeat_age_seconds": heartbeat_age,
            "activity_age_seconds": activity_status.get("activity_age_seconds"),
            "heartbeat_time": activity_status.get("heartbeat_time").isoformat() if activity_status.get("heartbeat_time") else None,
        },
        "external_services": external_health,
        "metrics": pipeline_metrics,
        "stats": pipeline_stats,
    }


@router.get("/pipeline/circuit-breaker")
async def get_pipeline_circuit_breaker():
    """Get pipeline circuit breaker status."""
    from app.pipeline.stability import pipeline_circuit_breaker

    return pipeline_circuit_breaker.get_status()


@router.post("/pipeline/circuit-breaker/reset")
async def reset_pipeline_circuit_breaker():
    """Reset pipeline circuit breaker (manual intervention)."""
    from app.pipeline.stability import pipeline_circuit_breaker

    pipeline_circuit_breaker._state.consecutive_failures = 0
    pipeline_circuit_breaker._state.is_open = False
    pipeline_circuit_breaker._state.last_failure_time = None

    logger.warning("Pipeline circuit breaker manually reset via API")

    return {
        "message": "Pipeline circuit breaker reset successfully",
        "status": pipeline_circuit_breaker.get_status(),
    }
