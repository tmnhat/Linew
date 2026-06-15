"""
Cross-post to Medium and other platforms.
"""
import logging
import re
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


async def post_to_medium(article, medium_token: str) -> dict:
    """
    Post an article to Medium.

    Requires a Medium integration token from https://medium.com/me/settings/security

    Args:
        article: Article object with meta_title, body_html, tags, wp_url
        medium_token: Medium integration token

    Returns:
        dict with status, external_id, external_url, error
    """
    if not medium_token:
        logger.warning("Medium token not configured")
        return {
            "status": "failed",
            "error": "Medium token not configured",
            "channel": "medium",
        }

    headers = {
        "Authorization": f"Bearer {medium_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Get user info first
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            user_resp = await client.get(
                "https://api.medium.com/v1/users/me",
                headers=headers,
            )

            if user_resp.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"Medium API error: {user_resp.status_code}",
                    "channel": "medium",
                }

            user_data = user_resp.json()
            if "data" not in user_data:
                return {
                    "status": "failed",
                    "error": "Could not get Medium user info",
                    "channel": "medium",
                }

            user_id = user_data["data"]["id"]

            # Format content for Medium
            title = article.meta_title or article.original_title
            body_html = article.body_html or ""

            # Add source attribution
            attribution = f'\n\n<p><em>Bài viết gốc: <a href="{article.wp_url}">Linews</a></em></p>'

            # Prepare tags
            tags = getattr(article, 'tags', None) or []
            if isinstance(tags, list):
                tags = tags[:5]

            # Post to Medium
            post_data = {
                "title": title,
                "contentFormat": "html",
                "content": body_html + attribution,
                "canonicalUrl": article.wp_url,  # Important for SEO - avoids duplicate content
                "tags": tags,
                "publishStatus": "public",
            }

            post_resp = await client.post(
                f"https://api.medium.com/v1/users/{user_id}/posts",
                headers=headers,
                json=post_data,
            )

            if post_resp.status_code == 201:
                post_result = post_resp.json()
                post_data_response = post_result.get("data", {})

                logger.info(f"Posted to Medium: {post_data_response.get('url')}")
                return {
                    "status": "success",
                    "external_id": post_data_response.get("id"),
                    "external_url": post_data_response.get("url"),
                    "channel": "medium",
                }
            else:
                error_text = post_resp.text[:200]
                logger.error(f"Medium post error: {error_text}")
                return {
                    "status": "failed",
                    "error": f"HTTP {post_resp.status_code}: {error_text}",
                    "channel": "medium",
                }

    except httpx.TimeoutException:
        logger.error("Medium API timeout")
        return {
            "status": "failed",
            "error": "Request timeout",
            "channel": "medium",
        }
    except Exception as e:
        logger.error(f"Error posting to Medium: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "channel": "medium",
        }


async def post_to_viblo(article, viblo_token: str) -> dict:
    """
    Post an article to Viblo (Vietnamese tech community).

    This is a placeholder - Viblo doesn't have a public API.
    In production, this would need to be implemented differently.

    Args:
        article: Article object
        viblo_token: Viblo API token (if available)

    Returns:
        dict with status, external_id, external_url, error
    """
    logger.info("Viblo cross-post not implemented (no public API)")
    return {
        "status": "skipped",
        "error": "Viblo cross-post not implemented (no public API)",
        "channel": "viblo",
    }


async def test_medium_connection(medium_token: str) -> dict:
    """Test Medium API connection."""
    if not medium_token:
        return {"success": False, "error": "Medium token not configured"}

    headers = {
        "Authorization": f"Bearer {medium_token}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.medium.com/v1/users/me",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                user = data.get("data", {})
                return {
                    "success": True,
                    "username": user.get("username"),
                    "name": user.get("name"),
                    "url": user.get("url"),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:100]}",
                }

    except Exception as e:
        return {"success": False, "error": str(e)}
