"""
Internal Linking Engine - Smart internal linking for SEO.
Handles:
- New article linking to old articles
- Old articles linking to new articles
- Related posts updates
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class LinkResult:
    """Result of an internal linking operation"""
    article_id: str
    links_added: int
    success: bool
    error: Optional[str] = None


class InternalLinkingEngine:
    """
    Smart internal linking engine for WordPress.
    
    Features:
    - Keyword-based linking
    - Related posts by category/tags
    - Batch processing
    - WordPress REST API integration
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.wp_url = self.settings.wp_url.rstrip("/")
        self.wp_username = self.settings.wp_username
        self.wp_app_password = self.settings.wp_app_password
        self.max_links_per_article = self.settings.internal_links_per_article
        self.max_articles_to_update = self.settings.max_articles_to_update
    
    def _get_auth_headers(self) -> dict:
        """Get Basic Auth headers for WordPress API"""
        import base64
        credentials = f"{self.wp_username}:{self.wp_app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": "Linew/1.0 SEO"
        }
    
    async def get_article_content(self, post_id: int) -> Optional[dict]:
        """Get article content from WordPress"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.wp_url}/wp-json/wp/v2/posts/{post_id}",
                    headers=self._get_auth_headers(),
                    params={"_embed": "true"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get article {post_id}: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error getting article {post_id}: {e}")
            return None
    
    async def get_related_articles(
        self, 
        category: str, 
        exclude_id: int,
        limit: int = 5
    ) -> List[dict]:
        """Get related articles by category"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get posts in same category
                response = await client.get(
                    f"{self.wp_url}/wp-json/wp/v2/posts",
                    headers=self._get_auth_headers(),
                    params={
                        "categories": category,
                        "exclude": exclude_id,
                        "per_page": limit,
                        "status": "publish",
                        "orderby": "date",
                        "order": "desc"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting related articles: {e}")
            return []
    
    def generate_see_also_block(self, articles: List[dict]) -> str:
        """
        Generate 'See Also' HTML block for linking to related articles.
        
        Args:
            articles: List of article dicts with title, link, slug
            
        Returns:
            HTML block to append to content
        """
        if not articles:
            return ""
        
        links_html = ""
        for article in articles[:self.max_links_per_article]:
            title = article.get("title", {}).get("rendered", "Related Article")
            # Decode HTML entities
            title = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), title)
            title = re.sub(r'&amp;', '&', title)
            title = re.sub(r'&quot;', '"', title)
            
            link = article.get("link", "")
            if link:
                links_html += f'<li><a href="{link}">{title}</a></li>'
        
        if not links_html:
            return ""
        
        return f'''
<!-- See Also Section -->
<div class="see-also-section">
    <h3>See Also</h3>
    <ul class="see-also-links">
        {links_html}
    </ul>
</div>
'''
    
    async def update_article_content(self, post_id: int, new_content: str) -> bool:
        """Update article content in WordPress"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.wp_url}/wp-json/wp/v2/posts/{post_id}",
                    headers=self._get_auth_headers(),
                    json={"content": new_content}
                )
                
                if response.status_code in (200, 201):
                    logger.info(f"Updated content for post {post_id}")
                    return True
                else:
                    logger.warning(f"Failed to update post {post_id}: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error updating post {post_id}: {e}")
            return False
    
    async def link_new_article(self, article_id: str, article_data: dict) -> LinkResult:
        """
        Link a new article to related old articles.
        
        Args:
            article_id: The article ID
            article_data: Dict with 'wp_post_id', 'title', 'category', 'content', 'link'
            
        Returns:
            LinkResult with operation status
        """
        try:
            wp_post_id = article_data.get("wp_post_id")
            category = article_data.get("category", "")
            article_link = article_data.get("link", "")
            article_title = article_data.get("title", "This Article")
            
            if not wp_post_id:
                return LinkResult(
                    article_id=article_id,
                    links_added=0,
                    success=False,
                    error="No WordPress post ID"
                )
            
            links_added = 0
            
            # Get related old articles
            related = await self.get_related_articles(category, wp_post_id, limit=self.max_links_per_article)
            
            if related:
                # Generate links TO old articles FROM this new article
                see_also_block = self.generate_see_also_block(related)
                
                if see_also_block:
                    # Get current content
                    article = await self.get_article_content(wp_post_id)
                    if article:
                        current_content = article.get("content", {}).get("rendered", "")
                        
                        # Append see also block before closing tag
                        new_content = current_content + see_also_block
                        
                        if await self.update_article_content(wp_post_id, new_content):
                            links_added += len(related)
                            logger.info(f"Added {len(related)} links in article {article_id}")
            
            # Also update old articles to link TO this new article
            await self.update_old_articles_with_new_link(
                category=category,
                exclude_id=wp_post_id,
                new_article_title=article_title,
                new_article_link=article_link
            )
            
            return LinkResult(
                article_id=article_id,
                links_added=links_added,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error linking article {article_id}: {e}")
            return LinkResult(
                article_id=article_id,
                links_added=0,
                success=False,
                error=str(e)
            )
    
    async def update_old_articles_with_new_link(
        self,
        category: str,
        exclude_id: int,
        new_article_title: str,
        new_article_link: str
    ) -> int:
        """
        Update old articles in same category to link to a new article.
        
        Args:
            category: Category name
            exclude_id: New article ID to exclude
            new_article_title: Title of new article for anchor text
            new_article_link: URL of new article
            
        Returns:
            Number of articles updated
        """
        if not new_article_link:
            return 0
        
        try:
            # Get recent articles (last 7 days) in same category
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search for posts
                response = await client.get(
                    f"{self.wp_url}/wp-json/wp/v2/posts",
                    headers=self._get_auth_headers(),
                    params={
                        "categories": category,
                        "exclude": exclude_id,
                        "per_page": self.max_articles_to_update,
                        "status": "publish",
                        "orderby": "date",
                        "order": "desc",
                        "after": (datetime.utcnow() - timedelta(days=7)).isoformat()
                    }
                )
                
                if response.status_code != 200:
                    return 0
                
                articles = response.json()
                updated = 0
                
                for article in articles:
                    post_id = article.get("id")
                    content = article.get("content", {}).get("rendered", "")
                    
                    # Check if already linked to new article
                    if new_article_link in content:
                        continue
                    
                    # Generate smart anchor text
                    anchor_text = self._generate_anchor_text(new_article_title)
                    
                    # Create link HTML
                    new_link = f'<li><a href="{new_article_link}">{anchor_text}</a></li>'
                    
                    # Check if see-also section exists
                    if 'class="see-also-links"' in content:
                        # Append to existing see-also section
                        new_content = re.sub(
                            r'(</ul>\s*</div>\s*<!--\s*End See Also)',
                            f'{new_link}\\1',
                            content
                        )
                    else:
                        # Add new see-also section
                        new_content = content + f'''
<!-- See Also Section -->
<div class="see-also-section">
    <h3>See Also</h3>
    <ul class="see-also-links">
        {new_link}
    </ul>
</div>
'''
                    
                    if new_content != content:
                        if await self.update_article_content(post_id, new_content):
                            updated += 1
                            logger.info(f"Updated post {post_id} with link to new article")
                
                return updated
                
        except Exception as e:
            logger.error(f"Error updating old articles: {e}")
            return 0
    
    def _generate_anchor_text(self, title: str) -> str:
        """Generate smart anchor text from title"""
        # Clean HTML entities
        title = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), title)
        title = re.sub(r'&amp;', '&', title)
        
        # Take first few words for anchor text
        words = title.split()
        if len(words) <= 5:
            return title
        
        # Use first 5-7 words
        anchor = ' '.join(words[:6])
        if not anchor.endswith(('.', '!', '?')):
            anchor += '...'
        
        return anchor
    
    async def refresh_related_posts(self, limit: int = 50) -> Dict[str, Any]:
        """
        Refresh related posts for trending/recent articles.
        
        Args:
            limit: Maximum number of articles to refresh
            
        Returns:
            Dict with statistics
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Get recent published articles
                response = await client.get(
                    f"{self.wp_url}/wp-json/wp/v2/posts",
                    headers=self._get_auth_headers(),
                    params={
                        "per_page": limit,
                        "status": "publish",
                        "orderby": "date",
                        "order": "desc"
                    }
                )
                
                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}"}
                
                articles = response.json()
                stats = {
                    "total": len(articles),
                    "updated": 0,
                    "failed": 0
                }
                
                for article in articles:
                    try:
                        post_id = article.get("id")
                        categories = article.get("categories", [])
                        
                        if not categories:
                            continue
                        
                        # Get current related posts
                        related = await self.get_related_articles(
                            categories[0], 
                            post_id, 
                            limit=self.max_links_per_article
                        )
                        
                        if related:
                            # Update see-also section
                            content = article.get("content", {}).get("rendered", "")
                            see_also_block = self.generate_see_also_block(related)
                            
                            # Remove old see-also section
                            content = re.sub(
                                r'<!--\s*See Also Section.*?<!--\s*End See Also\s*-->',
                                '',
                                content,
                                flags=re.DOTALL
                            )
                            
                            # Add new section
                            new_content = content + see_also_block
                            
                            if await self.update_article_content(post_id, new_content):
                                stats["updated"] += 1
                            else:
                                stats["failed"] += 1
                        else:
                            stats["failed"] += 1
                            
                    except Exception as e:
                        logger.warning(f"Error refreshing post {article.get('id')}: {e}")
                        stats["failed"] += 1
                
                return stats
                
        except Exception as e:
            logger.error(f"Error refreshing related posts: {e}")
            return {"error": str(e)}
    
    async def get_linking_stats(self) -> Dict[str, Any]:
        """Get internal linking statistics"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Count posts with see-also sections
                response = await client.get(
                    f"{self.wp_url}/wp-json/wp/v2/posts",
                    headers=self._get_auth_headers(),
                    params={
                        "per_page": 100,
                        "status": "publish"
                    }
                )
                
                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}"}
                
                articles = response.json()
                with_links = 0
                total_articles = len(articles)
                
                for article in articles:
                    content = article.get("content", {}).get("rendered", "")
                    if 'class="see-also-section"' in content:
                        with_links += 1
                
                return {
                    "total_articles": total_articles,
                    "articles_with_internal_links": with_links,
                    "coverage_percent": round(with_links / total_articles * 100, 1) if total_articles > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting linking stats: {e}")
            return {"error": str(e)}


# Singleton instance
_linking_engine: Optional[InternalLinkingEngine] = None


def get_linking_engine() -> InternalLinkingEngine:
    """Get or create Internal Linking Engine instance"""
    global _linking_engine
    if _linking_engine is None:
        _linking_engine = InternalLinkingEngine()
    return _linking_engine


def link_new_article_async(article_id: str):
    """
    Async wrapper to link new article.
    Can be called from Celery task.
    """
    import asyncio
    
    async def _link():
        try:
            engine = get_linking_engine()
            
            # Get article data from database
            from app.core.database import get_db_context
            from sqlalchemy import select
            from app.models.article import Article
            
            async with get_db_context() as session:
                result = await session.execute(
                    select(Article).where(Article.id == article_id)
                )
                article = result.scalar_one_or_none()
                
                if not article:
                    logger.warning(f"Article {article_id} not found for linking")
                    return
                
                article_data = {
                    "wp_post_id": article.wp_post_id,
                    "title": article.meta_title or article.original_title,
                    "category": article.category,
                    "link": article.wp_url
                }
                
                result = await engine.link_new_article(article_id, article_data)
                logger.info(f"Internal linking complete for {article_id}: {result}")
                
        except Exception as e:
            logger.error(f"Error in async link for {article_id}: {e}")
    
    # Run in background
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_link())
        else:
            loop.run_until_complete(_link())
    except Exception as e:
        logger.error(f"Failed to start async linking: {e}")
