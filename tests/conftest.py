"""
Pytest configuration and fixtures for Linew tests.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.set = MagicMock(return_value=True)
    mock.get = MagicMock(return_value=None)
    mock.delete = MagicMock(return_value=1)
    mock.eval = MagicMock(return_value=1)
    mock.expire = MagicMock(return_value=True)
    mock.setex = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_article():
    """Create a sample article object for testing."""
    article = MagicMock()
    article.id = "test-article-123"
    article.original_title = "Test Article Title"
    article.meta_title = "Test Meta Title"
    article.original_summary = "This is a test summary with enough content to be valid."
    article.category = "tech"
    article.body_html = "<p>This is the article body with <strong>rich content</strong>.</p>"
    article.slug = "test-article-title"
    article.title_hash = "abc123def456"
    article.state = "researched"
    article.source_id = None
    return article


@pytest.fixture
def sample_source():
    """Create a sample source object for testing."""
    source = MagicMock()
    source.id = "test-source-123"
    source.name = "Test Source"
    source.url = "https://example.com"
    source.requires_flaresolverr = False
    return source
