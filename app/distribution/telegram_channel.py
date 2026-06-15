"""
Telegram Channel integration for posting articles.
"""
import logging
import re
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    if not text:
        return text
    # Characters that need to be escaped in MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def escape_markdown_v2(text: str) -> str:
    """Enhanced escape for Telegram MarkdownV2 - handles all special cases."""
    if not text:
        return text
    # Replace problematic characters
    # Escape special markdown chars
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    # Remove any unclosed brackets
    text = re.sub(r'\[+', '', text)
    text = re.sub(r'\]+', '', text)
    # Remove consecutive newlines that might cause issues
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


async def post_to_channel(article) -> dict:
    """
    Post an article to the Telegram channel.

    Args:
        article: Article object with meta_title, body_html, category, tags, wp_url, original_image_url

    Returns:
        dict with status, external_id, external_url, error
    """
    settings = get_settings()

    # Check if Telegram is enabled
    if not settings.telegram_channel_enabled:
        logger.info("Telegram channel posting is disabled")
        return {
            "status": "skipped",
            "error": "Telegram channel posting is disabled",
            "channel": "telegram",
        }

    # Get channel ID and bot token
    channel_id = settings.telegram_channel_id
    bot_token = settings.telegram_bot_token

    if not bot_token:
        logger.warning("Telegram bot token not configured")
        return {
            "status": "failed",
            "error": "Telegram bot token not configured",
            "channel": "telegram",
        }

    if not channel_id:
        logger.warning("Telegram channel ID not configured")
        return {
            "status": "failed",
            "error": "Telegram channel ID not configured",
            "channel": "telegram",
        }

    # Format message
    title = article.meta_title or article.original_title
    excerpt = strip_html(article.body_html or "")[:200].strip()
    if excerpt:
        excerpt += "..."
    category = getattr(article, 'category', None) or 'news'

    # Category emoji
    category_emoji = "💻" if category == "tech" else "💰" if category == "finance" else "📰"

    # Build message text - use plain text for reliability
    # Telegram MarkdownV2 is too strict, use plain text
    tags = getattr(article, 'tags', None) or []
    hashtags = " ".join([f"#{tag.replace(' ', '_')}" for tag in tags[:3]]) if tags else f"#{category}"

    text = (
        f"{category_emoji} {title}\n\n"
        f"{excerpt}\n\n"
        f"🔗 {article.wp_url}\n\n"
        f"{hashtags}"
    )

    # Remove trailing space
    text = text.strip()

    # Send message
    api_url = f"https://api.telegram.org/bot{bot_token}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Try to send photo first if we have an image
            image_url = getattr(article, 'original_image_url', None) or None

            if image_url:
                # Send photo with caption (plain text)
                response = await client.post(
                    f"{api_url}/sendPhoto",
                    json={
                        "chat_id": channel_id,
                        "photo": image_url,
                        "caption": text,
                        "disable_web_page_preview": True,
                    },
                )
            else:
                # Send text message only (plain text)
                response = await client.post(
                    f"{api_url}/sendMessage",
                    json={
                        "chat_id": channel_id,
                        "text": text,
                        "disable_web_page_preview": True,
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    result = data.get("result", {})
                    message_id = str(result.get("message_id", ""))
                    channel_name = channel_id.replace('@', '')
                    external_url = f"https://t.me/{channel_name}/{message_id}"

                    logger.info(f"Posted to Telegram channel: {external_url}")
                    return {
                        "status": "success",
                        "external_id": message_id,
                        "external_url": external_url,
                        "channel": "telegram",
                    }
                else:
                    error_desc = data.get("description", "Unknown error")
                    logger.error(f"Telegram API error: {error_desc}")
                    return {
                        "status": "failed",
                        "error": error_desc,
                        "channel": "telegram",
                    }
            else:
                error_text = response.text[:200]
                logger.error(f"Telegram HTTP error: {response.status_code} - {error_text}")
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {error_text}",
                    "channel": "telegram",
                }

    except httpx.TimeoutException:
        logger.error("Telegram API timeout")
        return {
            "status": "failed",
            "error": "Request timeout",
            "channel": "telegram",
        }
    except Exception as e:
        logger.error(f"Error posting to Telegram: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "channel": "telegram",
        }


async def test_telegram_connection() -> dict:
    """Test Telegram bot connection and channel access."""
    settings = get_settings()

    bot_token = settings.telegram_bot_token
    if not bot_token:
        return {"success": False, "error": "Bot token not configured"}

    api_url = f"https://api.telegram.org/bot{bot_token}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get bot info
            response = await client.get(f"{api_url}/getMe")
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}

            data = response.json()
            if not data.get("ok"):
                return {"success": False, "error": data.get("description", "Unknown error")}

            bot_info = data.get("result", {})
            bot_username = bot_info.get("username", "unknown")

            # Try to get chat info
            channel_id = settings.telegram_channel_id
            if channel_id:
                chat_response = await client.get(f"{api_url}/getChat", params={"chat_id": channel_id})
                if chat_response.status_code == 200:
                    chat_data = chat_response.json()
                    if chat_data.get("ok"):
                        chat_info = chat_data.get("result", {})
                        chat_title = chat_info.get("title", "Unknown")
                        chat_type = chat_info.get("type", "unknown")
                        return {
                            "success": True,
                            "bot_username": f"@{bot_username}",
                            "channel_title": chat_title,
                            "channel_type": chat_type,
                        }

            return {
                "success": True,
                "bot_username": f"@{bot_username}",
                "channel_id": channel_id,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
