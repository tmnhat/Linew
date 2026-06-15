"""
Facebook Page integration for posting articles.

This module handles posting articles to Facebook Page without any links attached.
Uses photo upload approach to ensure clean posts without link previews.

NOTE: This module is maintained for backward compatibility.
For new code, use: app.distribution.facebook

Import from the package for new functionality:
    from app.distribution.facebook import format_article_for_facebook, post_photo_to_facebook
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"

# Facebook API error codes
ERROR_TOKEN_EXPIRED = 190
ERROR_PERMISSION_DENIED = 200
ERROR_RATE_LIMIT = 4

# Rate limit tracking
RATE_LIMIT_STATE_KEY = "linew:facebook:rate_limit"
RATE_LIMIT_WINDOW_MINUTES = 60


# === BACKWARD COMPATIBILITY ===
# Re-export from new package for existing imports
from app.distribution.facebook import (
    strip_html,
    strip_all_links,
    sanitize_message,
    format_article_for_facebook,
    upload_photo_to_facebook,
    create_photo_post,
    post_photo_to_facebook,
    test_facebook_connection,
    track_facebook_post_success,
    check_facebook_rate_limit_status,
    log_facebook_rate_limit_error,
    get_facebook_metrics,
    clear_facebook_metrics,
)


def get_category_emoji(category: str) -> str:
    """Get emoji for category."""
    from app.distribution.facebook.message import get_category_emoji as _get
    return _get(category)


def get_category_prefix(category: str) -> str:
    """Get category prefix for message."""
    from app.distribution.facebook.message import get_category_prefix as _get
    return _get(category)
