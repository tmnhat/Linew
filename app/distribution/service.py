"""
Distribution orchestrator - coordinates posting to all enabled channels.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db_context
from app.core.locks import DistributionLock
from app.models.article import Article, ArticleState
from app.models.distribution import DistributionLog
from app.models.setting import Setting

logger = logging.getLogger(__name__)


class DistributionService:
    """
    Orchestrates article distribution to all enabled channels.

    Each channel runs independently - a failure in one channel
    does not affect others.
    """

    def __init__(self):
        self.settings = get_settings()

    async def _is_channel_enabled(self, channel: str) -> bool:
        """Check if a distribution channel is enabled in settings."""
        # Check from config first
        channel_enabled_map = {
            "telegram": self.settings.telegram_channel_enabled,
            "facebook": self.settings.facebook_enabled,
            "twitter": self.settings.twitter_enabled,
            "newsletter": self.settings.newsletter_enabled,
            "medium": False,  # Not implemented yet, always false
        }

        # Check database settings (overrides config if set)
        async with get_db_context() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == "distribution")
            )
            setting = result.scalar_one_or_none()
            if setting and setting.value:
                db_value = setting.value.get(f"{channel}_enabled")
                if db_value is not None:
                    return db_value

        return channel_enabled_map.get(channel, False)

    async def _is_channel_paused(self, channel: str) -> bool:
        """Check if a distribution channel is paused."""
        async with get_db_context() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == "distribution")
            )
            setting = result.scalar_one_or_none()
            if setting and setting.value:
                return setting.value.get(f"{channel}_paused", False)
        return False

    async def _distribute_to_channel_with_lock(
        self,
        article,
        article_id: str,
        channel: str,
        post_func,
    ) -> dict:
        """
        Distribute to a single channel with idempotency lock.
        
        Uses Redis SETNX to ensure only one distribution per article/channel.
        Prevents race conditions where multiple workers try to distribute
        the same article to the same channel simultaneously.
        
        Args:
            article: Article object
            article_id: UUID of the article
            channel: Channel name (telegram, twitter, etc.)
            post_func: Async function to call for posting
        
        Returns:
            dict with distribution result
        """
        # Check if already distributed (fast path - no lock)
        if await self._is_already_distributed(article_id, channel):
            return {
                "status": "skipped",
                "reason": "already_distributed",
            }
        
        # Acquire idempotency lock
        dist_lock = DistributionLock(article_id, channel, ttl=300)
        
        if not dist_lock.try_acquire():
            return {
                "status": "skipped",
                "reason": "distribution_in_progress",
            }
        
        try:
            # Do the distribution
            result = await post_func(article)
            
            # Save to DB
            await self._save_distribution_log(
                article_id,
                channel,
                result.get("status", "failed"),
                result.get("external_id"),
                result.get("external_url"),
                result.get("error"),
            )
            
            # Mark as complete
            dist_lock.mark_complete(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Distribution failed for {channel}/{article_id[:8]}...: {e}")
            
            # Save failure to DB
            await self._save_distribution_log(
                article_id,
                channel,
                "failed",
                error=str(e),
            )
            
            # Mark as failed (releases lock for retry)
            dist_lock.mark_failed(str(e))
            
            return {
                "status": "failed",
                "error": str(e),
            }

    async def _is_already_distributed(self, article_id: str, channel: str) -> bool:
        """Check if article was already distributed to this channel (from DB)."""
        async with get_db_context() as session:
            result = await session.execute(
                select(DistributionLog)
                .where(DistributionLog.article_id == article_id)
                .where(DistributionLog.channel == channel)
                .where(DistributionLog.status == "success")
            )
            return result.scalar_one_or_none() is not None

    async def _save_distribution_log(
        self,
        article_id: str,
        channel: str,
        status: str,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Save distribution result to database."""
        async with get_db_context() as session:
            log = DistributionLog(
                article_id=article_id,
                channel=channel,
                status=status,
                external_id=external_id,
                external_url=external_url,
                error=error,
            )
            session.add(log)
            await session.commit()

    async def distribute_article(self, article_id: str) -> dict:
        """
        Distribute an article to all enabled channels.

        This is called after an article is successfully published.
        Each channel is handled independently.

        FIX: Added idempotency check using Redis SETNX - skip channels that were already
        successfully distributed to prevent duplicate posts.

        Args:
            article_id: UUID of the article to distribute

        Returns:
            dict with distribution results per channel
        """
        # Get article
        async with get_db_context() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()

            if not article:
                logger.error(f"Article {article_id} not found for distribution")
                return {"error": "Article not found"}

            if article.state != ArticleState.PUBLISHED.value:
                logger.warning(f"Article {article_id} is not published (state: {article.state})")
                return {"error": "Article not published"}

        logger.info(f"Starting distribution for article: {article.meta_title[:50]}...")

        results = {}

        # Get distribution settings from database
        async with get_db_context() as session:
            dist_result = await session.execute(
                select(Setting).where(Setting.key == "distribution")
            )
            dist_setting = dist_result.scalar_one_or_none()
            distribution_settings = dist_setting.value if dist_setting else {}

        # Distribute to Telegram with idempotency lock
        if await self._is_channel_enabled("telegram"):
            try:
                from app.distribution.telegram_channel import post_to_channel
                results["telegram"] = await self._distribute_to_channel_with_lock(
                    article,
                    article_id,
                    "telegram",
                    post_to_channel,
                )
            except Exception as e:
                logger.error(f"Telegram distribution failed: {e}")
                results["telegram"] = {"status": "failed", "error": str(e)}
        else:
            logger.info("Telegram channel disabled, skipping")
            results["telegram"] = {"status": "skipped", "reason": "disabled"}

        # Facebook Distribution - Handled by scheduled task (task_facebook_scheduled)
        # Facebook uses the scheduled task approach for no-link posting
        # See app/distribution/tasks.py::task_facebook_scheduled
        results["facebook"] = {"status": "skipped", "reason": "scheduled_task_only"}

        # Distribute to Twitter with idempotency lock
        if await self._is_channel_enabled("twitter"):
            if await self._is_channel_paused("twitter"):
                logger.info("Twitter paused, skipping distribution")
                results["twitter"] = {"status": "skipped", "reason": "paused"}
            else:
                try:
                    from app.distribution.twitter import post_to_twitter
                    results["twitter"] = await self._distribute_to_channel_with_lock(
                        article,
                        article_id,
                        "twitter",
                        post_to_twitter,
                    )
                except Exception as e:
                    logger.error(f"Twitter distribution failed: {e}")
                    results["twitter"] = {"status": "failed", "error": str(e)}
        else:
            logger.info("Twitter disabled, skipping")
            results["twitter"] = {"status": "skipped", "reason": "disabled"}

        # Add to newsletter queue (for daily digest)
        # Note: Newsletter is not posted immediately, it's queued for the daily digest
        if await self._is_channel_enabled("newsletter"):
            logger.info("Newsletter: article added to queue for daily digest")
            results["newsletter"] = {"status": "queued", "reason": "daily_digest"}

        logger.info(f"Distribution completed for article {article_id}")
        return results

    async def get_distribution_stats(self, db: AsyncSession, days: int = 7) -> dict:
        """Get distribution statistics."""
        from datetime import datetime, timedelta
        from sqlalchemy import func

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count by channel and status
        stmt = (
            select(
                DistributionLog.channel,
                DistributionLog.status,
                func.count(DistributionLog.id).label("count"),
            )
            .where(DistributionLog.created_at >= cutoff)
            .group_by(DistributionLog.channel, DistributionLog.status)
        )
        result = await db.execute(stmt)
        rows = result.all()

        stats = {}
        for channel, status, count in rows:
            if channel not in stats:
                stats[channel] = {"total": 0, "success": 0, "failed": 0, "pending": 0}
            stats[channel]["total"] += count
            stats[channel][status] = count

        return stats

    async def pause_channel(self, channel: str) -> bool:
        """Pause a distribution channel."""
        valid_channels = ["facebook", "twitter"]
        if channel not in valid_channels:
            raise ValueError(f"Invalid channel. Must be one of: {valid_channels}")

        async with get_db_context() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == "distribution")
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value[f"{channel}_paused"] = True
            else:
                setting = Setting(
                    key="distribution",
                    value={f"{channel}_paused": True},
                )
                session.add(setting)

            await session.commit()
            logger.info(f"Channel '{channel}' has been paused")
            return True

    async def resume_channel(self, channel: str) -> bool:
        """Resume a paused distribution channel."""
        valid_channels = ["facebook", "twitter"]
        if channel not in valid_channels:
            raise ValueError(f"Invalid channel. Must be one of: {valid_channels}")

        async with get_db_context() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == "distribution")
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value[f"{channel}_paused"] = False
            else:
                setting = Setting(
                    key="distribution",
                    value={f"{channel}_paused": False},
                )
                session.add(setting)

            await session.commit()
            logger.info(f"Channel '{channel}' has been resumed")
            return True

    async def get_channel_status(self) -> dict:
        """Get the pause/resume status of all channels."""
        async with get_db_context() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == "distribution")
            )
            setting = result.scalar_one_or_none()

            if setting and setting.value:
                return {
                    "facebook_paused": setting.value.get("facebook_paused", False),
                    "twitter_paused": setting.value.get("twitter_paused", False),
                }

        return {
            "facebook_paused": False,
            "twitter_paused": False,
        }
