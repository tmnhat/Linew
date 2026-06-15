"""
Facebook rate limiting and metrics tracking.

Handles:
- Rate limit tracking
- Post success/failure logging
- Metrics collection
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Rate limit tracking keys
RATE_LIMIT_STATE_KEY = "linew:facebook:rate_limit"
RATE_LIMIT_WINDOW_MINUTES = 60


def track_facebook_post_success():
    """Track successful Facebook post for rate limiting."""
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)

        now = datetime.utcnow()

        r.set(f"{RATE_LIMIT_STATE_KEY}:last_success", now.isoformat())
        r.expire(f"{RATE_LIMIT_STATE_KEY}:last_success", RATE_LIMIT_WINDOW_MINUTES * 2)

        posts_key = f"{RATE_LIMIT_STATE_KEY}:posts:{now.strftime('%Y%m%d%H%M')}"
        r.incr(posts_key)
        r.expire(posts_key, RATE_LIMIT_WINDOW_MINUTES * 2)

        logger.info(
            f"[Facebook Rate Limit] Post success tracked. "
            f"Window posts: {r.get(posts_key)}, "
            f"Last success: {now.isoformat()}"
        )
    except Exception as e:
        logger.warning(f"[Facebook Rate Limit] Failed to track success: {e}")


def check_facebook_rate_limit_status() -> dict:
    """Check current Facebook rate limit status."""
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)

        now = datetime.utcnow()

        last_success = r.get(f"{RATE_LIMIT_STATE_KEY}:last_success")
        if last_success:
            last_success_time = datetime.fromisoformat(last_success)
            minutes_since = (now - last_success_time).total_seconds() / 60
        else:
            minutes_since = None

        current_key = f"{RATE_LIMIT_STATE_KEY}:posts:{now.strftime('%Y%m%d%H%M')}"
        posts_this_minute = int(r.get(current_key) or 0)

        total_recent = 0
        for i in range(60):
            check_time = now - timedelta(minutes=i)
            key = f"{RATE_LIMIT_STATE_KEY}:posts:{check_time.strftime('%Y%m%d%H%M')}"
            total_recent += int(r.get(key) or 0)

        return {
            "last_success_minutes_ago": minutes_since,
            "posts_this_minute": posts_this_minute,
            "posts_last_60_minutes": total_recent,
            "limit_per_hour": 500,
            "can_post": total_recent < 500,
        }
    except Exception as e:
        logger.warning(f"[Facebook Rate Limit] Failed to check status: {e}")
        return {"error": str(e)}


def log_facebook_rate_limit_error(error_code: int, error_message: str):
    """Log Facebook rate limit errors for monitoring."""
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)

        now = datetime.utcnow()
        error_key = f"{RATE_LIMIT_STATE_KEY}:errors:{now.strftime('%Y%m%d%H%M')}"

        r.incr(error_key)
        r.expire(error_key, RATE_LIMIT_WINDOW_MINUTES * 2)

        error_count = int(r.get(error_key) or 0)

        logger.warning(
            f"[Facebook Rate Limit] Error detected. "
            f"Error code: {error_code}, Message: {error_message[:100]}, "
            f"Errors this minute: {error_count}"
        )

        if error_count >= 5:
            logger.error(
                f"[Facebook Rate Limit] HIGH ERROR RATE: {error_count} errors in current minute!"
            )
    except Exception as e:
        logger.warning(f"[Facebook Rate Limit] Failed to log error: {e}")


def get_facebook_metrics(days: int = 7) -> dict:
    """Get Facebook posting metrics for the past N days."""
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)

        now = datetime.utcnow()
        total_posts = 0
        total_errors = 0

        for i in range(days * 24):
            check_time = now - timedelta(hours=i)
            
            posts_key = f"{RATE_LIMIT_STATE_KEY}:posts:{check_time.strftime('%Y%m%d%H%M')}"
            total_posts += int(r.get(posts_key) or 0)

            error_key = f"{RATE_LIMIT_STATE_KEY}:errors:{check_time.strftime('%Y%m%d%H%M')}"
            total_errors += int(r.get(error_key) or 0)

        return {
            "posts_last_7_days": total_posts,
            "errors_last_7_days": total_errors,
            "average_posts_per_day": total_posts / days if days > 0 else 0,
            "success_rate": (total_posts - total_errors) / total_posts if total_posts > 0 else 0,
        }
    except Exception as e:
        logger.warning(f"[Facebook Metrics] Failed to get metrics: {e}")
        return {"error": str(e)}


def clear_facebook_metrics():
    """Clear all Facebook metrics (for testing)."""
    try:
        import redis
        from app.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)

        pattern = f"{RATE_LIMIT_STATE_KEY}:*"
        for key in r.scan_iter(match=pattern):
            r.delete(key)

        logger.info("[Facebook Metrics] All metrics cleared")
    except Exception as e:
        logger.warning(f"[Facebook Metrics] Failed to clear metrics: {e}")
