"""Tests for pipeline task functions."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTaskCategorize:
    @pytest.mark.asyncio
    async def test_categorize_skips_inactive_category(self, mock_db_session):
        """Article with inactive category should be SKIPPED."""
        from app.pipeline.tasks import task_categorize

        mock_article = MagicMock()
        mock_article.id = "test-id"
        mock_article.original_title = "Test Article"

        with patch("app.pipeline.tasks.get_db_context") as mock_ctx, \
             patch("app.pipeline.tasks.categorize_article") as mock_cat, \
             patch("app.pipeline.tasks.get_active_categories") as mock_cats:

            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.execute = AsyncMock(return_value=MagicMock(scalar_one=lambda: mock_article))
            mock_cat.return_value = {"category": "sports", "confidence": 0.9}
            mock_cats.return_value = ["tech", "finance"]

            result = await task_categorize("test-id")
            assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_categorize_active_category_proceeds(self, mock_db_session):
        """Article with active category should be CATEGORIZED."""
        from app.pipeline.tasks import task_categorize

        mock_article = MagicMock()
        mock_article.state = None
        mock_article.trend_score = 0.5

        with patch("app.pipeline.tasks.get_db_context") as mock_ctx, \
             patch("app.pipeline.tasks.categorize_article") as mock_cat, \
             patch("app.pipeline.tasks.get_active_categories") as mock_cats, \
             patch("app.pipeline.tasks.calculate_priority") as mock_pri, \
             patch("app.pipeline.tasks.publish_event") as mock_pub:

            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.execute = AsyncMock(return_value=MagicMock(scalar_one=lambda: mock_article))
            mock_cat.return_value = {"category": "tech", "confidence": 0.95}
            mock_cats.return_value = ["tech", "finance"]
            mock_pri.return_value = 0.8
            mock_pub.return_value = None

            result = await task_categorize("test-id")
            assert result["status"] == "categorized"
            assert result["category"] == "tech"


class TestRunAsyncSafety:
    def test_run_async_does_not_leak_loops(self):
        """Verify run_async uses threading.local, not global dict."""
        from app.worker.celery_app import _thread_local
        import threading
        assert isinstance(_thread_local, threading.local)

    def test_multiple_calls_reuse_loop(self):
        """Same thread should reuse the same event loop."""
        import asyncio
        from app.worker.celery_app import run_async

        async def get_loop():
            return asyncio.get_event_loop()

        loop1 = run_async(get_loop())
        loop2 = run_async(get_loop())
        assert loop1 is loop2  # Same loop reused
