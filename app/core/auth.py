"""
API Authentication middleware.
Supports API key auth via X-API-Key header or ?api_key= query param.
"""
import logging
import secrets
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

from app.config import get_settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    header_key: Optional[str] = Security(API_KEY_HEADER),
    query_key: Optional[str] = Security(API_KEY_QUERY),
) -> str:
    """
    Validate API key from header or query param.
    Public endpoints (health, sitemap, robots, feed, widget) are exempt.
    """
    settings = get_settings()

    # If no API key configured, skip auth (development mode)
    if not settings.api_key:
        return "no-auth-configured"

    provided_key = header_key or query_key

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header or ?api_key= query param.",
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_key, settings.api_key):
        logger.warning(f"Invalid API key attempt: {provided_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return provided_key


# Dependency alias for protected routes
require_auth = get_api_key
