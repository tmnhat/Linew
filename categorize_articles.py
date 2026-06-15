import asyncio
import sys
sys.path.insert(0, '/app')

from app.core.database import get_db_context
from sqlalchemy import select, update
from app.models.article import Article, ArticleState
from app.pipeline.analyzer import categorize_article

async def assign_categories():
    async with get_db_context() as session:
        # Get articles without category
        result = await session.execute(
            select(Article)
            .where(Article.category.is_(None))
            .where(Article.state == ArticleState.SIGNAL_COLLECTED.value)
            .limit(100)  # Process 100 at a time
        )
        articles = result.scalars().all()
        
        print(f"Found {len(articles)} articles without category")
        
        for article in articles:
            try:
                # Call AI to categorize
                result = await categorize_article(session, article)
                category = result["category"]
                confidence = result["confidence"]
                
                # Update article
                article.category = category
                article.category_confidence = confidence
                print(f"  {article.original_title[:50]}... -> {category} ({confidence:.2f})")
                
            except Exception as e:
                print(f"  Error categorizing {article.id}: {e}")
        
        await session.commit()
        print(f"Updated {len(articles)} articles")

if __name__ == "__main__":
    asyncio.run(assign_categories())
