"""
Signals API routes - sources management.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.source import Source
from app.signals.service import fetch_all_sources, fetch_source
from app.signals.rss_crawler import parse_feed, normalize_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    feed_url: str
    site_url: Optional[str] = None
    category_hint: Optional[str] = None
    language: str = "en"
    crawl_difficulty: str = "easy"
    requires_flaresolverr: bool = False
    requires_proxy: bool = False
    is_paywall: bool = False
    content_selector: Optional[str] = None
    notes: Optional[str] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    feed_url: Optional[str] = None
    site_url: Optional[str] = None
    category_hint: Optional[str] = None
    language: Optional[str] = None
    crawl_difficulty: Optional[str] = None
    requires_flaresolverr: Optional[bool] = None
    requires_proxy: Optional[bool] = None
    is_paywall: Optional[bool] = None
    content_selector: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SourceResponse(BaseModel):
    id: str
    name: str
    feed_url: str
    site_url: Optional[str]
    category_hint: Optional[str]
    language: str
    is_active: bool
    crawl_difficulty: str
    requires_flaresolverr: bool
    last_fetched_at: Optional[str]
    last_error: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all RSS sources."""
    stmt = select(Source)
    if is_active is not None:
        stmt = stmt.where(Source.is_active == is_active)
    stmt = stmt.order_by(Source.name)

    result = await db.execute(stmt)
    sources = result.scalars().all()
    return [s.to_dict() for s in sources]


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single source by ID."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source.to_dict()


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(
    data: SourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new RSS source."""
    # Check if feed_url already exists
    result = await db.execute(select(Source).where(Source.feed_url == data.feed_url))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Feed URL already exists")

    source = Source(
        name=data.name,
        feed_url=data.feed_url,
        site_url=data.site_url,
        category_hint=data.category_hint,
        language=data.language,
        crawl_difficulty=data.crawl_difficulty,
        requires_flaresolverr=data.requires_flaresolverr,
        requires_proxy=data.requires_proxy,
        is_paywall=data.is_paywall,
        content_selector=data.content_selector,
        notes=data.notes,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source.to_dict()


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: UUID,
    data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an RSS source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)

    await db.commit()
    await db.refresh(source)
    return source.to_dict()


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an RSS source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.delete(source)
    await db.commit()


@router.post("/fetch")
async def fetch_sources(
    source_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """Fetch RSS feeds from sources."""
    if source_id:
        try:
            source_uuid = UUID(source_id)
            result = await db.execute(select(Source).where(Source.id == source_uuid))
            source = result.scalar_one_or_none()
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
            articles = await fetch_source(db, source)
            return {
                "message": f"Fetched {len(articles)} articles",
                "sources_fetched": 1,
                "articles_created": len(articles),
            }
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid source ID")
    else:
        # Fetch all active sources
        result = await fetch_all_sources(db)
        return {
            "message": f"Fetched {result['sources_fetched']} sources, {result['articles_created']} articles",
            **result,
        }


class TestFeedRequest(BaseModel):
    feed_url: str


class TestFeedResponse(BaseModel):
    valid: bool
    title: Optional[str] = None
    items: list[dict]
    error: Optional[str] = None


@router.post("/test", response_model=TestFeedResponse)
async def test_feed(
    data: TestFeedRequest,
    db: AsyncSession = Depends(get_db),
):
    """Test if a feed URL is valid and returns items."""
    try:
        signals = parse_feed(data.feed_url)
        if signals:
            return TestFeedResponse(
                valid=True,
                title=signals[0].title if signals else None,  # Get feed title
                items=[{"title": s.title, "url": s.url} for s in signals[:10]],
            )
        else:
            return TestFeedResponse(
                valid=False,
                items=[],
                error="No items found in feed",
            )
    except Exception as e:
        return TestFeedResponse(
            valid=False,
            items=[],
            error=str(e),
        )


class DiscoverFeedRequest(BaseModel):
    site_url: str


class DiscoverFeedResponse(BaseModel):
    found: bool
    feed_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/discover", response_model=DiscoverFeedResponse)
async def discover_feed(
    data: DiscoverFeedRequest,
    db: AsyncSession = Depends(get_db),
):
    """Discover RSS feed from a website URL."""
    import httpx

    common_paths = [
        "/feed", "/rss", "/feed.xml", "/rss.xml",
        "/atom.xml", "/index.xml", "/feed/rss",
    ]

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for path in common_paths:
            feed_url = data.site_url.rstrip("/") + path
            try:
                response = await client.get(feed_url)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "xml" in content_type or "rss" in content_type or "atom" in content_type:
                        return DiscoverFeedResponse(found=True, feed_url=feed_url)
            except Exception:
                continue

    return DiscoverFeedResponse(found=False, error="No RSS feed found")


# =============================================================================
# Reset Signals & Articles Endpoints
# =============================================================================

class ResetSignalsRequest(BaseModel):
    """Request to reset signals for re-collection."""
    unprocess_raw_signals: bool = True  # Mark raw_signals as unprocessed
    reset_articles_to_signal_collected: bool = True  # Reset articles to SIGNAL_COLLECTED
    delete_duplicates: bool = False  # Delete duplicate articles
    categories: Optional[list[str]] = None  # Only reset articles in these categories


class ResetSignalsResponse(BaseModel):
    """Response from reset operation."""
    success: bool
    message: str
    raw_signals_reset: int
    articles_reset: int
    articles_deleted: int


@router.post("/reset", response_model=ResetSignalsResponse)
async def reset_signals(
    data: ResetSignalsRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """
    Reset signals and articles to allow re-collection.

    This is useful when:
    - You want to re-process signals that were already processed
    - You want to get new signals from the same sources
    - You want to restart the pipeline with fresh signals

    Options:
    - unprocess_raw_signals: Mark all processed raw_signals as unprocessed
    - reset_articles_to_signal_collected: Reset articles back to SIGNAL_COLLECTED state
    - delete_duplicates: Delete duplicate articles to free up space
    - categories: Only reset articles in specific categories (None = all)
    """
    from datetime import datetime
    from app.models.raw_signal import RawSignal
    from app.models.article import Article, ArticleState

    results = {
        "raw_signals_reset": 0,
        "articles_reset": 0,
        "articles_deleted": 0,
    }

    # 1. Reset raw_signals: mark was_processed = False
    if data.unprocess_raw_signals:
        from sqlalchemy import update

        stmt = (
            update(RawSignal)
            .where(RawSignal.was_processed == True)  # noqa: E712
            .values(
                was_processed=False,
                article_id=None,
                processing_result=None,
                processed_at=None,
            )
        )
        result = await db.execute(stmt)
        results["raw_signals_reset"] = result.rowcount
        logger.info(f"Reset {result.rowcount} raw_signals to unprocessed")

    # 2. Reset articles to SIGNAL_COLLECTED
    if data.reset_articles_to_signal_collected:
        from sqlalchemy import update

        # Define states to reset (not PUBLISHED, APPROVED, REJECTED)
        states_to_reset = [
            ArticleState.SIGNAL_COLLECTED.value,
            ArticleState.CATEGORIZED.value,
            ArticleState.TRENDING.value,
            ArticleState.SKIPPED.value,
            ArticleState.EXPIRED.value,
            ArticleState.RESEARCHED.value,
            ArticleState.WRITTEN.value,
            ArticleState.GOVERNED.value,
            ArticleState.FAILED.value,
        ]

        if data.categories:
            # Only reset articles in specific categories
            stmt = (
                update(Article)
                .where(
                    and_(
                        Article.state.in_(states_to_reset),
                        Article.category.in_(data.categories),
                    )
                )
                .values(
                    state=ArticleState.SIGNAL_COLLECTED.value,
                    category=None,
                    category_confidence=None,
                    trend_score=None,
                    queued_at=None,
                    priority=50,
                    fail_reason=None,
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            # Reset all articles in those states
            stmt = (
                update(Article)
                .where(Article.state.in_(states_to_reset))
                .values(
                    state=ArticleState.SIGNAL_COLLECTED.value,
                    category=None,
                    category_confidence=None,
                    trend_score=None,
                    queued_at=None,
                    priority=50,
                    fail_reason=None,
                    updated_at=datetime.utcnow(),
                )
            )

        result = await db.execute(stmt)
        results["articles_reset"] = result.rowcount
        logger.info(f"Reset {result.rowcount} articles to SIGNAL_COLLECTED")

    # 3. Delete duplicate articles (optional)
    if data.delete_duplicates:
        from sqlalchemy import delete, func

        # Find duplicate articles by title_hash (keep the newest, delete older)
        # Subquery to find IDs to delete
        subq = (
            select(Article.id)
            .where(Article.state.in_([
                ArticleState.SIGNAL_COLLECTED.value,
                ArticleState.SKIPPED.value,
                ArticleState.EXPIRED.value,
            ]))
            .order_by(Article.created_at.desc())
        )

        # Get all articles with duplicate title_hash
        dup_query = (
            select(Article.title_hash, func.count(Article.id).label("count"))
            .group_by(Article.title_hash)
            .having(func.count(Article.id) > 1)
        )
        dup_result = await db.execute(dup_query)
        duplicate_hashes = [row.title_hash for row in dup_result.all()]

        if duplicate_hashes:
            # Delete older duplicates
            stmt = (
                delete(Article)
                .where(
                    and_(
                        Article.title_hash.in_(duplicate_hashes),
                        Article.state.in_([
                            ArticleState.SIGNAL_COLLECTED.value,
                            ArticleState.SKIPPED.value,
                            ArticleState.EXPIRED.value,
                        ]),
                    )
                )
            )
            result = await db.execute(stmt)
            results["articles_deleted"] = result.rowcount
            logger.info(f"Deleted {result.rowcount} duplicate articles")

    await db.commit()

    return ResetSignalsResponse(
        success=True,
        message=f"Reset completed: {results['raw_signals_reset']} signals, {results['articles_reset']} articles reset, {results['articles_deleted']} deleted",
        **results,
    )


# =============================================================================
# Hard Reset - Delete All Signals & Articles
# =============================================================================

class HardResetRequest(BaseModel):
    """Request to completely delete all signals and articles."""
    delete_raw_signals: bool = True  # Delete all raw_signals
    delete_articles: bool = True  # Delete all articles (except optionally PUBLISHED)
    keep_published: bool = True  # Keep PUBLISHED articles
    reset_sources: bool = False  # Reset source last_fetched_at


class ResetByCategoryRequest(BaseModel):
    """Request to boost articles in specific categories."""
    categories: list[str]
    limit: int = 50


class ResetByCategoryResponse(BaseModel):
    """Response from category reset."""
    success: bool
    message: str
    articles_boosted: int
    categories_boosted: list[str]


@router.post("/reset/by-category", response_model=ResetByCategoryResponse)
async def reset_articles_by_category(
    data: ResetByCategoryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset and boost articles in specific categories.

    This is useful when you want to prioritize creating articles
    for categories that currently have few articles.

    The reset will:
    1. Set articles in specified categories back to SIGNAL_COLLECTED
    2. Increase their priority to 100 (maximum)
    3. Clear their queued_at to allow re-queuing
    """
    from datetime import datetime
    from sqlalchemy import update
    from app.models.article import Article, ArticleState

    states_to_reset = [
        ArticleState.SIGNAL_COLLECTED.value,
        ArticleState.CATEGORIZED.value,
        ArticleState.TRENDING.value,
        ArticleState.RESEARCHED.value,
    ]

    stmt = (
        update(Article)
        .where(
            and_(
                Article.category.in_(data.categories),
                Article.state.in_(states_to_reset),
            )
        )
        .values(
            state=ArticleState.SIGNAL_COLLECTED.value,
            priority=100,  # Maximum priority
            queued_at=None,
            fail_reason=None,
            updated_at=datetime.utcnow(),
        )
    )
    result = await db.execute(stmt)
    await db.commit()

    return ResetByCategoryResponse(
        success=True,
        message=f"Boosted {result.rowcount} articles in {len(data.categories)} categories",
        articles_boosted=result.rowcount,
        categories_boosted=data.categories,
    )


class HardResetResponse(BaseModel):
    """Response from hard reset operation."""
    success: bool
    message: str
    raw_signals_deleted: int
    articles_deleted: int


@router.post("/reset/hard", response_model=HardResetResponse)
async def hard_reset_signals(
    data: HardResetRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """
    HARD RESET - Delete ALL signals and articles to start fresh.

    ⚠️ WARNING: This is a destructive operation!
    - Deletes ALL raw_signals from the database
    - Deletes ALL articles (optionally keeping PUBLISHED ones)
    - This cannot be undone!

    Use this when:
    - You want to completely start over with fresh data
    - The pipeline is stuck with old signals
    - You want to free up database space
    """
    from sqlalchemy import delete
    from app.models.raw_signal import RawSignal
    from app.models.article import Article, ArticleState

    results = {
        "raw_signals_deleted": 0,
        "articles_deleted": 0,
    }

    # 1. Delete ALL raw_signals
    if data.delete_raw_signals:
        stmt = delete(RawSignal)
        result = await db.execute(stmt)
        results["raw_signals_deleted"] = result.rowcount
        logger.info(f"HARD RESET: Deleted {result.rowcount} raw_signals")

    # 2. Delete ALL articles (except PUBLISHED if keep_published=True)
    if data.delete_articles:
        if data.keep_published:
            # Keep PUBLISHED articles
            stmt = delete(Article).where(
                Article.state != ArticleState.PUBLISHED.value
            )
        else:
            # Delete ALL articles
            stmt = delete(Article)

        result = await db.execute(stmt)
        results["articles_deleted"] = result.rowcount
        logger.info(f"HARD RESET: Deleted {result.rowcount} articles")

    # 3. Reset source last_fetched_at (optional)
    if data.reset_sources:
        from datetime import datetime
        from sqlalchemy import update
        from app.models.source import Source

        stmt = update(Source).values(last_fetched_at=None)
        await db.execute(stmt)
        logger.info("HARD RESET: Reset all source last_fetched_at")

    await db.commit()

    return HardResetResponse(
        success=True,
        message=f"Hard reset completed: {results['raw_signals_deleted']} signals deleted, {results['articles_deleted']} articles deleted",
        **results,
    )
