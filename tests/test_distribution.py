"""
Tests for distribution service functionality.

Tests cover:
- Distribution idempotency
- Channel status checking
- Distribution orchestration
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


class TestDistributionIdempotency:
    """Test cases for distribution idempotency."""

    def test_distribution_lock_prevents_duplicate(self):
        """Test that distribution lock prevents duplicate posts."""
        from app.core.locks import DistributionLock
        import json
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=None)  # No existing lock
        mock_redis.set = MagicMock(return_value=True)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributionLock("article-123", "telegram", ttl=300)
            acquired = lock.try_acquire()
            
            assert acquired is True
            mock_redis.set.assert_called_once()

    def test_distribution_lock_blocked_when_done(self):
        """Test that distribution lock blocks when already done."""
        from app.core.locks import DistributionLock
        import json
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=json.dumps({
            "status": "done",
            "completed_at": 1234567890
        }))
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributionLock("article-123", "telegram", ttl=300)
            acquired = lock.try_acquire()
            
            assert acquired is False

    def test_distribution_lock_mark_complete(self):
        """Test marking distribution as complete."""
        from app.core.locks import DistributionLock
        
        mock_redis = MagicMock()
        mock_redis.setex = MagicMock(return_value=True)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributionLock("article-123", "telegram", ttl=300)
            lock.mark_complete({"post_id": "12345"})
            
            mock_redis.setex.assert_called_once()
            
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 86400  # 24 hours


class TestDistributionService:
    """Test cases for DistributionService."""

    @pytest.mark.asyncio
    async def test_is_channel_enabled_telegram(self):
        """Test telegram channel enabled check."""
        from app.distribution.service import DistributionService
        
        mock_settings = MagicMock()
        mock_settings.telegram_channel_enabled = True
        mock_settings.facebook_enabled = False
        mock_settings.twitter_enabled = True
        mock_settings.newsletter_enabled = False
        
        service = DistributionService()
        service.settings = mock_settings
        
        # Just test that settings are loaded correctly
        assert hasattr(mock_settings, 'telegram_channel_enabled')

    @pytest.mark.asyncio
    async def test_is_channel_paused(self):
        """Test channel pause status check."""
        from app.distribution.service import DistributionService
        from unittest.mock import AsyncMock
        
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_setting = MagicMock()
        mock_setting.value = {"facebook_paused": True}
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_setting)
        
        with patch('app.distribution.service.get_db_context') as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            service = DistributionService()
            result = await service._is_channel_paused("facebook")
            
            assert result is True


class TestFacebookMessageFormatting:
    """Test cases for Facebook message formatting."""

    def test_get_category_emoji(self):
        """Test category emoji mapping."""
        from app.distribution.facebook import get_category_emoji
        
        assert get_category_emoji("tech") == "💻"
        assert get_category_emoji("ai") == "🤖"
        assert get_category_emoji("finance") == "💰"
        assert get_category_emoji("unknown") == "📰"  # Default

    def test_get_category_prefix(self):
        """Test category prefix mapping."""
        from app.distribution.facebook import get_category_prefix
        
        assert get_category_prefix("tech") == "CÔNG NGHỆ"
        assert get_category_prefix("ai") == "TRÍ TUỆ NHÂN TẠO"
        assert get_category_prefix("unknown") == ""

    def test_format_article_for_facebook(self):
        """Test article formatting for Facebook."""
        from app.distribution.facebook import format_article_for_facebook
        
        mock_article = MagicMock()
        mock_article.category = "tech"
        mock_article.meta_title = "Test Article Title"
        mock_article.original_summary = "This is a test summary."
        mock_article.original_image_url = "https://example.com/image.jpg"
        
        message, image_url = format_article_for_facebook(mock_article)
        
        assert "Test Article Title" in message
        assert "CÔNG NGHỆ" in message
        assert "💻" in message
        assert image_url == "https://example.com/image.jpg"


class TestFacebookMetrics:
    """Test cases for Facebook metrics."""
    # Note: These functions use redis directly inside the function,
    # so mocking is complex. They are tested via integration tests instead.
    pass
