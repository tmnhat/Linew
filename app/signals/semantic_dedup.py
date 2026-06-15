"""
Semantic deduplication using keyword-based similarity.
Faster and doesn't require external API.
"""
import logging
import re
from typing import Optional
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleState
from app.models.article_states import DEDUP_CHECK_STATES

logger = logging.getLogger(__name__)

# Similarity threshold (0.0 - 1.0)
# FIX: Increased from 0.30 to 0.45 to reduce false positives
# 0.45 = articles must share at least 45% keywords to be considered duplicates
# This prevents different articles about similar topics from being marked as duplicates
SEMANTIC_SIMILARITY_THRESHOLD = 0.45

# Minimum shared keywords to consider as potential duplicate
# FIX: Increased from 7 to 10 to require more shared keywords
MIN_SHARED_KEYWORDS = 10


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Lowercase
    title = title.lower()
    # Remove special characters
    title = re.sub(r'[^\w\s]', ' ', title)
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def extract_keywords(title: str) -> set[str]:
    """Extract important keywords from title."""
    words = normalize_title(title).split()
    
    # Common stopwords to exclude
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
        'what', 'which', 'who', 'whom', 'how', 'why', 'when', 'where',
        'vs', 'vs.', 'v', 'v.', 'các', 'và', 'của', 'là', 'có', 'được',
        'nào', 'gì', 'ra', 'về', 'hay', 'hay', 'nên', 'để', 'từ', 'trong',
    }
    
    # Filter: length > 2, not stopword
    keywords = {w for w in words if len(w) > 2 and w not in stopwords}
    return keywords


def keyword_similarity(title1: str, title2: str) -> float:
    """Calculate similarity based on shared keywords."""
    keywords1 = extract_keywords(title1)
    keywords2 = extract_keywords(title2)
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(keywords1 & keywords2)
    union = len(keywords1 | keywords2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


async def check_semantic_duplicate(
    session: AsyncSession,
    article: Article,
    window_hours: int = 72,
) -> dict:
    """
    Check if article is semantically similar to recently published articles.

    Uses keyword-based similarity for efficiency.

    Returns:
        {
            "is_duplicate": bool,
            "similar_article_id": str (optional),
            "similarity_score": float (optional),
            "similar_title": str (optional),
        }
    """
    if not article.original_title:
        return {"is_duplicate": False}

    # Find recently published/approved articles to compare
    # FIX: Check against ALL in-progress states to prevent race condition
    from datetime import datetime, timedelta
    window = datetime.utcnow() - timedelta(hours=window_hours)

    stmt = select(Article).where(
        Article.created_at >= window,
        Article.state.in_(DEDUP_CHECK_STATES),  # Use in-progress states
        Article.id != article.id,
    )
    result = await session.execute(stmt)
    recent_articles = result.scalars().all()

    if not recent_articles:
        return {"is_duplicate": False}

    # Calculate similarity with all recent articles
    max_similarity = 0.0
    most_similar = None
    shared_keywords = []

    current_keywords = extract_keywords(article.original_title)

    for recent in recent_articles:
        if not recent.original_title:
            continue
        
        similarity = keyword_similarity(article.original_title, recent.original_title)
        
        if similarity > max_similarity:
            max_similarity = similarity
            most_similar = recent
            shared_keywords = list(current_keywords & extract_keywords(recent.original_title))

    logger.debug(
        f"Keyword similarity for '{article.original_title[:50]}': "
        f"max_sim={max_similarity:.3f}, threshold={SEMANTIC_SIMILARITY_THRESHOLD}, "
        f"shared={shared_keywords[:5]}"
    )

    if max_similarity >= SEMANTIC_SIMILARITY_THRESHOLD and most_similar:
        logger.warning(
            f"SEMANTIC DUPLICATE DETECTED: '{article.original_title[:50]}' "
            f"(ID: {article.id}) is {max_similarity:.0%} similar to "
            f"'{most_similar.original_title[:50]}' (ID: {most_similar.id}) "
            f"via keywords: {shared_keywords[:5]}"
        )
        return {
            "is_duplicate": True,
            "similar_article_id": str(most_similar.id),
            "similarity_score": max_similarity,
            "similar_title": most_similar.original_title,
            "similar_wp_url": most_similar.wp_url,
        }

    return {"is_duplicate": False}
