"""
Facebook distribution package.

This package contains:
- message: Message formatting and sanitization
- api: Facebook Graph API integration
- scheduler: Scheduled posting logic
- metrics: Rate limiting and metrics tracking

Usage:
    from app.distribution.facebook.message import format_article_for_facebook
    from app.distribution.facebook.api import post_photo_to_facebook
    from app.distribution.facebook.metrics import check_facebook_rate_limit_status
"""
from app.distribution.facebook.message import (
    strip_html,
    strip_all_links,
    sanitize_message,
    get_category_emoji,
    get_category_prefix,
    format_article_for_facebook,
)
from app.distribution.facebook.api import (
    upload_photo_to_facebook,
    create_photo_post,
    post_photo_to_facebook,
    test_facebook_connection,
)
from app.distribution.facebook.metrics import (
    track_facebook_post_success,
    check_facebook_rate_limit_status,
    log_facebook_rate_limit_error,
    get_facebook_metrics,
    clear_facebook_metrics,
)


async def post_to_facebook_no_link(article) -> dict:
    """
    Post an article to Facebook Page without any links.

    This is the main entry point for Facebook scheduled posting.
    Posts the article with its image but WITHOUT any links to the website.

    Args:
        article: Article object with attributes like meta_title, category, etc.

    Returns:
        dict with status, post_id, external_url, etc.
    """
    from app.config import get_settings
    from app.distribution.facebook.api import post_photo_to_facebook

    settings = get_settings()

    page_id = settings.facebook_page_id
    access_token = settings.facebook_page_access_token

    if not page_id or not access_token:
        return {"status": "failed", "error": "Facebook credentials not configured"}

    # Format message and get image
    message, image_url = format_article_for_facebook(article)

    if not image_url:
        return {"status": "failed", "error": "No image available for Facebook post"}

    # Post to Facebook (no_link=True for scheduled posting)
    result = await post_photo_to_facebook(
        page_id=page_id,
        access_token=access_token,
        image_url=image_url,
        message=message,
        no_link=True,  # This ensures no link is included
    )

    if "error" in result:
        return {
            "status": "failed",
            "error": result.get("error", "Unknown error"),
            "post_id": result.get("post_id"),
            "external_url": result.get("post_url"),
        }

    return {
        "status": "success",
        "post_id": result.get("post_id"),
        "external_url": result.get("post_url"),
        "has_image": bool(image_url),
    }
