"""
Robots.txt generator for SEO.
"""
from fastapi import APIRouter
from fastapi.responses import Response

from app.config import get_settings

logger = __name__
router = APIRouter()


@router.get("/robots.txt")
async def robots():
    """
    Generate robots.txt for search engines.
    """
    settings = get_settings()
    site_url = settings.site_url.rstrip("/") if settings.site_url else "https://litimez.ai"

    content = f"""User-agent: *
Allow: /

# Sitemap
Sitemap: {site_url}/sitemap.xml
Sitemap: {site_url}/sitemap-news.xml

# Allow Googlebot (standard)
User-agent: Googlebot
Allow: /

# Allow Googlebot-Image
User-agent: Googlebot-Image
Allow: /wp-content/uploads/
Allow: /wp-content/themes/

# Allow Bingbot
User-agent: Bingbot
Allow: /

# Allow Twitterbot (for Twitter Cards)
User-agent: Twitterbot
Allow: /

# Disallow admin areas
Disallow: /wp-admin/
Disallow: /wp-login.php
Disallow: /wp-content/plugins/
Disallow: /wp-content/cache/
Disallow: /wp-json/
Disallow: /xmlrpc.php
Disallow: /?s=*
Disallow: /search/

# Disallow API endpoints
Disallow: /api/
Disallow: /api

# Allow WP admin for logged in users (they add noindex themselves)
Allow: /wp-admin/admin-ajax.php
"""

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Cache-Control": "public, max-age=86400",  # 24 hours
        }
    )
