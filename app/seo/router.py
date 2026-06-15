"""
SEO router - registers sitemap, robots.txt, ping, and internal linking endpoints.
"""
import logging
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.seo.sitemap import router as sitemap_router
from app.seo.robots import router as robots_router
from app.seo.ping_service import (
    PingService,
    PingResult,
    get_ping_service,
    ping_on_publish,
    ping_on_update,
    ping_on_delete
)
from app.seo.internal_linking import (
    InternalLinkingEngine,
    get_linking_engine
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Redirect /sitemap to /sitemap.xml
@router.get("/sitemap")
async def sitemap_redirect():
    """Redirect /sitemap to /sitemap.xml"""
    return RedirectResponse(url="/sitemap.xml", status_code=301)


# ============ Pydantic Models ============

class PingRequest(BaseModel):
    url: str
    action: str = "publish"  # publish, update, delete
    notify_google: bool = True
    notify_bing: bool = True

class BatchPingRequest(BaseModel):
    urls: List[str]
    action: str = "publish"

class PingResponse(BaseModel):
    url: str
    status: str
    google_success: bool = False
    bing_success: bool = False
    error: Optional[str] = None

class TestResponse(BaseModel):
    google: dict
    bing: dict
    overall: str


# ============ Ping Endpoints ============

@router.post("/api/seo/ping", response_model=PingResponse)
async def ping_url(request: PingRequest):
    """
    Ping search engines (Google & Bing) about a URL change.

    - **url**: The URL to submit
    - **action**: 'publish' for new content, 'update' for changes, 'delete' to remove
    - **notify_google**: Whether to notify Google
    - **notify_bing**: Whether to notify Bing
    """
    try:
        result = await ping_on_publish(request.url)
        return PingResponse(
            url=result.url,
            status=result.status.value,
            google_success=result.google_result.success if result.google_result else False,
            bing_success=result.bing_result.success if result.bing_result else False,
            error=result.error_message
        )
    except Exception as e:
        logger.error(f"Ping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/seo/ping-batch")
async def ping_batch(request: BatchPingRequest, background_tasks: BackgroundTasks):
    """
    Submit multiple URLs to search engines.

    - **urls**: List of URLs to submit
    - **action**: 'publish', 'update', or 'delete'
    """
    service = await get_ping_service()

    async def run_batch():
        for url in request.urls:
            try:
                await service.ping_url(url, request.action)
            except Exception as e:
                logger.error(f"Batch ping error for {url}: {e}")

    background_tasks.add_task(run_batch)

    return {
        "status": "queued",
        "count": len(request.urls),
        "message": f"Queued {len(request.urls)} URLs for indexing"
    }


@router.post("/api/seo/index-url", response_model=PingResponse)
async def index_url(url: str, action: str = "publish"):
    """
    Submit a URL to Google Indexing API.

    - **url**: The URL to index
    - **action**: 'publish' or 'delete'
    """
    return await ping_url(PingRequest(url=url, action=action))


@router.post("/api/seo/delete-url", response_model=PingResponse)
async def delete_url(url: str):
    """
    Remove a URL from Google and Bing indexes.
    """
    result = await ping_on_delete(url)
    return PingResponse(
        url=result.url,
        status=result.status.value,
        google_success=result.google_result.success if result.google_result else False,
        bing_success=result.bing_result.success if result.bing_result else False,
        error=result.error_message
    )


@router.get("/api/seo/test-connections", response_model=TestResponse)
async def test_connections():
    """
    Test connections to Google Indexing API and Bing Webmaster API.
    """
    service = await get_ping_service()
    return await service.test_connections()


# ============ Internal Linking Endpoints ============

class LinkArticleRequest(BaseModel):
    article_id: str


@router.post("/api/seo/link-article/{article_id}")
async def link_article(article_id: str, db: AsyncSession = Depends(get_db)):
    """
    Link a single article to related articles.
    
    - Finds articles in same category
    - Adds 'See Also' section with links
    - Updates related articles to link back to this article
    """
    try:
        from app.models.article import Article
        
        result = await db.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        engine = get_linking_engine()
        article_data = {
            "wp_post_id": article.wp_post_id,
            "title": article.meta_title or article.original_title,
            "category": article.category,
            "link": article.wp_url
        }
        
        link_result = await engine.link_new_article(article_id, article_data)
        
        return {
            "article_id": article_id,
            "links_added": link_result.links_added,
            "success": link_result.success,
            "error": link_result.error
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link article error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/seo/link-refresh")
async def refresh_internal_links():
    """
    Refresh internal links for all recent articles.
    
    Updates 'See Also' sections across the site.
    This is a scheduled task, can take a while.
    """
    try:
        engine = get_linking_engine()
        stats = await engine.refresh_related_posts()
        return {
            "status": "completed",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Refresh links error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/seo/link-stats")
async def get_linking_stats():
    """
    Get internal linking statistics.
    
    Returns:
    - Total articles
    - Articles with internal links
    - Coverage percentage
    """
    try:
        engine = get_linking_engine()
        stats = await engine.get_linking_stats()
        return stats
    except Exception as e:
        logger.error(f"Link stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/seo/health")
async def seo_health():
    """
    Overall SEO system health check.
    
    Returns status of:
    - Ping service connections
    - Internal linking engine
    """
    try:
        ping_service = await get_ping_service()
        linking_engine = get_linking_engine()
        
        ping_status = await ping_service.test_connections()
        link_stats = await linking_engine.get_linking_stats()
        
        return {
            "ping_service": ping_status,
            "internal_linking": link_stats,
            "overall": "ok" if ping_status.get("overall") != "error" else "degraded"
        }
    except Exception as e:
        logger.error(f"SEO health check error: {e}")
        return {
            "overall": "error",
            "error": str(e)
        }


# Include sitemap endpoints
router.include_router(sitemap_router)

# Include robots endpoint
router.include_router(robots_router)
