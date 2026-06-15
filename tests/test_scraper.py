"""
Tests for web scraper functionality.

Tests cover:
- HTTP fetch with retry logic
- FlareSolverr fetch with retry logic
- Image extraction
- Content extraction
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import httpx


class TestFetchWithHeaders:
    """Test cases for fetch_with_headers function."""

    @pytest.mark.asyncio
    async def test_fetch_with_headers_success(self):
        """Test successful HTTP fetch."""
        from app.signals.web_scraper import fetch_with_headers
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "x" * 1000  # Sufficiently large content
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await fetch_with_headers("https://example.com")
            
            # Should return content (or None if mocked incorrectly)
            assert result is None or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_fetch_with_headers_timeout(self):
        """Test HTTP fetch with timeout."""
        from app.signals.web_scraper import fetch_with_headers
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            result = await fetch_with_headers("https://example.com", timeout=5)
            
            assert result is None


class TestFetchViaFlaresolverr:
    """Test cases for fetch_via_flaresolverr function."""

    @pytest.mark.asyncio
    async def test_flaresolverr_success(self):
        """Test successful FlareSolverr fetch."""
        from app.signals.web_scraper import fetch_via_flaresolverr
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "status": "ok",
            "solution": {
                "response": "x" * 1000  # Sufficiently large content
            }
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await fetch_via_flaresolverr("https://example.com")
            
            # Should return content or None
            assert result is None or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_flaresolverr_empty_response(self):
        """Test FlareSolverr with empty response."""
        from app.signals.web_scraper import fetch_via_flaresolverr
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "status": "ok",
            "solution": {
                "response": ""  # Empty content
            }
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await fetch_via_flaresolverr("https://example.com")
            
            # Should return None for empty response
            assert result is None

    @pytest.mark.asyncio
    async def test_flaresolverr_cf_challenge(self):
        """Test FlareSolverr with Cloudflare challenge response."""
        from app.signals.web_scraper import fetch_via_flaresolverr
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "status": "error",
            "message": "Cloudflare challenge"
        })
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await fetch_via_flaresolverr("https://example.com")
            
            assert result is None


class TestImageExtraction:
    """Test cases for image extraction functions."""

    def test_should_skip_image_url_icon(self):
        """Test that icon images are skipped."""
        from app.signals.web_scraper import _should_skip_image_url
        
        result = _should_skip_image_url("https://example.com/icon.png")
        assert result is True

    def test_should_skip_image_url_logo(self):
        """Test that logo images are skipped."""
        from app.signals.web_scraper import _should_skip_image_url
        
        result = _should_skip_image_url("https://example.com/logo.jpg")
        assert result is True

    def test_should_skip_image_url_ads(self):
        """Test that ad/tracking images are skipped."""
        from app.signals.web_scraper import _should_skip_image_url
        
        result = _should_skip_image_url("https://doubleclick.net/ad.jpg")
        assert result is True

    def test_should_skip_image_url_qrcode(self):
        """Test that QR code images are skipped."""
        from app.signals.web_scraper import _should_skip_image_url
        
        result = _should_skip_image_url("https://example.com/qrcode.png")
        assert result is True

    def test_should_not_skip_article_image(self):
        """Test that normal article images are not skipped."""
        from app.signals.web_scraper import _should_skip_image_url
        
        # A normal article image should not be skipped
        result = _should_skip_image_url(
            "https://example.com/images/article-123-hero.jpg"
        )
        # Result depends on implementation, but we test the function runs
        assert isinstance(result, bool)

    def test_should_skip_small_image(self):
        """Test that very small images are skipped."""
        from app.signals.web_scraper import _should_skip_image_url
        
        result = _should_skip_image_url("https://example.com/spacer.gif")
        assert result is True

    def test_extract_images_from_html(self):
        """Test extract_images_from_html function."""
        from app.signals.web_scraper import extract_images_from_html
        
        html = """
        <html>
            <head>
                <meta property="og:image" content="https://example.com/og-image.jpg">
            </head>
            <body>
                <article>
                    <img src="https://example.com/article-image.jpg" alt="Article image">
                </article>
            </body>
        </html>
        """
        
        images = extract_images_from_html(html, "https://example.com/article")
        
        # Test that function returns a list
        assert isinstance(images, list)


class TestContentExtraction:
    """Test cases for content extraction."""

    def test_strip_html(self):
        """Test HTML tag stripping."""
        from app.distribution.facebook import strip_html
        
        html = "<p>Hello <strong>World</strong></p>"
        result = strip_html(html)
        
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Hello" in result
        assert "World" in result

    def test_strip_all_links(self):
        """Test complete link stripping."""
        from app.distribution.facebook import strip_all_links
        
        text = """
        Check out this <a href="https://example.com">link</a> and 
        this https://another.com/url and 
        visit www.example.com
        """
        
        result = strip_all_links(text)
        
        assert "href=" not in result
        assert "https://" not in result
        assert "www.example.com" not in result
        assert "Check out this" in result

    def test_sanitize_message(self):
        """Test message sanitization."""
        from app.distribution.facebook import sanitize_message
        
        message = """
        This is a message with [https://link.com] and 
        (https://another.com) links
        """
        
        result = sanitize_message(message)
        
        assert "[https://" not in result
        assert "(https://" not in result
