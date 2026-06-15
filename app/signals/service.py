"""
Signals service - orchestrates RSS fetching, raw signal storage, dedup, and article creation.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleState
from app.models.article_states import IN_PROGRESS_STATES, DEDUP_CHECK_STATES
from app.models.source import Source
from app.models.raw_signal import RawSignal, hash_url, hash_title, hash_content
from app.signals.rss_crawler import parse_feed, RawSignal as RSSRawSignal
from app.signals.dedup import hash_title as hash_title_func, normalize_url_for_dedup
from app.core.redis import publish_event, CHANNEL_ARTICLE_EVENTS
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


# Semantic dedup threshold
# FIX: Increased from 0.25 to 0.35 to reduce false positives
# 0.35 = articles sharing at least 35% keywords are potential duplicates
# This is more aggressive than the dedicated semantic_dedup.py (0.40) because
# this check runs early during signal collection
SEMANTIC_THRESHOLD = 0.35


def extract_keywords(title: str) -> set:
    """Extract keywords from title for semantic dedup."""
    import re
    words = title.lower().split()
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                 'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
                 'what', 'which', 'who', 'how', 'why', 'when', 'where', 'vs', 'vs.',
                 'các', 'và', 'của', 'là', 'có', 'được', 'nào', 'gì', 'ra', 'về', 'hay', 'nên'}
    keywords = {w for w in words if len(w) > 2 and w not in stopwords}
    # Remove punctuation
    keywords = {re.sub(r'[^\w]', '', w) for w in keywords if re.sub(r'[^\w]', '', w)}
    return keywords


def keyword_similarity(title1: str, title2: str) -> float:
    """Calculate Jaccard similarity between two titles."""
    k1 = extract_keywords(title1)
    k2 = extract_keywords(title2)
    if not k1 or not k2:
        return 0.0
    return len(k1 & k2) / len(k1 | k2)


async def check_semantic_duplicate(session: AsyncSession, title: str, exclude_id: str = None, window_hours: int = 72) -> tuple:
    """
    Check if title is semantically similar to any recent article.
    Returns (is_duplicate, similar_title, similar_url) or (False, None, None).

    FIX: Now checks against ALL in-progress states to prevent race condition
    where multiple workers process similar articles simultaneously.
    """
    window = datetime.utcnow() - timedelta(hours=window_hours)

    # Check against ALL in-progress articles (not just published/approved)
    # This prevents race condition where 2 articles pass governance before either is published
    stmt = select(Article).where(
        Article.created_at >= window,
        Article.state.in_(DEDUP_CHECK_STATES),  # Use in-progress states
    )
    result = await session.execute(stmt)
    recent = result.scalars().all()

    current_keywords = extract_keywords(title)

    for article in recent:
        if not article.original_title:
            continue
        if exclude_id and article.id == exclude_id:
            continue

        sim = keyword_similarity(title, article.original_title)
        if sim >= SEMANTIC_THRESHOLD:
            logger.info(f"SEMANTIC DUPLICATE at creation: '{title[:50]}' vs '{article.original_title[:50]}' (sim={sim:.0%})")
            return (True, article.original_title, article.wp_url or article.original_url)

    return (False, None, None)


def count_words(text: Optional[str]) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


async def create_raw_signal(session: AsyncSession, source: Source, signal: RSSRawSignal) -> RawSignal:
    """
    Create a RawSignal record from RSS data.
    ALWAYS saves to raw_signals - no skipping, no dedup here.
    """
    url_hash = hash_url(signal.url)
    title_hash = hash_title(signal.title)
    content_hash = hash_content(signal.summary or signal.content)

    raw_signal = RawSignal(
        source_id=source.id,
        source_name=source.name,
        feed_url=source.feed_url,
        original_url=signal.url,
        original_title=signal.title,
        original_summary=signal.summary,
        original_content=signal.content,
        original_image_url=signal.image_url,
        original_author=signal.author,
        original_language=source.language,
        original_tags=[],
        published_at=signal.published_at,
        url_hash=url_hash,
        title_hash=title_hash,
        content_hash=content_hash,
        word_count=count_words(signal.summary or signal.content),
        has_image=bool(signal.image_url),
        was_processed=False,
        processing_result=None,
    )
    session.add(raw_signal)
    await session.flush()
    return raw_signal


async def fetch_source(
    session: AsyncSession,
    source: Source,
    save_articles: bool = True,
) -> list[Article]:
    """
    Fetch RSS feed for a single source.

    Flow:
    1. Parse RSS feed
    2. ALWAYS save to raw_signals (no skipping)
    3. Check dedup (URL match in articles table)
    4. If not duplicate: create article and link to raw_signal
    5. Update raw_signal with processing result

    Returns list of created Article objects.
    """
    from app.signals.web_scraper import fetch_with_headers, extract_main_content

    articles_created = []
    source_id = source.id  # Store ID to avoid session state issues

    try:
        # Parse RSS feed
        signals = parse_feed(source.feed_url)

        if not signals:
            logger.info(f"No signals parsed from {source.name} ({source.feed_url}) — feed may be empty")
            await session.execute(
                update(Source)
                .where(Source.id == source_id)
                .values(
                    last_fetched_at=datetime.utcnow(),
                    last_error=None,
                )
            )
            await session.commit()
            return []

        logger.info(f"Parsed {len(signals)} signals from {source.name}")

        # Process signals one by one with fresh session for each
        for signal in signals:
            async with async_session_maker() as new_session:
                now = datetime.utcnow()
                raw_signal = None
                article = None

                try:
                    # STEP 1: ALWAYS save to raw_signals FIRST
                    raw_signal = RawSignal(
                        source_id=source_id,
                        source_name=source.name,
                        feed_url=source.feed_url,
                        original_url=signal.url,
                        original_title=signal.title,
                        original_summary=signal.summary,
                        original_content=signal.content,
                        original_image_url=signal.image_url,
                        original_author=signal.author,
                        original_language=source.language,
                        original_tags=[],
                        published_at=signal.published_at,
                        url_hash=hash_url(signal.url),
                        title_hash=hash_title(signal.title),
                        content_hash=hash_content(signal.summary or signal.content),
                        word_count=count_words(signal.summary or signal.content),
                        has_image=bool(signal.image_url),
                        was_processed=False,
                    )
                    new_session.add(raw_signal)
                    await new_session.flush()

                    # STEP 2: Check dedup - BOTH URL AND title_hash
                    # FIX: Use normalized URL and check ALL in-progress states
                    title_hash = hash_title(signal.title)
                    normalized_url = normalize_url_for_dedup(signal.url)

                    # Check against ALL in-progress states to prevent race condition
                    stmt = select(Article).where(
                        (Article.original_url == normalized_url) |
                        ((Article.title_hash == title_hash) & (Article.state.in_(DEDUP_CHECK_STATES)))
                    )
                    result = await new_session.execute(stmt)
                    existing_article = result.scalar_one_or_none()

                    if existing_article:
                        # Duplicate found - update raw_signal and skip
                        duplicate_reason = "url_match" if existing_article.original_url == signal.url else "title_match"
                        raw_signal.was_processed = True
                        raw_signal.processing_result = f"duplicate_{duplicate_reason}"
                        raw_signal.article_id = existing_article.id
                        raw_signal.processed_at = now
                        await new_session.commit()
                        logger.info(f"Raw signal marked as duplicate ({duplicate_reason}): {signal.title[:60]}")
                        continue

                    # STEP 2.5: Check semantic duplicate BEFORE creating article
                    # This prevents creating articles about same topic from different sources
                    is_semantic_dup, similar_title, similar_url = await check_semantic_duplicate(
                        new_session, signal.title
                    )
                    if is_semantic_dup:
                        raw_signal.was_processed = True
                        raw_signal.processing_result = "duplicate_semantic"
                        raw_signal.processed_at = now
                        await new_session.commit()
                        logger.info(f"Raw signal marked as semantic duplicate: '{signal.title[:60]}' vs '{similar_title[:60]}'")
                        continue

                    # STEP 3: Create article (not a duplicate)
                    # NOTE: unique constraint on title_hash will prevent duplicates
                    # but we handle the exception gracefully
                    article = Article(
                        source_id=source_id,
                        original_url=signal.url,
                        original_title=signal.title,
                        title_hash=hash_title(signal.title),
                        original_summary=signal.summary,
                        original_image_url=signal.image_url,
                        signal_published_at=signal.published_at,
                        state=ArticleState.SIGNAL_COLLECTED.value,
                        created_at=now,
                        updated_at=now,
                    )
                    new_session.add(article)

                    try:
                        await new_session.flush()
                    except Exception as flush_error:
                        # Handle unique constraint violation (PostgreSQL error code 23505)
                        error_str = str(flush_error)
                        if "23505" in error_str or "uq_articles_title_hash_active" in error_str:
                            # Another article with same title_hash was created concurrently
                            raw_signal.was_processed = True
                            raw_signal.processing_result = "duplicate_constraint"
                            raw_signal.processed_at = now
                            await new_session.rollback()
                            logger.info(f"Raw signal skipped due to unique constraint: '{signal.title[:60]}'")
                            continue
                        else:
                            # Re-raise other errors
                            raise flush_error

                    # STEP 4: Link raw_signal to article and mark as processed
                    raw_signal.was_processed = True
                    raw_signal.article_id = article.id
                    raw_signal.processing_result = "created"
                    raw_signal.processed_at = now

                    await new_session.commit()
                    articles_created.append(article)
                    logger.debug(f"Created article from raw signal: {signal.title[:50]}")

                except Exception as e:
                    logger.warning(f"Failed to process signal: {e}")
                    # Update raw_signal with error if it was created
                    if raw_signal and raw_signal.id:
                        try:
                            raw_signal.was_processed = True
                            raw_signal.processing_result = "error"
                            raw_signal.processing_note = str(e)[:500]
                            raw_signal.processed_at = datetime.utcnow()
                            await new_session.commit()
                        except Exception:
                            pass
                    try:
                        await new_session.rollback()
                    except Exception:
                        pass

        # Update source status
        if articles_created or signals:
            logger.info(f"Created {len(articles_created)} articles from {source.name} ({len(signals)} signals)")
            try:
                await session.execute(
                    update(Source)
                    .where(Source.id == source_id)
                    .values(
                        last_fetched_at=datetime.utcnow(),
                        last_error=None,
                    )
                )
                await session.commit()
            except Exception as e:
                logger.warning(f"Failed to update source: {e}")

    except Exception as e:
        logger.error(f"Failed to fetch source {source.name}: {e}")

    return articles_created


async def fetch_all_sources(
    session: AsyncSession,
    source_ids: Optional[list[str]] = None,
) -> dict:
    """
    Fetch all active sources or specific sources by ID.

    Returns summary of results.
    """
    total_signals = 0
    total_created = 0
    sources_fetched = 0
    errors = []

    if source_ids:
        stmt = select(Source).where(Source.id.in_(source_ids))
    else:
        stmt = select(Source).where(Source.is_active == True)  # noqa: E712

    result = await session.execute(stmt)
    sources = result.scalars().all()

    for source in sources:
        try:
            articles = await fetch_source(session, source, save_articles=True)
            total_signals += len(articles) if articles else 0
            total_created += len(articles)
            sources_fetched += 1
        except Exception as e:
            await session.rollback()
            errors.append({"source": source.name, "error": str(e)})

    # Publish event for real-time dashboard update
    await publish_event(CHANNEL_ARTICLE_EVENTS, {
        "type": "signals_fetched",
        "data": {
            "sources_fetched": sources_fetched,
            "articles_created": total_created,
            "total_signals": total_signals,
        },
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "sources_fetched": sources_fetched,
        "articles_created": total_created,
        "total_signals": total_signals,
        "errors": errors,
    }
