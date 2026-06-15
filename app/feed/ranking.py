"""
Smart Feed Ranking Algorithm.

This module implements an AI-powered ranking system that considers:
- Recency: Recent articles get higher scores
- Trend: Articles with high trend scores rank higher
- Breaking News: Breaking news gets priority boost
- Category Preference: Match user's preferred categories
- Content Quality: Based on word count and analysis
- Seen Penalty: Articles already read get significantly reduced score
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleState


@dataclass
class RankingConfig:
    """Configuration for ranking weights."""
    recency_weight: float = 1.0
    trend_weight: float = 1.0
    breaking_weight: float = 1.0
    category_weight: float = 1.0
    quality_weight: float = 1.0

    preference_tech: float = 0.5
    preference_finance: float = 0.5


@dataclass
class RankingResult:
    """Result of ranking calculation."""
    article_id: str
    score: float
    components: dict


async def is_breaking_news(db: AsyncSession, article_id: str) -> bool:
    """
    Check if an article is marked as breaking news.
    """
    from app.models import Article
    from uuid import UUID

    result = await db.execute(
        select(Article).where(Article.id == UUID(article_id))
    )
    article = result.scalar_one_or_none()

    if not article:
        return False

    return article.article_type == "breaking"


def calculate_recency_score(
    published_at: Optional[datetime],
    max_age_hours: int = 24
) -> float:
    """
    Calculate recency score (0-30 points).

    - 30 points: Published within last hour
    - Decreases linearly to 0 points at max_age_hours
    """
    if not published_at:
        return 0.0

    # Handle timezone-aware vs naive datetime
    now = datetime.utcnow()
    if published_at.tzinfo is not None:
        # If published_at is timezone-aware, convert now to UTC without timezone
        published_at = published_at.replace(tzinfo=None) - published_at.utcoffset()
    
    age = now - published_at

    if age < timedelta(hours=1):
        return 30.0
    elif age > timedelta(hours=max_age_hours):
        return 0.0
    else:
        hours = age.total_seconds() / 3600
        return max(0.0, 30.0 * (1 - hours / max_age_hours))


def calculate_trend_score(
    trend_score: Optional[float],
    max_score: float = 20.0
) -> float:
    """
    Calculate trend bonus (0-20 points).

    Trend score from article (0-1) maps to 0-20 points.
    """
    if trend_score is None:
        return 0.0

    return min(max_score, trend_score * max_score * 100)


def calculate_breaking_bonus(
    article_type: str,
    max_bonus: float = 25.0
) -> float:
    """
    Calculate breaking news bonus (0-25 points).

    Breaking news and urgent articles get priority boost.
    """
    if article_type == "breaking":
        return max_bonus
    elif article_type == "urgent":
        return max_bonus * 0.8
    else:
        return 0.0


def calculate_category_score(
    category: Optional[str],
    config: RankingConfig
) -> float:
    """
    Calculate category preference score (0-15 points).

    Matches user's preference with article category.
    """
    if not category:
        return 0.0

    category_lower = category.lower()

    tech_keywords = ["tech", "technology", "ai", "crypto", "cryptocurrency", "gaming"]
    finance_keywords = ["finance", "business", "stock", "market", "economy"]

    score = 0.0

    if any(kw in category_lower for kw in tech_keywords):
        score += config.preference_tech * 15.0
    elif any(kw in category_lower for kw in finance_keywords):
        score += config.preference_finance * 15.0
    else:
        score = 7.5

    return min(15.0, score)


def calculate_quality_score(
    word_count: Optional[int],
    trend_score: Optional[float]
) -> float:
    """
    Calculate content quality score (0-10 points).

    Based on word count and trend score.
    """
    score = 0.0

    if word_count:
        if word_count >= 1000:
            score += 5.0
        elif word_count >= 500:
            score += 3.0
        elif word_count >= 200:
            score += 2.0
        else:
            score += 1.0

    if trend_score and trend_score > 0.7:
        score += 5.0
    elif trend_score and trend_score > 0.5:
        score += 3.0
    elif trend_score and trend_score > 0.3:
        score += 1.0

    return min(10.0, score)


def calculate_seen_penalty(is_read: bool) -> float:
    """
    Calculate penalty for already read articles (-100 points).
    """
    if is_read:
        return -100.0
    return 0.0


async def calculate_ranking_score(
    db: AsyncSession,
    article: Article,
    config: Optional[RankingConfig] = None,
    read_article_ids: Optional[set] = None
) -> RankingResult:
    """
    Calculate the ranking score for a single article.

    Components:
    - Recency Bonus: 0-30 points
    - Trend Bonus: 0-20 points
    - Breaking News Bonus: 0-25 points
    - Category Preference: 0-15 points
    - Content Quality: 0-10 points
    - Seen Penalty: -100 if already read
    """
    if config is None:
        config = RankingConfig()

    if read_article_ids is None:
        read_article_ids = set()

    is_read = str(article.id) in read_article_ids

    recency = calculate_recency_score(article.published_at)
    trend = calculate_trend_score(article.trend_score)
    breaking = calculate_breaking_bonus(article.article_type)
    category = calculate_category_score(article.category, config)
    quality = calculate_quality_score(article.word_count, article.trend_score)
    seen_penalty = calculate_seen_penalty(is_read)

    total_score = (
        recency * config.recency_weight +
        trend * config.trend_weight +
        breaking * config.breaking_weight +
        category * config.category_weight +
        quality * config.quality_weight +
        seen_penalty
    )

    components = {
        "recency": round(recency, 2),
        "trend": round(trend, 2),
        "breaking": round(breaking, 2),
        "category": round(category, 2),
        "quality": round(quality, 2),
        "seen_penalty": round(seen_penalty, 2),
        "is_read": is_read,
    }

    return RankingResult(
        article_id=str(article.id),
        score=round(total_score, 2),
        components=components
    )


async def rank_articles(
    db: AsyncSession,
    articles: list[Article],
    config: Optional[RankingConfig] = None,
    exclude_ids: Optional[set] = None
) -> list[RankingResult]:
    """
    Rank a list of articles and return sorted results.

    Articles are sorted by score in descending order.
    Read articles are pushed to the bottom.
    """
    if config is None:
        config = RankingConfig()

    if exclude_ids is None:
        exclude_ids = set()

    results = []
    for article in articles:
        if str(article.id) not in exclude_ids:
            result = await calculate_ranking_score(
                db, article, config, exclude_ids
            )
            results.append(result)

    results.sort(key=lambda x: x.score, reverse=True)

    return results


async def get_published_articles(
    db: AsyncSession,
    category: Optional[str] = None,
    limit: int = 100,
    hours_back: int = 72
) -> list[Article]:
    """
    Fetch published articles for ranking.

    Args:
        db: Database session
        category: Optional category filter
        limit: Maximum number of articles to fetch
        hours_back: How far back to look for articles

    Returns:
        List of published Article objects
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours_back)

    stmt = select(Article).where(
        Article.state == ArticleState.PUBLISHED.value,
        Article.published_at >= cutoff,
        Article.published_at.isnot(None)
    )

    if category and category != "all":
        stmt = stmt.where(Article.category == category)

    stmt = stmt.order_by(Article.published_at.desc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())
