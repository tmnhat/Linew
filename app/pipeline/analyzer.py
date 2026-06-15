"""
Article analyzer - categorization and trend scoring.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import ai_gateway
from app.core.ai_presets import CATEGORIZE_PROMPT
from app.models.article import Article
from app.models.source import Source

logger = logging.getLogger(__name__)

# Map AI categories to English dashboard categories
CATEGORY_MAP = {
    # Technology
    "tech": "Technology",
    "technology": "Technology",
    "ai": "Technology",
    "software": "Technology",
    "hardware": "Technology",
    "internet": "Technology",
    "science": "Technology",
    "robotics": "Technology",
    "cybersecurity": "Technology",
    "gadget": "Technology",
    "digital": "Technology",
    # Finance
    "finance": "Finance",
    "financial": "Finance",
    "stock": "Finance",
    "stocks": "Finance",
    "crypto": "Finance",
    "cryptocurrency": "Finance",
    "banking": "Finance",
    "economy": "Finance",
    "business": "Finance",
    "investment": "Finance",
    "market": "Finance",
    "trading": "Finance",
    # Sports
    "sports": "Sports",
    "football": "Sports",
    "soccer": "Sports",
    "basketball": "Sports",
    "tennis": "Sports",
    "golf": "Sports",
    "olympics": "Sports",
    "racing": "Sports",
    "motorsport": "Sports",
    "ufc": "Sports",
    "boxing": "Sports",
    "nba": "Sports",
    "nfl": "Sports",
    # Entertainment
    "entertainment": "Entertainment",
    "movie": "Entertainment",
    "movies": "Entertainment",
    "film": "Entertainment",
    "music": "Entertainment",
    "celebrity": "Entertainment",
    "hollywood": "Entertainment",
    "tv": "Entertainment",
    "streaming": "Entertainment",
    "netflix": "Entertainment",
    "game": "Entertainment",
    "gaming": "Entertainment",
    "esports": "Entertainment",
    "concert": "Entertainment",
    # Health
    "health": "Health",
    "healthcare": "Health",
    "medical": "Health",
    "medicine": "Health",
    "wellness": "Health",
    "fitness": "Health",
    "diet": "Health",
    "nutrition": "Health",
    "mental health": "Health",
    "disease": "Health",
    "vaccine": "Health",
    # Education
    "education": "Education",
    "university": "Education",
    "school": "Education",
    "college": "Education",
    "student": "Education",
    "learning": "Education",
    "academic": "Education",
    "exam": "Education",
    "research": "Education",
    "study": "Education",
    # Politics
    "politics": "Politics",
    "political": "Politics",
    "government": "Politics",
    "election": "Politics",
    "congress": "Politics",
    "senate": "Politics",
    "parliament": "Politics",
    "policy": "Politics",
    "law": "Politics",
    "vote": "Politics",
    "trump": "Politics",
    "biden": "Politics",
    "white house": "Politics",
    # World
    "world": "World",
    "international": "World",
    "global": "World",
    "europe": "World",
    "asia": "World",
    "china": "World",
    "russia": "World",
    "ukraine": "World",
    "middle east": "World",
    "diplomatic": "World",
    "foreign": "World",
    "nato": "World",
    # Science (thay Exploration)
    "exploration": "Science",
    "discover": "Science",
    "space": "Science",
    "nasa": "Science",
    "mars": "Science",
    "ocean": "Science",
    "archaeology": "Science",
    "nature": "Science",
    "animal": "Science",
    "wildlife": "Science",
    "environment": "Science",
    "climate": "Science",
    # Business (thay Automotive)
    "auto": "Business",
    "automotive": "Business",
    "car": "Business",
    "cars": "Business",
    "vehicle": "Business",
    "electric vehicle": "Business",
    "ev": "Business",
    "tesla": "Business",
    "toyota": "Business",
    "ford": "Business",
    "bmw": "Business",
    "mercedes": "Business",
    "luxury car": "Business",
    # Other
    "other": "Other",
}


def map_category(category: str) -> str:
    """Map English category to dashboard category."""
    return CATEGORY_MAP.get(category.lower(), CATEGORY_MAP.get(category, "Other"))


async def categorize_article(session: AsyncSession, article: Article) -> dict:
    """
    Categorize article using AI (light model).
    Returns {category, confidence}.
    """
    try:
        # Build prompt
        prompt = CATEGORIZE_PROMPT.format(
            title=article.original_title,
            summary=article.original_summary or "",
        )

        # Call AI
        response = await ai_gateway.call_ai(
            prompt=prompt,
            task_type="categorize",
            response_format={"type": "json_object"},
            max_tokens=256,
            temperature=0.3,
        )

        raw_category = response.get("category", "other")
        confidence = float(response.get("confidence", 0.0))
        
        # Map to dashboard category (Vietnamese)
        category = map_category(raw_category)

        logger.info(f"Categorized article {article.id}: {raw_category} -> {category} ({confidence:.2f})")

        return {
            "category": category,
            "confidence": confidence,
        }

    except Exception as e:
        logger.error(f"Failed to categorize article {article.id}: {e}")
        return {
            "category": "other",
            "confidence": 0.0,
        }


async def count_signal_frequency(
    session: AsyncSession,
    title: str,
    window_hours: int = 24,
) -> int:
    """Count similar signals in the time window."""
    window = datetime.utcnow() - timedelta(hours=window_hours)

    try:
        stmt = text("""
            SELECT COUNT(*) FROM articles
            WHERE created_at >= :window
            AND original_title % :title
        """)
        result = await session.execute(stmt, {
            "window": window,
            "title": title,
        })
        count = result.scalar()
        return int(count) if count else 0
    except Exception as e:
        logger.warning(f"Signal frequency query failed: {e}")
        return 0


def score_trend(
    signal_frequency: int,
    article_age_hours: float,
    source_authority: str,
    base_score: float = 15.0,
) -> float:
    """
    Calculate trend score (0-1) based on rule-based factors.

    Factors:
    - signal_frequency: +30 max (many sources = trending)
    - recency: +20 max (< 2 hours = very fresh)
    - source_authority: +15 max (high authority)
    - base: +15

    Max = 80, normalize to 0-1
    """
    score = base_score  # Base score

    # Signal frequency (0-30)
    freq_score = min(signal_frequency * 5, 30)
    score += freq_score

    # Recency (0-20)
    if article_age_hours < 2:
        recency_score = 20
    elif article_age_hours < 6:
        recency_score = 15
    elif article_age_hours < 12:
        recency_score = 10
    elif article_age_hours < 24:
        recency_score = 5
    else:
        recency_score = 0
    score += recency_score

    # Source authority (0-15)
    authority_map = {"high": 15, "medium": 10, "low": 5}
    authority_score = authority_map.get(source_authority.lower(), 10)
    score += authority_score

    # Normalize to 0-1
    trend_score = min(score / 80.0, 1.0)
    return round(trend_score, 3)


async def score_article_trend(session: AsyncSession, article: Article) -> dict:
    """
    Score article trend based on multiple factors.
    """
    try:
        # Get source authority
        source_authority = "medium"
        if article.source_id:
            result = await session.execute(
                select(Source.crawl_difficulty).where(Source.id == article.source_id)
            )
            row = result.scalar_one_or_none()
            if row:
                difficulty = row
                if difficulty == "easy":
                    source_authority = "high"
                elif difficulty == "hard":
                    source_authority = "low"

        # Calculate signal frequency
        signal_freq = await count_signal_frequency(session, article.original_title)

        # Calculate age (use timezone-aware datetime to avoid offset-naive/-aware mismatch)
        from datetime import timezone
        article_age_hours = 0
        now = datetime.now(timezone.utc)
        
        if article.signal_published_at:
            # Ensure both datetimes are timezone-aware for comparison
            signal_time = article.signal_published_at
            if signal_time.tzinfo is None:
                signal_time = signal_time.replace(tzinfo=timezone.utc)
            age = now - signal_time
            article_age_hours = age.total_seconds() / 3600
        elif article.created_at:
            created = article.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age = now - created
            article_age_hours = age.total_seconds() / 3600

        # Calculate trend score
        trend_score = score_trend(
            signal_frequency=signal_freq,
            article_age_hours=article_age_hours,
            source_authority=source_authority,
        )

        logger.info(
            f"Trend score for article {article.id}: {trend_score} "
            f"(freq={signal_freq}, age={article_age_hours:.1f}h, auth={source_authority})"
        )

        return {
            "trend_score": trend_score,
            "signal_frequency": signal_freq,
        }

    except Exception as e:
        logger.error(f"Failed to score trend for article {article.id}: {e}")
        return {
            "trend_score": 0.0,
            "signal_frequency": 0,
        }
