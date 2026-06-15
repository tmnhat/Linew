import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.article import Article, ArticleState
from app.publisher.wordpress import publish_article_to_wordpress

async def test_publish():
    async with async_session_maker() as session:
        # Get an APPROVED article
        result = await session.execute(
            select(Article).where(Article.state == ArticleState.APPROVED.value).limit(1)
        )
        article = result.scalar_one_or_none()
        
        if not article:
            print("No approved articles found")
            return
        
        print(f"Testing publish for article: {article.original_title[:50]}")
        print(f"Article ID: {article.id}")
        print(f"Current state: {article.state}")
        print(f"Current wp_post_id: {article.wp_post_id}")
        
        # Publish
        pub_result = await publish_article_to_wordpress(session, article, source_name="Test")
        
        print(f"\nPublish result keys: {pub_result.keys()}")
        print(f"wp_post_id in result: {pub_result.get('wp_post_id')}")
        print(f"wp_url in result: {pub_result.get('wp_url')}")
        print(f"error in result: {pub_result.get('error')}")
        
        # Check if error
        if "error" in pub_result:
            print(f"Error: {pub_result.get('error')}")
            print(f"Response: {pub_result.get('response', 'N/A')[:500]}")
        
        # Check article state after publish
        await session.refresh(article)
        print(f"\nAfter publish:")
        print(f"Article state: {article.state}")
        print(f"Article wp_post_id: {article.wp_post_id}")
        print(f"Article wp_url: {article.wp_url}")

if __name__ == "__main__":
    asyncio.run(test_publish())
