"""
Governance - copyright check, duplicate detection, and content moderation.
"""
import logging
import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import ai_gateway
from app.core.ai_presets import GOVERNANCE_PROMPT
from app.models.article import Article, ArticleState
from app.models.article_states import IN_PROGRESS_STATES, DEDUP_CHECK_STATES

logger = logging.getLogger(__name__)

# Minimum word count for publishing
MIN_WORD_COUNT = 100

# Copyright similarity threshold (0.0 - 1.0)
# FIX: Set to 0.30 to reject articles that are >30% similar to source content
COPYRIGHT_SIMILARITY_THRESHOLD = 0.30


def check_copyright(content1: str, content2: str) -> float:
    """
    Check copyright similarity between two texts.
    Returns similarity ratio (0-1).
    """
    if not content1 or not content2:
        return 0.0

    # Strip HTML from content1
    plain1 = re.sub(r'<[^>]+>', ' ', content1)
    plain2 = content2

    # Truncate to reasonable length for comparison
    plain1 = plain1[:5000]
    plain2 = plain2[:5000]

    ratio = SequenceMatcher(None, plain1, plain2).ratio()
    return round(ratio, 3)


async def moderate_content(session: AsyncSession, article: Article) -> dict:
    """
    Check article content for policy violations.
    Uses AI governance prompt.
    """
    try:
        prompt = GOVERNANCE_PROMPT.format(
            body_html=article.body_html or "",
        )

        response = await ai_gateway.call_ai(
            prompt=prompt,
            task_type="governance",
            response_format={"type": "json_object"},
            max_tokens=256,
            temperature=0.3,
        )

        result = response.get("result", "pass")
        reason = response.get("reason")

        logger.info(
            f"Governance check for article {article.id}: {result}"
            f"{f' - {reason}' if reason else ''}"
        )

        return {
            "result": result,
            "reason": reason,
        }

    except Exception as e:
        logger.error(f"Governance check failed for article {article.id}: {e}")
        # Fail-safe: mark as fail to be safe
        return {
            "result": "fail",
            "reason": f"Governance check error: {e}",
        }


async def check_duplicate_published_article(session: AsyncSession, article: Article) -> dict:
    """
    Check if this article is a duplicate of an already in-progress or published article.
    Uses title_hash to detect duplicates from different sources.

    FIX: Now checks against ALL active states AND terminal states (REJECTED, FAILED)
    to prevent race condition where multiple workers process articles with the same title_hash.

    Returns {is_duplicate, existing_article_id, existing_wp_url}.
    """
    if not article.title_hash:
        return {"is_duplicate": False}

    try:
        # FIX: Check against ALL states including REJECTED/FAILED to prevent reprocessing
        # This ensures we don't publish duplicates of articles that were rejected
        from app.models.article_states import DEDUP_CHECK_STATES
        
        stmt = select(Article).where(
            Article.title_hash == article.title_hash,
            Article.state.in_(DEDUP_CHECK_STATES),
            Article.id != article.id,  # Exclude self
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.warning(
                f"DUPLICATE DETECTED: Article '{article.original_title[:50]}' "
                f"(ID: {article.id}) matches {existing.state} article '{existing.original_title[:50]}' "
                f"(ID: {existing.id}, URL: {existing.wp_url or 'pending'})"
            )
            return {
                "is_duplicate": True,
                "existing_article_id": str(existing.id),
                "existing_wp_url": existing.wp_url,
            }

        return {"is_duplicate": False}

    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        return {"is_duplicate": False, "error": str(e)}


async def govern_article(session: AsyncSession, article: Article) -> dict:
    """
    Run full governance check on article.

    Steps:
    1. Word count check (reject if < 100 words)
    2. Duplicate check (reject if similar published article exists)
    3. Copyright check (rule-based)
    4. Content moderation (AI)

    Returns {passed, reason, copyright_score}.
    """
    copyright_score = 0.0
    passed = True
    reason = None

    # Step 0: Word count validation
    if article.body_html:
        plain_text = re.sub(r'<[^>]+>', ' ', article.body_html)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        word_count = len(plain_text.split())
    else:
        word_count = getattr(article, 'word_count', 0) or 0

    if word_count < MIN_WORD_COUNT:
        passed = False
        reason = f"Article too short ({word_count} words, minimum {MIN_WORD_COUNT} required)"
        logger.warning(f"Article {article.id} rejected: {reason}")
        return {
            "passed": False,
            "reason": reason,
            "copyright_score": 0.0,
        }

    # === FIX: Step 1 - Duplicate check with published articles ===
    duplicate_check = await check_duplicate_published_article(session, article)
    if duplicate_check.get("is_duplicate"):
        passed = False
        existing_url = duplicate_check.get("existing_wp_url", "unknown")
        reason = f"Duplicate article already published: {existing_url}"
        logger.warning(f"Article {article.id} rejected: duplicate of published article")
        return {
            "passed": False,
            "reason": reason,
            "copyright_score": 0.0,
            "duplicate": True,
            "existing_wp_url": existing_url,
        }

    # === FIX: Step 1.5 - Semantic duplicate check ===
    # Check if article is semantically similar to recently published articles
    # This catches duplicates with different titles but same topic
    try:
        from app.signals.semantic_dedup import check_semantic_duplicate
        logger.debug(f"[{article.id}] Starting semantic duplicate check...")
        semantic_result = await check_semantic_duplicate(session, article, window_hours=72)
        logger.debug(f"[{article.id}] Semantic check result: {semantic_result.get('is_duplicate')}")

        if semantic_result.get("is_duplicate"):
            passed = False
            similar_url = semantic_result.get("similar_wp_url", "unknown")
            similarity = semantic_result.get("similarity_score", 0)
            similar_title = semantic_result.get("similar_title", "")[:50]
            reason = f"Semantic duplicate (similarity={similarity:.0%}): {similar_title}"
            logger.warning(f"Article {article.id} rejected: semantic duplicate - {reason}")
            return {
                "passed": False,
                "reason": reason,
                "copyright_score": 0.0,
                "duplicate": True,
                "duplicate_type": "semantic",
                "existing_wp_url": similar_url,
            }
    except Exception as e:
        # Don't fail governance if semantic check fails - just log
        logger.warning(f"Semantic duplicate check failed for {article.id}: {e}")

    # Step 2: Copyright check
    if article.crawled_content and article.body_html:
        copyright_score = check_copyright(
            article.body_html,
            article.crawled_content,
        )
        logger.debug(f"Copyright score for {article.id}: {copyright_score}")

        if copyright_score > COPYRIGHT_SIMILARITY_THRESHOLD:
            passed = False
            reason = f"Copyright violation detected (similarity={copyright_score:.0%}, max {COPYRIGHT_SIMILARITY_THRESHOLD:.0%})"
            logger.warning(f"Article {article.id} failed copyright check: {reason}")
            return {
                "passed": False,
                "reason": reason,
                "copyright_score": copyright_score,
            }

    # Step 3: Content moderation
    moderation_result = await moderate_content(session, article)

    if moderation_result["result"] == "fail":
        passed = False
        reason = moderation_result["reason"] or "Content policy violation"
        logger.warning(f"Article {article.id} failed moderation: {reason}")
        return {
            "passed": False,
            "reason": reason,
            "copyright_score": copyright_score,
        }

    logger.info(f"Article {article.id} passed governance checks")
    return {
        "passed": True,
        "reason": None,
        "copyright_score": copyright_score,
    }
