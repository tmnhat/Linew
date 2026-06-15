"""
Deduplication logic using URL normalization and title hashing.
"""
import hashlib
import re
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.article_states import IN_PROGRESS_STATES

logger = logging.getLogger(__name__)


def normalize_title_for_hash(title: str) -> str:
    """
    Normalize title for hashing:
    - Lowercase
    - Remove punctuation
    - Normalize whitespace
    """
    # Lowercase
    title = title.lower()
    # Remove punctuation
    title = re.sub(r'[^\w\s]', '', title)
    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def hash_title(title: str) -> str:
    """Generate SHA-256 hash of normalized title."""
    normalized = normalize_title_for_hash(title)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def normalize_url_for_dedup(url: str) -> str:
    """
    Normalize URL for dedup:
    - Remove trailing slashes
    - Lowercase
    - Remove www prefix
    - FIX: Remove tracking query parameters (utm_source, fbclid, etc.)
    - FIX: Normalize HTTP to HTTPS
    - FIX: Remove URL fragments (#anchor)
    """
    try:
        from urllib.parse import urlparse, parse_qs, urlencode
        
        parsed = urlparse(url.lower().strip())
        
        # Normalize HTTP to HTTPS (same content, different protocol)
        scheme = 'https' if parsed.scheme in ('http', 'https') else parsed.scheme
        
        # Remove tracking parameters
        tracking_params = [
            # UTM parameters
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
            # Click tracking
            "fbclid", "gclid", "msclkid", "dclid", "twclid", "igshid",
            "mc_cid", "mc_eid",
            # Other tracking
            "ref", "ref_src", "ref_url", "source", "via", "utm_id",
            # Social tracking
            "share_source", "share_medium", "share_campaign",
            # Content delivery
            "__twitter_impression", "s", "si",
        ]
        
        qs = parse_qs(parsed.query)
        clean_qs = {k: v for k, v in qs.items() if k not in tracking_params}
        clean_query = urlencode(clean_qs, doseq=True)
        
        # Reconstruct URL with normalized scheme
        # FIX: Remove fragment (#anchor) as it refers to same content
        normalized = parsed._replace(
            scheme=scheme,
            query=clean_query,
            fragment=''  # Remove fragment
        ).geturl()
        
        # Remove trailing slash
        normalized = normalized.rstrip('/')
        
        # Remove www prefix
        normalized = re.sub(r'^https?://www\.', r'https://', normalized)
        
        return normalized
    except Exception:
        # Fallback to basic normalization
        url = url.lower().strip()
        url = url.rstrip('/')
        url = re.sub(r'^https?://www\.', r'https://', url)
        # Remove fragment in fallback
        url = url.split('#')[0]
        return url


async def is_duplicate(
    session: AsyncSession,
    title: str,
    url: str,
    dedup_window_days: int = 7,
) -> bool:
    """
    Check if an article is duplicate based on URL or title similarity.

    FIX: Now checks against ALL in-progress states to prevent race condition.

    Uses:
    1. URL exact match (normalized)
    2. Title hash exact match
    3. Title similarity > 0.7 using pg_trgm
    """
    title_hash = hash_title(title)
    url_normalized = normalize_url_for_dedup(url)
    window = datetime.utcnow() - timedelta(days=dedup_window_days)

    # Check 1: URL exact match (check all states - URL dedup is always valid)
    stmt = select(Article).where(
        and_(
            Article.original_url == url_normalized,
            Article.created_at >= window,
        )
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        logger.debug(f"Duplicate by URL: {url_normalized}")
        return True

    # Check 2: Title hash exact match (check in-progress states only)
    stmt = select(Article).where(
        and_(
            Article.title_hash == title_hash,
            Article.state.in_(IN_PROGRESS_STATES),
            Article.created_at >= window,
        )
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        logger.debug(f"Duplicate by title hash: {title[:50]}")
        return True

    # Check 3: pg_trgm similarity (check in-progress states only)
    # Only if title is long enough for meaningful comparison
    if len(title) < 20:
        return False

    try:
        # Use raw SQL for trgm similarity - check in-progress states
        stmt = text("""
            SELECT id FROM articles
            WHERE created_at >= :window
            AND state IN :states
            AND similarity(normalize_title(original_title), :norm_title) > 0.7
            LIMIT 1
        """)
        result = await session.execute(stmt, {
            "window": window,
            "norm_title": normalize_title_for_hash(title),
            "states": tuple(IN_PROGRESS_STATES),
        })
        if result.scalar_one_or_none():
            logger.debug(f"Duplicate by title similarity: {title[:50]}")
            return True
    except Exception as e:
        logger.warning(f"Trgm similarity check failed: {e}")

    return False


async def count_signals_in_window(
    session: AsyncSession,
    title: str,
    window_hours: int = 24,
) -> int:
    """
    Count how many signals with similar titles exist in the time window.
    Used for trend scoring.
    """
    window = datetime.utcnow() - timedelta(hours=window_hours)
    title_hash = hash_title(title)
    norm_title = normalize_title_for_hash(title)

    try:
        stmt = text("""
            SELECT COUNT(*) FROM articles
            WHERE created_at >= :window
            AND (
                title_hash = :hash
                OR similarity(normalize_title(original_title), :norm_title) > 0.5
            )
        """)
        result = await session.execute(stmt, {
            "window": window,
            "hash": title_hash,
            "norm_title": norm_title,
        })
        count = result.scalar()
        return int(count) if count else 0
    except Exception as e:
        logger.warning(f"Signal count query failed: {e}")
        return 0
