"""
Celery tasks for archiving - PostgreSQL to SQLite.
"""
import asyncio
import logging
from datetime import date, timedelta

from celery import shared_task

from app.archive.service import ArchiveService
from app.archive.cleanup import PostgresCleanup

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def task_daily_archive(self):
    """
    Daily incremental archive - archive yesterday's data.
    Runs at 2:00 AM every day.
    """
    try:
        service = ArchiveService()
        results = run_async(service.archive_daily_incremental())
        logger.info(f"Daily archive completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Daily archive failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def task_monthly_archive(self):
    """
    Full monthly archive - archive previous month's data.
    Runs at 2:00 AM on the 1st of every month.
    """
    try:
        # Archive previous month
        today = date.today()
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1

        service = ArchiveService()
        results = run_async(service.archive_month(year, month))
        logger.info(f"Monthly archive {year}-{month:02d} completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Monthly archive failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def task_cleanup_postgres(self):
    """
    Clean up old data from PostgreSQL after archiving.
    Runs at 3:00 AM on the 1st of every month (after monthly archive).
    """
    try:
        cleanup = PostgresCleanup()
        results = run_async(cleanup.run_all_cleanup())
        logger.info(f"PostgreSQL cleanup completed: {results}")
        return results
    except Exception as e:
        logger.error(f"PostgreSQL cleanup failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def task_archive_specific_month(self, year: int, month: int):
    """
    Archive specific month (for manual triggering).
    """
    try:
        service = ArchiveService()
        results = run_async(service.archive_month(year, month))
        logger.info(f"Archive {year}-{month:02d} completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Archive {year}-{month:02d} failed: {e}")
        raise self.retry(exc=e)
