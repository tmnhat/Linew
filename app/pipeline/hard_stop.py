"""
Pipeline Hard Stop Module - cơ chế dừng pipeline đáng tin cậy qua Redis.

Nguyên tắc hoạt động:
1. User bấm Stop → Set STOP_KEY = "true"
2. Pipeline check STOP_KEY trước mỗi batch/article
3. Nếu STOP_KEY = "true" → Dừng ngay lập tức
4. Pipeline dừng → Xóa STOP_KEY để có thể start lại

Ưu điểm:
- Redis-based → Works across all workers
- Sync check → Không cần async
- Instant response → Không cần chờ tick
"""
import asyncio
import threading
from datetime import datetime
from typing import Optional

# Redis key cho stop signal
STOP_SIGNAL_KEY = "linew:pipeline:user_stop"
STOP_TIMESTAMP_KEY = "linew:pipeline:user_stop_timestamp"
STOP_REASON_KEY = "linew:pipeline:user_stop_reason"

# Cache để tránh đọc Redis quá nhiều
# Refresh mỗi 1 giây
_stop_signal_cache = {"value": False, "last_check": 0.0}
_cache_lock = threading.Lock()
_CACHE_TTL = 1.0  # 1 giây


def should_stop_pipeline() -> bool:
    """
    Kiểm tra xem pipeline có nên dừng không.
    
    Returns:
        True nếu user đã bấm Stop HOẶC pipeline cần dừng
        False nếu pipeline nên tiếp tục chạy
    
    Cơ chế cache để tránh đọc Redis quá nhiều lần.
    """
    import time
    
    current_time = time.time()
    
    with _cache_lock:
        # Nếu cache còn valid, trả về cached value
        if current_time - _stop_signal_cache["last_check"] < _CACHE_TTL:
            return _stop_signal_cache["value"]
        
        # Cache expired, đọc từ Redis
        _stop_signal_cache["last_check"] = current_time
    
    # Đọc từ Redis (sync call - cần wrap trong asyncio)
    try:
        import redis
        from app.config import get_settings
        
        settings = get_settings()
        
        # Parse Redis URL
        from urllib.parse import urlparse
        parsed = urlparse(settings.redis_url)
        redis_host = parsed.hostname or "localhost"
        redis_port = parsed.port or 6379
        redis_db = int(parsed.path.lstrip("/") or 0)
        
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
        )
        
        stop_signal = client.get(STOP_SIGNAL_KEY)
        should_stop = stop_signal == "true"
        
        with _cache_lock:
            _stop_signal_cache["value"] = should_stop
        
        return should_stop
        
    except Exception:
        # Nếu lỗi Redis, không dừng pipeline
        return False


async def should_stop_pipeline_async() -> bool:
    """
    Async version của should_stop_pipeline().
    Sử dụng trong async context.
    """
    try:
        from app.core.redis import get_redis
        
        redis = await get_redis()
        stop_signal = await redis.get(STOP_SIGNAL_KEY)
        return stop_signal == "true"
    except Exception:
        return False


def trigger_user_stop(reason: str = "User requested stop") -> dict:
    """
    User bấm Stop → Gọi hàm này.
    
    Args:
        reason: Lý do dừng (mặc định: "User requested stop")
    
    Returns:
        Dict với trạng thái operation
    """
    try:
        import redis
        from urllib.parse import urlparse
        from app.config import get_settings
        
        settings = get_settings()
        parsed = urlparse(settings.redis_url)
        redis_host = parsed.hostname or "localhost"
        redis_port = parsed.port or 6379
        redis_db = int(parsed.path.lstrip("/") or 0)
        
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
        )
        
        timestamp = datetime.utcnow().isoformat()
        
        # Set stop signal
        pipe = client.pipeline()
        pipe.set(STOP_SIGNAL_KEY, "true")
        pipe.set(STOP_TIMESTAMP_KEY, timestamp)
        pipe.set(STOP_REASON_KEY, reason)
        pipe.execute()
        
        # Clear cache
        with _cache_lock:
            _stop_signal_cache["value"] = True
            _stop_signal_cache["last_check"] = 0.0
        
        return {
            "success": True,
            "message": "Stop signal triggered",
            "timestamp": timestamp,
            "reason": reason,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def clear_user_stop() -> dict:
    """
    Xóa stop signal để pipeline có thể start lại.
    Gọi khi user bấm Start.
    """
    try:
        import redis
        from urllib.parse import urlparse
        from app.config import get_settings
        
        settings = get_settings()
        parsed = urlparse(settings.redis_url)
        redis_host = parsed.hostname or "localhost"
        redis_port = parsed.port or 6379
        redis_db = int(parsed.path.lstrip("/") or 0)
        
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
        )
        
        # Delete all stop-related keys
        pipe = client.pipeline()
        pipe.delete(STOP_SIGNAL_KEY)
        pipe.delete(STOP_TIMESTAMP_KEY)
        pipe.delete(STOP_REASON_KEY)
        pipe.execute()
        
        # Clear cache
        with _cache_lock:
            _stop_signal_cache["value"] = False
            _stop_signal_cache["last_check"] = 0.0
        
        return {
            "success": True,
            "message": "Stop signal cleared",
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_stop_status() -> dict:
    """
    Lấy trạng thái stop signal hiện tại.
    """
    try:
        import redis
        from urllib.parse import urlparse
        from app.config import get_settings
        
        settings = get_settings()
        parsed = urlparse(settings.redis_url)
        redis_host = parsed.hostname or "localhost"
        redis_port = parsed.port or 6379
        redis_db = int(parsed.path.lstrip("/") or 0)
        
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
        )
        
        pipe = client.pipeline()
        pipe.get(STOP_SIGNAL_KEY)
        pipe.get(STOP_TIMESTAMP_KEY)
        pipe.get(STOP_REASON_KEY)
        results = pipe.execute()
        
        return {
            "is_stopped": results[0] == "true",
            "timestamp": results[1],
            "reason": results[2],
        }
        
    except Exception as e:
        return {
            "is_stopped": False,
            "error": str(e),
        }


async def get_stop_status_async() -> dict:
    """Async version của get_stop_status()."""
    try:
        from app.core.redis import get_redis
        
        redis = await get_redis()
        pipe = redis.pipeline()
        pipe.get(STOP_SIGNAL_KEY)
        pipe.get(STOP_TIMESTAMP_KEY)
        pipe.get(STOP_REASON_KEY)
        results = await pipe.execute()
        
        return {
            "is_stopped": results[0] == "true",
            "timestamp": results[1],
            "reason": results[2],
        }
        
    except Exception as e:
        return {
            "is_stopped": False,
            "error": str(e),
        }
