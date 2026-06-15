"""
Storage, Archive & Backup API routes.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.article import Article, ArticleState
from app.models.raw_signal import RawSignal
from app.models.prediction_models import PredictionFinal, MarketResearch
from app.archive.service import ArchiveService
from app.archive.cleanup import PostgresCleanup
from app.backup.gdrive_service import GoogleDriveBackup

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/stats")
async def get_storage_stats(db: AsyncSession = Depends(get_db)):
    """
    Get storage statistics including PostgreSQL counts and archive stats.
    """
    # PostgreSQL counts
    stats = {
        "postgresql": {},
        "archive": {},
        "gdrive": {},
        "last_backup": None,
        "last_archive": None,
    }

    # Raw signals count
    result = await db.execute(select(func.count()).select_from(RawSignal))
    stats["postgresql"]["raw_signals_count"] = result.scalar() or 0

    # Raw signals archived
    result = await db.execute(
        select(func.count()).select_from(RawSignal).where(RawSignal.is_archived == True)
    )
    stats["postgresql"]["raw_signals_archived"] = result.scalar() or 0

    # Raw signals pending (not archived)
    result = await db.execute(
        select(func.count()).select_from(RawSignal).where(RawSignal.is_archived == False)
    )
    stats["postgresql"]["raw_signals_pending"] = result.scalar() or 0

    # Articles by state
    result = await db.execute(select(func.count()).select_from(Article))
    stats["postgresql"]["articles_total"] = result.scalar() or 0

    result = await db.execute(
        select(func.count()).select_from(Article).where(Article.state == ArticleState.PUBLISHED.value)
    )
    stats["postgresql"]["articles_published"] = result.scalar() or 0

    # Predictions count
    result = await db.execute(select(func.count()).select_from(PredictionFinal))
    stats["postgresql"]["predictions_count"] = result.scalar() or 0

    # Market research count
    result = await db.execute(select(func.count()).select_from(MarketResearch))
    stats["postgresql"]["market_research_count"] = result.scalar() or 0

    # Archive stats
    archive_service = ArchiveService()
    stats["archive"] = archive_service.get_stats()

    # Google Drive stats
    gdrive = GoogleDriveBackup()
    stats["gdrive"] = gdrive.get_drive_usage()

    return stats


@router.post("/backup")
async def trigger_backup(background_tasks: BackgroundTasks):
    """
    Trigger a manual backup.
    Returns task info for tracking.
    """
    from app.backup.tasks import task_daily_backup

    # Queue the backup task
    task = task_daily_backup.delay()
    logger.info(f"Manual backup triggered: {task.id}")

    return {
        "task_id": task.id,
        "message": "Backup task queued",
        "status": "pending",
    }


@router.post("/archive")
async def trigger_archive():
    """
    Trigger a manual archive (daily incremental).
    Returns task info for tracking.
    """
    from app.archive.tasks import task_daily_archive

    # Queue the archive task
    task = task_daily_archive.delay()
    logger.info(f"Manual archive triggered: {task.id}")

    return {
        "task_id": task.id,
        "message": "Archive task queued",
        "status": "pending",
    }


@router.post("/archive/{year}/{month}")
async def trigger_monthly_archive(year: int, month: int):
    """
    Trigger archive for a specific month.
    """
    from app.archive.tasks import task_archive_specific_month

    # Validate month
    if month < 1 or month > 12:
        return {"error": "Invalid month (1-12)"}

    task = task_archive_specific_month.delay(year, month)
    logger.info(f"Archive {year}-{month:02d} triggered: {task.id}")

    return {
        "task_id": task.id,
        "message": f"Archive task for {year}-{month:02d} queued",
        "status": "pending",
    }


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of a background task.
    """
    from app.backup.tasks import task_daily_backup

    # Get task result
    task = task_daily_backup.AsyncResult(task_id)

    if task.ready():
        if task.successful():
            return {
                "task_id": task_id,
                "status": "completed",
                "result": task.result,
            }
        else:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(task.info),
            }
    else:
        return {
            "task_id": task_id,
            "status": "pending",
        }


@router.get("/cleanup/preview")
async def preview_cleanup(db: AsyncSession = Depends(get_db)):
    """
    Preview what would be cleaned up (without actually deleting).
    """
    cleanup = PostgresCleanup()
    counts = await cleanup.get_counts(db)

    return {
        "current_counts": counts,
        "would_delete": {
            "raw_signals_older_than_60_days": "run cleanup to see actual count",
            "articles_non_published_older_than_30_days": "run cleanup to see actual count",
            "predictions_older_than_90_days": "run cleanup to see actual count",
            "publish_logs_older_than_90_days": "run cleanup to see actual count",
        },
        "never_deletes": [
            "Articles in PUBLISHED state (kept forever in PostgreSQL)",
            "Articles newer than retention period",
            "Any data that hasn't been archived",
        ],
    }


@router.post("/cleanup")
async def run_cleanup():
    """
    Run PostgreSQL cleanup manually.
    """
    from app.archive.tasks import task_cleanup_postgres

    task = task_cleanup_postgres.delay()
    logger.info(f"Manual cleanup triggered: {task.id}")

    return {
        "task_id": task.id,
        "message": "Cleanup task queued",
        "status": "pending",
    }
