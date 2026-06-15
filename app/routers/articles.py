"""
Articles API routes.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.article import Article, ArticleState
from app.models.publish_log import PublishLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/articles", tags=["articles"])


class ArticleListResponse(BaseModel):
    items: list
    total: int
    page: int
    pages: int


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    state: Optional[str] = None,
    category: Optional[str] = None,
    mode: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = "-created_at",
    db: AsyncSession = Depends(get_db),
):
    """List articles with filtering and pagination."""
    # Build query
    stmt = select(Article)

    # Filters
    if state:
        states = state.split(",")
        stmt = stmt.where(Article.state.in_(states))

    if category:
        categories = category.split(",")
        stmt = stmt.where(Article.category.in_(categories))

    if mode:
        stmt = stmt.where(Article.mode == mode)

    # Count total
    count_stmt = select(func.count(Article.id))
    if state:
        count_stmt = count_stmt.where(Article.state.in_(state.split(",")))
    result = await db.execute(count_stmt)
    total = result.scalar()

    # Sort
    if sort.startswith("-"):
        field_name = sort[1:]
        order = False
    else:
        field_name = sort
        order = True

    if hasattr(Article, field_name):
        order_col = getattr(Article, field_name)
        if not order:
            order_col = order_col.desc()
        stmt = stmt.order_by(order_col)
    else:
        stmt = stmt.order_by(Article.created_at.desc())

    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    articles = result.scalars().all()

    pages = (total + limit - 1) // limit

    return ArticleListResponse(
        items=[a.to_dict() for a in articles],
        total=total,
        page=page,
        pages=pages,
    )


@router.get("/{article_id}")
async def get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single article with publish logs."""
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Get publish logs
    result = await db.execute(
        select(PublishLog)
        .where(PublishLog.article_id == article_id)
        .order_by(PublishLog.created_at.desc())
    )
    logs = result.scalars().all()

    article_dict = article.to_dict()
    article_dict["publish_logs"] = [log.to_dict() for log in logs]

    return article_dict


class ApproveRequest(BaseModel):
    pass


class RejectRequest(BaseModel):
    reason: str


@router.post("/{article_id}/approve")
async def approve_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve an article for publishing.
    ALWAYS runs governance first before approving.
    """
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.state == ArticleState.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Article already published")

    # Run governance first
    from app.pipeline.governor import govern_article
    gov_result = await govern_article(db, article)

    if not gov_result.get("passed"):
        article.state = ArticleState.REJECTED.value
        article.governance_result = "fail"
        article.governance_reason = gov_result.get("reason")
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Article failed governance: {gov_result.get('reason')}"
        )

    # Governance passed - approve
    article.state = ArticleState.APPROVED.value
    article.governance_result = "pass"
    article.last_step_at = datetime.utcnow()
    await db.commit()

    return {"id": str(article.id), "state": article.state, "governance": "passed"}


@router.post("/{article_id}/reject")
async def reject_article(
    article_id: UUID,
    data: RejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject an article."""
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.state = ArticleState.REJECTED.value
    article.governance_reason = data.reason
    article.last_step_at = datetime.utcnow()
    await db.commit()

    return {"id": str(article.id), "state": article.state}


@router.post("/{article_id}/unpublish")
async def unpublish_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Unpublish an article."""
    from app.publisher.wordpress import get_wordpress_client

    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not article.wp_post_id:
        raise HTTPException(status_code=400, detail="Article has no WordPress post")

    client = get_wordpress_client()
    client.unpublish_post(article.wp_post_id)

    # Log action
    log = PublishLog(
        article_id=article.id,
        action="unpublish",
        wp_post_id=article.wp_post_id,
    )
    db.add(log)

    article.state = ArticleState.APPROVED.value
    article.wp_url = None
    article.published_at = None
    await db.commit()

    return {"id": str(article.id), "state": article.state}


@router.post("/{article_id}/republish")
async def republish_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Republish an article."""
    from app.pipeline.tasks import task_publish

    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    try:
        result = await task_publish(str(article_id))
        return {"id": str(article.id), **result}
    except Exception as e:
        logger.error(f"Republish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
