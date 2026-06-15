"""
Publisher API routes.
"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_auth
from app.models.article import Article, ArticleState
from app.models.publish_log import PublishLog
from app.publisher.wordpress import get_wordpress_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/publisher", tags=["publisher"])


@router.post("/test-connection")
async def test_wordpress_connection():
    """Test WordPress connection."""
    client = get_wordpress_client()
    result = client.test_connection()
    return result


@router.post("/articles/{article_id}/publish")
async def publish_article(
    article_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """Manually publish an article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.state == ArticleState.PUBLISHED.value:
        return {
            "message": "Article already published",
            "wp_url": article.wp_url,
            "wp_post_id": article.wp_post_id,
        }

    # Run publish task in background
    background_tasks.add_task(run_publish_task, str(article_id))

    return {
        "message": "Publish task scheduled",
        "article_id": str(article_id),
    }


async def run_publish_task(article_id: str):
    """Background task to publish article."""
    from app.core.database import get_db_context
    from app.pipeline.tasks import task_publish

    try:
        await task_publish(article_id)
    except Exception as e:
        logger.error(f"Publish task failed for {article_id}: {e}")


@router.post("/articles/{article_id}/unpublish")
async def unpublish_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """Unpublish an article (set to draft)."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if not article.wp_post_id:
        raise HTTPException(status_code=400, detail="Article has no WordPress post ID")

    client = get_wordpress_client()
    unpub_result = client.unpublish_post(article.wp_post_id)

    # Log action
    log = PublishLog(
        article_id=article.id,
        action="unpublish",
        wp_post_id=article.wp_post_id,
        wp_response=unpub_result,
    )
    db.add(log)

    if "error" not in unpub_result:
        article.state = ArticleState.APPROVED.value
        article.wp_url = None
        article.published_at = None

    await db.commit()

    return {
        "message": "Article unpublished" if "error" not in unpub_result else "Unpublish failed",
        "wp_response": unpub_result,
    }


@router.post("/articles/{article_id}/republish")
async def republish_article(
    article_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_auth),
):
    """Republish an unpublished article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.wp_post_id:
        # Update existing post
        client = get_wordpress_client()
        pub_result = client.update_post(
            article.wp_post_id,
            {"status": "publish"},
        )

        if "error" not in pub_result:
            article.state = ArticleState.PUBLISHED.value
            article.published_at = datetime.utcnow()
            await db.commit()

        return {
            "message": "Article republished",
            "wp_url": article.wp_url,
        }
    else:
        # Need to create new post
        background_tasks.add_task(run_publish_task, str(article_id))
        return {"message": "Publish task scheduled", "article_id": str(article_id)}
