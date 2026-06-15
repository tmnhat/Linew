"""
Twitter/X integration for posting articles.
"""
import logging
import re
from typing import Optional

import tweepy

from app.config import get_settings

logger = logging.getLogger(__name__)


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


def get_twitter_client() -> Optional[tweepy.Client]:
    """Get configured Twitter API v2 client."""
    settings = get_settings()

    api_key = settings.twitter_api_key
    api_secret = settings.twitter_api_secret
    access_token = settings.twitter_access_token
    access_secret = settings.twitter_access_secret

    if not all([api_key, api_secret, access_token, access_secret]):
        logger.warning("Twitter credentials not configured")
        return None

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        return client
    except Exception as e:
        logger.error(f"Error creating Twitter client: {e}")
        return None


async def post_to_twitter(article) -> dict:
    """
    Post a tweet about an article.

    Twitter has a 280 character limit, so we need to be concise.

    Args:
        article: Article object with meta_title, body_html, category, tags, wp_url

    Returns:
        dict with status, external_id, external_url, error
    """
    settings = get_settings()

    # Check if Twitter is enabled
    if not settings.twitter_enabled:
        logger.info("Twitter posting is disabled")
        return {
            "status": "skipped",
            "error": "Twitter posting is disabled",
            "channel": "twitter",
        }

    client = get_twitter_client()
    if not client:
        return {
            "status": "failed",
            "error": "Twitter client not configured",
            "channel": "twitter",
        }

    # Build tweet text
    title = article.meta_title or article.original_title
    category = getattr(article, 'category', None) or 'news'

    # Hashtags
    tags = getattr(article, 'tags', None) or []
    if isinstance(tags, list):
        hashtags = " ".join([f"#{tag.replace(' ', '')}" for tag in tags[:3]])
    else:
        hashtags = f"#{category}"

    link = article.wp_url or ""

    # Build tweet with title + hashtags + link
    # Reserve space for link + space + hashtags + newlines
    reserved = len(link) + 10 + len(hashtags)

    # Title length calculation
    max_title_len = 280 - reserved

    # Truncate title if needed
    if len(title) > max_title_len:
        title = title[:max_title_len - 3] + "..."

    tweet_text = f"{title}\n\n{hashtags}\n\n{link}"

    # Final check
    if len(tweet_text) > 280:
        # Aggressive truncation
        max_title_len = 280 - reserved - 5
        title = title[:max_title_len] + "..."
        tweet_text = f"{title}\n\n{hashtags}\n\n{link}"

    try:
        # Post tweet
        response = client.create_tweet(text=tweet_text)

        if response.data:
            tweet_id = str(response.data["id"])
            external_url = f"https://twitter.com/linews_vn/status/{tweet_id}"

            logger.info(f"Posted to Twitter: {external_url}")
            return {
                "status": "success",
                "external_id": tweet_id,
                "external_url": external_url,
                "channel": "twitter",
            }
        else:
            logger.error(f"Twitter API returned no data: {response}")
            return {
                "status": "failed",
                "error": "No tweet ID returned",
                "channel": "twitter",
            }

    except tweepy.TooManyRequests:
        logger.error("Twitter rate limit exceeded")
        return {
            "status": "failed",
            "error": "Rate limit exceeded",
            "channel": "twitter",
        }
    except tweepy.Forbidden as e:
        if "duplicate" in str(e).lower():
            logger.warning("Duplicate tweet detected")
            return {
                "status": "skipped",
                "error": "Duplicate content",
                "channel": "twitter",
            }
        logger.error(f"Twitter forbidden: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "channel": "twitter",
        }
    except Exception as e:
        logger.error(f"Error posting to Twitter: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "channel": "twitter",
        }


async def test_twitter_connection() -> dict:
    """Test Twitter API connection."""
    client = get_twitter_client()

    if not client:
        return {"success": False, "error": "Twitter credentials not configured"}

    try:
        # Get user info
        me = client.get_me(user_fields=["username", "name", "public_metrics"])
        if me.data:
            user = me.data
            return {
                "success": True,
                "username": f"@{user.username}",
                "name": user.name,
                "followers": user.public_metrics["followers_count"],
            }
        else:
            return {"success": False, "error": "Could not get user info"}
    except Exception as e:
        return {"success": False, "error": str(e)}
