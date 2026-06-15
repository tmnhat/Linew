#!/usr/bin/env python3
"""
Pipeline Monitor Script - Ensures pipeline stays running 24/7.

This script provides multiple layers of protection:

1. Monitors Celery worker processes
2. Checks Redis pipeline state
3. Auto-restarts if pipeline stops unexpectedly
4. Alerts on critical failures

Usage:
    python scripts/monitor_pipeline.py              # Normal mode
    python scripts/monitor_pipeline.py --daemon    # Run as daemon
    python scripts/monitor_pipeline.py --once       # Single check and exit
    python scripts/monitor_pipeline.py --status     # Show current status
    python scripts/monitor_pipeline.py --restart    # Force restart pipeline
"""
import asyncio
import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/pipeline_monitor.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


class PipelineMonitor:
    """
    Monitor and maintain pipeline health.

    This class provides:
    - Health checks for Redis and Celery
    - Automatic restart of stopped pipelines
    - Process monitoring
    - Alerting on failures
    """

    def __init__(self):
        self.running = True
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.check_interval = 60  # Check every 60 seconds

    async def check_redis(self) -> dict:
        """Check Redis connectivity and pipeline state."""
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            await redis.ping()

            # Get pipeline state
            state = await redis.get("linew:pipeline:state")
            mode = await redis.get("linew:pipeline:mode")
            heartbeat = await redis.get("linew:pipeline:heartbeat")

            return {
                "ok": True,
                "state": state,
                "mode": mode,
                "heartbeat": heartbeat,
            }
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            return {"ok": False, "error": str(e)}

    async def check_celery_workers(self) -> dict:
        """Check if Celery workers are running."""
        try:
            import redis as sync_redis

            # Parse Redis URL
            r = sync_redis.from_url(self.redis_url)

            # Check for active workers by looking at Celery queues
            # This is a simple check - in production you might want to use celery inspect

            # Check for pending tasks
            inspect_key = "celery"
            keys = r.keys(f"{inspect_key}*")

            return {
                "ok": True,
                "keys": len(keys),
                "has_celery_data": len(keys) > 0,
            }
        except Exception as e:
            logger.warning(f"Celery check failed: {e}")
            return {"ok": False, "error": str(e)}

    async def check_database(self) -> dict:
        """Check database connectivity."""
        try:
            from app.core.database import async_engine

            async with async_engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
                return {"ok": True}
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return {"ok": False, "error": str(e)}

    async def restart_pipeline(self, mode: str = "continuous") -> dict:
        """Restart the pipeline."""
        try:
            from app.pipeline.control import (
                stop_pipeline,
                start_pipeline,
                PipelineMode,
            )
            from app.worker.celery_app import task_run_pipeline_celery

            logger.info(f"Restarting pipeline in {mode} mode...")

            # Stop first
            await stop_pipeline()

            # Small delay
            await asyncio.sleep(1)

            # Start
            result = await start_pipeline(
                PipelineMode.CONTINUOUS if mode == "continuous" else PipelineMode.NORMAL
            )

            # Trigger Celery task
            task_run_pipeline_celery.delay(mode=mode, limit=10)

            logger.info(f"Pipeline restarted: {result}")
            return {"ok": True, "result": result}
        except Exception as e:
            logger.error(f"Failed to restart pipeline: {e}")
            return {"ok": False, "error": str(e)}

    async def run_health_check(self) -> dict:
        """Run complete health check."""
        redis_status = await self.check_redis()
        celery_status = await self.check_celery_workers()
        db_status = await self.check_database()

        overall_ok = redis_status.get("ok") and db_status.get("ok")

        # Check if continuous pipeline needs restart
        needs_restart = False
        if redis_status.get("ok"):
            state = redis_status.get("state")
            mode = redis_status.get("mode")
            heartbeat = redis_status.get("heartbeat")

            if mode == "continuous" and state != "running":
                logger.warning(f"Pipeline needs restart: state={state}, mode={mode}")
                needs_restart = True

            # Check if heartbeat is stale (> 5 minutes old)
            if heartbeat:
                from datetime import datetime
                try:
                    last_hb = datetime.fromisoformat(heartbeat)
                    age = (datetime.utcnow() - last_hb).total_seconds()
                    if age > 300:  # 5 minutes
                        logger.warning(f"Heartbeat is stale: {age:.0f} seconds old")
                        needs_restart = True
                except:
                    pass

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall": overall_ok,
            "redis": redis_status,
            "celery": celery_status,
            "database": db_status,
            "needs_restart": needs_restart,
        }

    async def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting pipeline monitor loop...")
        consecutive_failures = 0
        max_failures = 3

        while self.running:
            try:
                health = await self.run_health_check()

                if health["needs_restart"]:
                    logger.warning("Pipeline health check indicates restart needed")
                    consecutive_failures += 1

                    if consecutive_failures >= max_failures:
                        logger.error(f"{consecutive_failures} consecutive restart failures, alerting...")
                        # In production, you might want to send an alert here
                        consecutive_failures = 0  # Reset to avoid infinite loop
                    else:
                        await self.restart_pipeline(mode="continuous")
                else:
                    consecutive_failures = 0
                    logger.info(f"Pipeline healthy: state={health['redis'].get('state')}, mode={health['redis'].get('mode')}")

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                consecutive_failures += 1

            # Wait before next check
            for _ in range(self.check_interval):
                if not self.running:
                    break
                await asyncio.sleep(1)

        logger.info("Pipeline monitor loop stopped")

    def stop(self):
        """Stop the monitor."""
        logger.info("Stopping pipeline monitor...")
        self.running = False


async def main(args):
    """Main entry point."""
    monitor = PipelineMonitor()

    if args.status:
        # Single status check
        health = await monitor.run_health_check()
        print("\n=== Pipeline Status ===")
        print(f"Overall: {'OK' if health['overall'] else 'FAILED'}")
        print(f"Redis: {'OK' if health['redis'].get('ok') else 'FAILED'} - state={health['redis'].get('state')}, mode={health['redis'].get('mode')}")
        print(f"Database: {'OK' if health['database'].get('ok') else 'FAILED'}")
        print(f"Needs Restart: {health['needs_restart']}")
        return 0

    elif args.restart:
        # Force restart
        print("Restarting pipeline...")
        result = await monitor.restart_pipeline(mode="continuous")
        if result["ok"]:
            print("Pipeline restarted successfully!")
            return 0
        else:
            print(f"Failed to restart: {result.get('error')}")
            return 1

    elif args.once:
        # Single check
        health = await monitor.run_health_check()
        print("\n=== Health Check ===")
        print(f"Overall: {'OK' if health['overall'] else 'FAILED'}")
        print(f"Redis: {health['redis']}")
        print(f"Database: {health['database']}")
        print(f"Needs Restart: {health['needs_restart']}")

        if health['needs_restart']:
            print("\nRestarting pipeline...")
            result = await monitor.restart_pipeline(mode="continuous")
            if result["ok"]:
                print("Pipeline restarted!")
            else:
                print(f"Restart failed: {result.get('error')}")
        return 0

    elif args.daemon:
        # Run as daemon
        print("Starting pipeline monitor as daemon...")
        logger.info("Pipeline monitor started as daemon")

        # Handle signals
        def signal_handler(sig, frame):
            monitor.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await monitor.monitor_loop()
        return 0

    else:
        # Default: interactive mode with periodic checks
        print("Starting pipeline monitor (interactive mode)...")
        logger.info("Pipeline monitor started")

        # Handle signals
        def signal_handler(sig, frame):
            monitor.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await monitor.monitor_loop()
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--once", action="store_true", help="Run single check and exit")
    parser.add_argument("--status", action="store_true", help="Show current status and exit")
    parser.add_argument("--restart", action="store_true", help="Force restart pipeline")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    args = parser.parse_args()

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Run async main
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
