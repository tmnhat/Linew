"""
Archive Service - orchestrates PostgreSQL to SQLite archiving.
Runs daily incremental and monthly full archive.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_signal import RawSignal
from app.models.article import Article
from app.models.prediction_models import PredictionFinal, MarketResearch
from app.archive.sqlite_writer import SQLiteArchiveWriter
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


class ArchiveService:
    """Orchestrates archiving from PostgreSQL to SQLite."""

    def __init__(self, base_dir: str = "/data/archive"):
        self.writer = SQLiteArchiveWriter(base_dir=base_dir)

    async def archive_signals(
        self,
        session: AsyncSession,
        year: int,
        month: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Archive raw_signals for date range."""
        stmt = select(RawSignal).where(
            RawSignal.created_at >= datetime.combine(start_date, datetime.min.time()),
            RawSignal.created_at < datetime.combine(end_date, datetime.min.time()),
            RawSignal.is_archived == False,
        )
        result = await session.execute(stmt)
        signals = result.scalars().all()

        if not signals:
            return 0

        count = self.writer.write_signals(year, month, signals)

        # Mark as archived
        signal_ids = [s.id for s in signals]
        await session.execute(
            update(RawSignal)
            .where(RawSignal.id.in_(signal_ids))
            .values(is_archived=True, archived_at=datetime.utcnow())
        )
        await session.commit()

        logger.info(f"Archived {count} signals for {year}-{month:02d}")
        return count

    async def archive_articles(
        self,
        session: AsyncSession,
        year: int,
        month: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Archive ALL articles for date range - includes SKIPPED, FAILED, etc."""
        stmt = select(Article).where(
            Article.created_at >= datetime.combine(start_date, datetime.min.time()),
            Article.created_at < datetime.combine(end_date, datetime.min.time()),
        )
        result = await session.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            return 0

        count = self.writer.write_articles(year, month, articles)
        logger.info(f"Archived {count} articles for {year}-{month:02d}")
        return count

    async def archive_predictions(
        self,
        session: AsyncSession,
        year: int,
        month: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Archive predictions for date range."""
        stmt = select(PredictionFinal).where(
            PredictionFinal.generated_at >= datetime.combine(start_date, datetime.min.time()),
            PredictionFinal.generated_at < datetime.combine(end_date, datetime.min.time()),
        )
        result = await session.execute(stmt)
        predictions = result.scalars().all()

        if not predictions:
            return 0

        count = self.writer.write_predictions(year, month, predictions)
        logger.info(f"Archived {count} predictions for {year}-{month:02d}")
        return count

    async def archive_market_research(
        self,
        session: AsyncSession,
        year: int,
        month: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Archive market research for date range."""
        stmt = select(MarketResearch).where(
            MarketResearch.generated_at >= datetime.combine(start_date, datetime.min.time()),
            MarketResearch.generated_at < datetime.combine(end_date, datetime.min.time()),
        )
        result = await session.execute(stmt)
        research = result.scalars().all()

        if not research:
            return 0

        count = self.writer.write_market_research(year, month, research)
        logger.info(f"Archived {count} market research for {year}-{month:02d}")
        return count

    async def archive_month(self, year: int, month: int) -> dict:
        """
        Full archive for a specific month.
        Archive all data from that month to SQLite.
        """
        start_date = date(year, month, 1)
        # First day of next month
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        results = {}
        async with async_session_maker() as session:
            # Archive raw_signals
            results["signals"] = await self.archive_signals(
                session, year, month, start_date, end_date
            )
            # Archive articles
            results["articles"] = await self.archive_articles(
                session, year, month, start_date, end_date
            )
            # Archive predictions
            results["predictions"] = await self.archive_predictions(
                session, year, month, start_date, end_date
            )
            # Archive market research
            results["market_research"] = await self.archive_market_research(
                session, year, month, start_date, end_date
            )

        logger.info(f"Monthly archive {year}-{month:02d} completed: {results}")
        return results

    async def archive_daily_incremental(self) -> dict:
        """
        Daily incremental archive - archive yesterday's data.
        Supplements monthly archive in case it hasn't run.
        """
        yesterday = date.today() - timedelta(days=1)
        year, month = yesterday.year, yesterday.month
        start_date = yesterday
        end_date = date.today()

        results = {}
        async with async_session_maker() as session:
            results["signals"] = await self.archive_signals(
                session, year, month, start_date, end_date
            )
            results["articles"] = await self.archive_articles(
                session, year, month, start_date, end_date
            )
            results["predictions"] = await self.archive_predictions(
                session, year, month, start_date, end_date
            )
            results["market_research"] = await self.archive_market_research(
                session, year, month, start_date, end_date
            )

        logger.info(f"Daily incremental archive completed: {results}")
        return results

    def get_stats(self) -> dict:
        """Return archive statistics."""
        return self.writer.get_archive_stats()
