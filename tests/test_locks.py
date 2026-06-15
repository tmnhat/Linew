"""
Tests for distributed locking system.

Tests cover:
- Article lock acquisition and release
- Title lock acquisition and release
- Distribution idempotency locks
- Lock status checking
- Owner-based lock release
"""
import pytest
from unittest.mock import MagicMock, patch
import json


class TestDistributedLock:
    """Test cases for DistributedLock class."""

    def test_lock_key_format(self):
        """Test that lock keys are formatted correctly."""
        from app.core.locks import DistributedLock
        
        lock = DistributedLock("test-key", ttl=3600, owner_id="worker-1")
        assert lock.key == "test-key"
        assert lock.ttl == 3600
        assert lock.owner_id == "worker-1"

    def test_lock_acquire_redis_success(self):
        """Test successful Redis lock acquisition."""
        from app.core.locks import DistributedLock
        
        mock_redis = MagicMock()
        mock_redis.set = MagicMock(return_value=True)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributedLock("test-key", ttl=3600, owner_id="worker-1")
            result = lock.acquire_redis()
            
            assert result is True
            mock_redis.set.assert_called_once_with(
                "test-key",
                "worker-1",
                nx=True,
                ex=3600
            )

    def test_lock_acquire_redis_failure(self):
        """Test failed Redis lock acquisition (already locked)."""
        from app.core.locks import DistributedLock
        
        mock_redis = MagicMock()
        mock_redis.set = MagicMock(return_value=None)  # Lock already exists (nx=True returns None)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributedLock("test-key", ttl=3600, owner_id="worker-1")
            result = lock.acquire_redis()
            
            # When nx=True and key exists, set returns None (not False)
            assert result is None or result is False

    def test_lock_release_redis_success(self):
        """Test successful Redis lock release."""
        from app.core.locks import DistributedLock
        
        mock_redis = MagicMock()
        mock_redis.eval = MagicMock(return_value=1)  # Lock released
        
        lock = DistributedLock("test-key", ttl=3600, owner_id="worker-1")
        lock._redis_locked = True
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            result = lock.release_redis()
            
            assert result is True

    def test_lock_check_redis(self):
        """Test checking who holds the lock."""
        from app.core.locks import DistributedLock
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value="worker-2")
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributedLock("test-key", ttl=3600, owner_id="worker-1")
            holder = lock.check_redis()
            
            assert holder == "worker-2"


class TestArticleLock:
    """Test cases for article_lock context manager."""

    @pytest.mark.asyncio
    async def test_article_lock_acquired(self):
        """Test article lock is acquired successfully."""
        from app.core.locks import article_lock
        
        mock_redis = MagicMock()
        mock_redis.set = MagicMock(return_value=True)
        mock_redis.eval = MagicMock(return_value=1)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            async with article_lock("article-123", "worker-1") as acquired:
                assert acquired is True

    @pytest.mark.asyncio
    async def test_article_lock_already_held(self):
        """Test article lock fails when already held."""
        from app.core.locks import article_lock
        
        mock_redis = MagicMock()
        mock_redis.set = MagicMock(return_value=None)  # Lock already exists
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            async with article_lock("article-123", "worker-1") as acquired:
                # When nx=True and key exists, set returns None (not False)
                assert acquired is None or acquired is False


class TestTitleLock:
    """Test cases for title_lock context manager."""

    @pytest.mark.asyncio
    async def test_title_lock_acquired(self):
        """Test title lock is acquired successfully."""
        from app.core.locks import title_lock
        
        mock_redis = MagicMock()
        mock_redis.set = MagicMock(return_value=True)
        mock_redis.eval = MagicMock(return_value=1)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            async with title_lock("title-hash-123", "worker-1") as acquired:
                assert acquired is True


class TestDistributionLock:
    """Test cases for DistributionLock class."""

    def test_distribution_lock_try_acquire(self):
        """Test distribution lock try_acquire method."""
        from app.core.locks import DistributionLock
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=None)  # No existing lock
        mock_redis.set = MagicMock(return_value=True)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributionLock("article-123", "telegram", ttl=300)
            result = lock.try_acquire()
            
            assert result is True

    def test_distribution_lock_try_acquire_already_done(self):
        """Test distribution lock when already completed."""
        from app.core.locks import DistributionLock
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=json.dumps({
            "status": "done",
            "completed_at": 1234567890
        }))
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributionLock("article-123", "telegram", ttl=300)
            result = lock.try_acquire()
            
            assert result is False

    def test_distribution_lock_is_completed(self):
        """Test distribution lock is_completed method."""
        from app.core.locks import DistributionLock
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=json.dumps({
            "status": "done"
        }))
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            lock = DistributionLock("article-123", "telegram", ttl=300)
            result = lock.is_completed()
            
            assert result is True


class TestLockHelpers:
    """Test cases for lock helper functions."""

    def test_is_article_locked(self):
        """Test is_article_locked function."""
        from app.core.locks import is_article_locked, DistributedLock
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value="some-owner")
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            result = is_article_locked("article-123")
            assert result is True

    def test_is_article_not_locked(self):
        """Test is_article_locked returns False when not locked."""
        from app.core.locks import is_article_locked, DistributedLock
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=None)
        
        with patch('app.core.redis.get_redis_sync', return_value=mock_redis):
            result = is_article_locked("article-123")
            assert result is False
