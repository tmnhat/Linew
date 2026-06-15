"""
Redis caching layer cho prediction system.
Sử dụng Redis để cache AI analysis, predictions, và indicators.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Cache TTL configurations (in seconds)
CACHE_TTL = {
    "price": 60,           # 1 minute - prices change frequently
    "prediction": 3600,    # 1 hour - predictions are generated hourly
    "analysis": 3600,      # 1 hour - AI analysis cached
    "indicators": 300,     # 5 minutes - technical indicators
    "symbols": 86400,      # 24 hours - symbol lists rarely change
    "news": 900,           # 15 minutes - news updates
    "fear_greed": 1800,    # 30 minutes - Fear & Greed index
}

# Redis key prefixes
KEY_PREFIX = "linew:prediction:"


class PredictionCache:
    """
    Redis cache manager cho prediction system.
    """
    
    _instance = None
    _redis: Optional[aioredis.Redis] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, redis_url: str = None) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return
        
        if redis_url is None:
            from app.config import get_settings
            settings = get_settings()
            redis_url = settings.redis_url
        
        try:
            self._redis = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._initialized = True
            logger.info("Prediction cache initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
            self._redis = None
            self._initialized = True  # Mark as initialized even if failed
    
    def _get_key(self, key_type: str, identifier: str) -> str:
        """Generate cache key."""
        return f"{KEY_PREFIX}{key_type}:{identifier}"
    
    async def get(self, key_type: str, identifier: str) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            key_type: Type of data (price, prediction, analysis, etc.)
            identifier: Unique identifier (symbol name, date, etc.)
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self._redis:
            return None
        
        try:
            key = self._get_key(key_type, identifier)
            data = await self._redis.get(key)
            
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
                
        except Exception as e:
            logger.warning(f"Cache get error for {key_type}/{identifier}: {e}")
            return None
    
    async def set(
        self,
        key_type: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set cached value.
        
        Args:
            key_type: Type of data
            identifier: Unique identifier
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successful
        """
        if not self._redis:
            return False
        
        try:
            key = self._get_key(key_type, identifier)
            ttl = ttl or CACHE_TTL.get(key_type, 3600)
            
            # Serialize value
            serialized = json.dumps(value, default=str)
            
            await self._redis.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error for {key_type}/{identifier}: {e}")
            return False
    
    async def delete(self, key_type: str, identifier: str) -> bool:
        """Delete cached value."""
        if not self._redis:
            return False
        
        try:
            key = self._get_key(key_type, identifier)
            await self._redis.delete(key)
            logger.debug(f"Cache delete: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (VD: "analysis:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._redis:
            return 0
        
        try:
            full_pattern = f"{KEY_PREFIX}{pattern}"
            keys = []
            
            async for key in self._redis.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache delete pattern {pattern}: {deleted} keys")
                return deleted
            return 0
            
        except Exception as e:
            logger.warning(f"Cache delete pattern error: {e}")
            return 0
    
    async def get_or_set(
        self,
        key_type: str,
        identifier: str,
        fetch_func,
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get from cache or fetch and cache.
        
        Args:
            key_type: Type of data
            identifier: Unique identifier
            fetch_func: Async function to fetch data if not cached
            ttl: Time-to-live in seconds
            
        Returns:
            Cached or freshly fetched value
        """
        # Try cache first
        cached = await self.get(key_type, identifier)
        if cached is not None:
            return cached
        
        # Fetch fresh data
        if callable(fetch_func):
            value = await fetch_func()
        else:
            value = fetch_func
        
        # Cache the result
        if value is not None:
            await self.set(key_type, identifier, value, ttl)
        
        return value
    
    async def exists(self, key_type: str, identifier: str) -> bool:
        """Check if key exists in cache."""
        if not self._redis:
            return False
        
        try:
            key = self._get_key(key_type, identifier)
            return await self._redis.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists check error: {e}")
            return False
    
    async def get_ttl(self, key_type: str, identifier: str) -> int:
        """Get remaining TTL for a key."""
        if not self._redis:
            return -1
        
        try:
            key = self._get_key(key_type, identifier)
            ttl = await self._redis.ttl(key)
            return ttl if ttl > 0 else -1
        except Exception:
            return -1
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._initialized = False
            logger.info("Prediction cache closed")


# Singleton instance
prediction_cache = PredictionCache()


# Convenience functions for specific data types

async def get_cached_price(symbol: str) -> Optional[dict]:
    """Get cached price data."""
    return await prediction_cache.get("price", symbol.upper())


async def cache_price(symbol: str, price_data: dict) -> bool:
    """Cache price data."""
    return await prediction_cache.set("price", symbol.upper(), price_data, CACHE_TTL["price"])


async def get_cached_analysis(symbol: str) -> Optional[dict]:
    """Get cached AI analysis."""
    return await prediction_cache.get("analysis", symbol.upper())


async def cache_analysis(symbol: str, analysis: dict, ttl: int = None) -> bool:
    """Cache AI analysis."""
    return await prediction_cache.set(
        "analysis",
        symbol.upper(),
        analysis,
        ttl or CACHE_TTL["analysis"]
    )


async def get_cached_prediction(symbol: str, horizon: int = None) -> Optional[dict]:
    """Get cached prediction."""
    key = f"{symbol.upper()}_{horizon}" if horizon else symbol.upper()
    return await prediction_cache.get("prediction", key)


async def cache_prediction(
    symbol: str,
    prediction: dict,
    horizon: int = None,
    ttl: int = None,
) -> bool:
    """Cache prediction data."""
    key = f"{symbol.upper()}_{horizon}" if horizon else symbol.upper()
    return await prediction_cache.set(
        "prediction",
        key,
        prediction,
        ttl or CACHE_TTL["prediction"]
    )


async def get_cached_indicators(symbol: str) -> Optional[dict]:
    """Get cached technical indicators."""
    return await prediction_cache.get("indicators", symbol.upper())


async def cache_indicators(symbol: str, indicators: dict) -> bool:
    """Cache technical indicators."""
    return await prediction_cache.set(
        "indicators",
        symbol.upper(),
        indicators,
        CACHE_TTL["indicators"]
    )


async def get_cached_news(symbol: str) -> Optional[list]:
    """Get cached news headlines."""
    return await prediction_cache.get("news", symbol.upper())


async def cache_news(symbol: str, news: list) -> bool:
    """Cache news headlines."""
    return await prediction_cache.set(
        "news",
        symbol.upper(),
        news,
        CACHE_TTL["news"]
    )


async def get_cached_fear_greed() -> Optional[dict]:
    """Get cached Fear & Greed index."""
    return await prediction_cache.get("fear_greed", "index")


async def cache_fear_greed(data: dict) -> bool:
    """Cache Fear & Greed index."""
    return await prediction_cache.set("fear_greed", "index", data, CACHE_TTL["fear_greed"])


async def invalidate_symbol_cache(symbol: str) -> int:
    """
    Invalidate all cache entries for a symbol.
    
    Args:
        symbol: Stock/crypto symbol
        
    Returns:
        Number of entries deleted
    """
    total = 0
    for key_type in ["price", "analysis", "prediction", "indicators", "news"]:
        deleted = await prediction_cache.delete(key_type, symbol.upper())
        total += deleted
    return total


async def invalidate_all_predictions() -> int:
    """Invalidate all cached predictions."""
    return await prediction_cache.delete_pattern("prediction:*")


async def invalidate_all_analyses() -> int:
    """Invalidate all cached AI analyses."""
    return await prediction_cache.delete_pattern("analysis:*")
