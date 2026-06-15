"""
Smart Feed API Routes.

This module provides AI-powered feed endpoints with:
- Personalized ranking based on user preferences
- Breaking news prioritization
- Trend-aware article ordering
- Read history tracking (via client-provided IDs)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.article import Article, ArticleState
from app.feed.ranking import (
    RankingConfig,
    rank_articles,
    get_published_articles,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feed", tags=["feed"])


# =============================================================================
# Response Models
# =============================================================================

class ArticleCard(BaseModel):
    """Article card for feed display."""
    id: str
    title: str
    excerpt: str
    thumbnail: str
    category: str
    date: str
    date_ago: str
    url: str
    is_new: bool
    is_breaking: bool
    author: str
    views: int
    read_time_minutes: int
    ranking_score: float = 0


class FeedResponse(BaseModel):
    """Response for feed endpoint."""
    articles: list[ArticleCard]
    has_more: bool
    page: int
    per_page: int
    total: int
    server_time: str


class MissedSectionResponse(BaseModel):
    """Response for missed articles section."""
    articles: list[ArticleCard]
    count: int


# =============================================================================
# Helper Functions
# =============================================================================

def generate_excerpt(content: Optional[str], max_length: int = 150) -> str:
    """Generate excerpt from content, removing HTML tags."""
    if not content:
        return ""

    text = re.sub(r'<[^>]+>', ' ', content)
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) > max_length:
        return text[:max_length].rsplit(' ', 1)[0] + '...'

    return text


def estimate_read_time(word_count: Optional[int]) -> int:
    """Estimate read time in minutes based on word count."""
    if not word_count:
        return 3

    words_per_minute = 200
    minutes = max(1, round(word_count / words_per_minute))
    return min(minutes, 30)


def get_thumbnail_url(article: Article) -> str:
    """Get thumbnail URL from article with fallbacks."""
    # Handle crawled_images - could be list of strings or list of dicts
    if article.crawled_images and len(article.crawled_images) > 0:
        first_image = article.crawled_images[0]
        if isinstance(first_image, str):
            return first_image
        elif isinstance(first_image, dict) and 'url' in first_image:
            return first_image['url']
        elif isinstance(first_image, dict) and 'src' in first_image:
            return first_image['src']

    if article.original_image_url:
        # Handle dict format
        if isinstance(article.original_image_url, dict):
            return article.original_image_url.get('url', article.original_image_url.get('src', ''))
        return article.original_image_url

    return get_category_placeholder(article.category)


def get_category_placeholder(category: Optional[str]) -> str:
    """Get placeholder image based on category."""
    placeholders = {
        "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=400&fit=crop",
        "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=400&fit=crop",
        "ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&h=400&fit=crop",
        "crypto": "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=600&h=400&fit=crop",
        "cryptocurrency": "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=600&h=400&fit=crop",
        "finance": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=400&fit=crop",
        "business": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&h=400&fit=crop",
        "stock": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=400&fit=crop",
        "market": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&h=400&fit=crop",
        "science": "https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=600&h=400&fit=crop",
        "gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&h=400&fit=crop",
        "entertainment": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&h=400&fit=crop",
        "health": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=600&h=400&fit=crop",
    }

    if category:
        category_lower = category.lower()
        for key, url in placeholders.items():
            if key in category_lower:
                return url

    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&h=400&fit=crop"


def format_time_ago(dt: datetime) -> str:
    """Format datetime as Vietnamese time ago string."""
    now = datetime.utcnow()
    # Handle timezone-aware datetime
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None) - dt.utcoffset()
    diff = now - dt

    intervals = {
        31536000: ("năm", "năm"),
        2592000: ("tháng", "tháng"),
        86400: ("ngày", "ngày"),
        3600: ("giờ", "giờ"),
        60: ("phút", "phút"),
        1: ("giây", "giây"),
    }

    for seconds, (singular, plural) in intervals.items():
        count = int(diff.total_seconds() / seconds)
        if count >= 1:
            return f"{count} {plural} trước"

    return "vừa xong"


def is_new_article(article: Article) -> bool:
    """Check if article is new (less than 24 hours old)."""
    if not article.published_at:
        return False

    now = datetime.utcnow()
    pub_at = article.published_at
    if pub_at.tzinfo is not None:
        pub_at = pub_at.replace(tzinfo=None) - pub_at.utcoffset()
    age = now - pub_at
    return age < timedelta(hours=24)


def is_breaking_article(article: Article) -> bool:
    """Check if article is marked as breaking."""
    return article.article_type == "breaking"


async def format_article_card(
    article: Article,
    ranking_score: float = 0
) -> ArticleCard:
    """Format article into feed card."""
    published_at = article.published_at or article.created_at
    date_str = published_at.isoformat() if published_at else datetime.utcnow().isoformat()
    date_ago = format_time_ago(published_at) if published_at else "không rõ"

    excerpt = generate_excerpt(
        article.original_summary or article.body_html or "",
        max_length=150
    )

    thumbnail = get_thumbnail_url(article)

    return ArticleCard(
        id=str(article.id),
        title=article.meta_title or article.original_title,
        excerpt=excerpt,
        thumbnail=thumbnail,
        category=article.category or "Tin tức",
        date=date_str,
        date_ago=date_ago,
        url=article.wp_url or article.original_url,
        is_new=is_new_article(article),
        is_breaking=is_breaking_article(article),
        author="Linews",
        views=0,
        read_time_minutes=estimate_read_time(article.word_count),
        ranking_score=ranking_score,
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=FeedResponse)
async def get_feed(
    offset: int = Query(0, ge=0, description="Offset for pagination (number of articles to skip)"),
    per_page: int = Query(12, ge=1, le=50, description="Articles per page"),
    category: Optional[str] = Query(None, description="Category filter: tech, finance, all"),
    exclude_read: Optional[str] = Query(None, description="Comma-separated article IDs to exclude (read posts)"),
    preference_tech: float = Query(0.5, ge=0, le=1, description="Tech preference weight"),
    preference_finance: float = Query(0.5, ge=0, le=1, description="Finance preference weight"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get personalized smart feed with AI-powered ranking.

    Features:
    - Recency scoring: Recent articles get higher scores
    - Trend awareness: High-trending articles are prioritized
    - Breaking news: Breaking news gets priority boost
    - Category matching: Matches user preferences
    - Content quality: Longer, well-researched articles score higher
    - Read exclusion: Articles already read are deprioritized
    """
    # Parse exclude_read IDs
    exclude_ids = set()
    if exclude_read:
        exclude_ids = set(exclude_read.split(","))

    config = RankingConfig(
        preference_tech=preference_tech,
        preference_finance=preference_finance,
    )

    articles = await get_published_articles(
        db,
        category=category if category and category != "all" else None,
        limit=500,
        hours_back=168,
    )

    ranked = await rank_articles(db, articles, config, exclude_ids)

    total = len(ranked)
    start = offset
    end = start + per_page
    page_results = ranked[start:end]

    article_cards = []
    for result in page_results:
        article_map = {str(a.id): a for a in articles}
        article = article_map.get(result.article_id)
        if article:
            card = await format_article_card(article, result.score)
            article_cards.append(card)

    return FeedResponse(
        articles=article_cards,
        has_more=end < total,
        page=offset // per_page + 1 if per_page > 0 else 1,
        per_page=per_page,
        total=total,
        server_time=datetime.utcnow().isoformat(),
    )


@router.get("/missed", response_model=MissedSectionResponse)
async def get_missed_articles(
    limit: int = Query(6, ge=1, le=20, description="Number of missed articles to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get "Bạn có thể đã bỏ lỡ" (You may have missed) section.

    Returns older articles that haven't been seen yet,
    sorted by a combination of recency and trend score.
    """
    cutoff = datetime.utcnow() - timedelta(hours=72)
    start_cutoff = datetime.utcnow() - timedelta(hours=168)

    stmt = (
        select(Article)
        .where(
            Article.state == ArticleState.PUBLISHED.value,
            Article.published_at >= start_cutoff,
            Article.published_at <= cutoff,
            Article.published_at.isnot(None),
        )
        .order_by(Article.trend_score.desc().nullslast(), Article.published_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    cards = []
    for article in articles:
        trend_bonus = (article.trend_score or 0) * 20 if article.trend_score else 0
        card = await format_article_card(article, ranking_score=trend_bonus)
        cards.append(card)

    return MissedSectionResponse(
        articles=cards,
        count=len(cards),
    )


@router.get("/categories")
async def get_feed_categories(db: AsyncSession = Depends(get_db)):
    """
    Get available feed categories with article counts.
    """
    stmt = (
        select(Article.category, func.count(Article.id).label("count"))
        .where(
            Article.state == ArticleState.PUBLISHED.value,
            Article.category.isnot(None),
            Article.published_at >= datetime.utcnow() - timedelta(days=7),
        )
        .group_by(Article.category)
        .order_by(func.count(Article.id).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    categories = [
        {"name": row[0], "count": row[1]}
        for row in rows
    ]

    return {
        "categories": categories,
        "total": sum(c["count"] for c in categories),
    }


@router.get("/breaking")
async def get_breaking_news(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Get latest breaking news articles.
    """
    stmt = (
        select(Article)
        .where(
            Article.state == ArticleState.PUBLISHED.value,
            Article.article_type == "breaking",
            Article.published_at >= datetime.utcnow() - timedelta(hours=24),
            Article.published_at.isnot(None),
        )
        .order_by(Article.published_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    cards = []
    for article in articles:
        card = await format_article_card(article, ranking_score=100)
        cards.append(card)

    return {
        "articles": cards,
        "count": len(cards),
    }
