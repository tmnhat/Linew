"""
Article writer - generates content using AI.
"""
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import ai_gateway
from app.core.ai_presets import WRITE_QUICK_PROMPT, WRITE_DEEP_PROMPT
from app.models.article import Article

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Count words in HTML text (strip tags first)."""
    plain = re.sub(r'<[^>]+>', ' ', text)
    words = plain.split()
    return len(words)


def slugify(text: str) -> str:
    """Convert title to URL-friendly slug."""
    # Lowercase, replace spaces with hyphens
    slug = text.lower()
    # Remove special chars except hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Limit length
    if len(slug) > 80:
        slug = slug[:80].rsplit('-', 1)[0]
    return slug


async def write_article(session: AsyncSession, article: Article) -> dict:
    """
    Write article content using AI (heavy model).

    Returns dict with:
    - body_html
    - meta_title
    - meta_description
    - slug
    - tags
    - image_keywords
    - word_count
    """
    try:
        # Get source name
        source_name = "Unknown"
        if article.source_id:
            from sqlalchemy import select
            from app.models.source import Source
            result = await session.execute(
                select(Source.name).where(Source.id == article.source_id)
            )
            source_name = result.scalar() or "Unknown"

        # Choose prompt based on article type
        if article.article_type == "deep" and article.crawled_content:
            prompt = WRITE_DEEP_PROMPT.format(
                original_title=article.original_title,
                crawled_content=article.crawled_content[:8000],  # Limit to 8000 chars
                source_name=source_name,
                category=article.category or "general",
            )
            max_tokens = 4096
        else:
            # Handle case where original_summary is a list (malformed data)
            summary_text = article.original_summary
            if isinstance(summary_text, list):
                # Extract text from list of dicts
                summary_text = " ".join(
                    str(item.get("value", "")) if isinstance(item, dict) else str(item)
                    for item in summary_text
                )
            elif not isinstance(summary_text, str):
                summary_text = str(summary_text) if summary_text else ""

            prompt = WRITE_QUICK_PROMPT.format(
                original_title=article.original_title,
                original_summary=summary_text,
                source_name=source_name,
                category=article.category or "general",
            )
            max_tokens = 2048

        # Call AI
        logger.info(f"Writing article {article.id} (type={article.article_type})")
        response = await ai_gateway.call_ai(
            prompt=prompt,
            task_type="write",
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.7,
        )
        
        # DEBUG: Log AI response to see tags
        logger.info(f"AI response keys: {list(response.keys())}")
        logger.info(f"AI response tags: {response.get('tags', 'NO_TAGS_KEY')}")

        # Extract response fields
        body_html = response.get("body_html", "")

        # Validate body_html - if empty or just whitespace, use fallback content
        if not body_html or not body_html.strip():
            logger.warning(f"AI returned empty body_html for article {article.id}, using fallback")
            # Use crawled_content or original_summary as fallback
            # Handle case where original_summary is a list (malformed data)
            fallback_summary = article.original_summary
            if isinstance(fallback_summary, list):
                fallback_summary = " ".join(
                    str(item.get("value", "")) if isinstance(item, dict) else str(item)
                    for item in fallback_summary
                )
            elif not isinstance(fallback_summary, str):
                fallback_summary = str(fallback_summary) if fallback_summary else ""

            fallback_content = article.crawled_content or fallback_summary or ""
            if fallback_content:
                # Convert plain text to basic HTML
                paragraphs = [p.strip() for p in fallback_content.split('\n\n') if p.strip()]
                body_html = '\n\n'.join([f'<p>{p}</p>' for p in paragraphs[:10]])  # Limit to 10 paragraphs
            if not body_html:
                # Last resort: use original_title as single paragraph
                body_html = f'<p>{article.original_title}</p>'

        word_count = count_words(body_html)

        # Ensure slug exists
        slug = response.get("slug") or slugify(article.original_title)

        # Ensure image_keywords is a list (must come before fallback that may use it)
        image_keywords = response.get("image_keywords", [])
        if isinstance(image_keywords, str):
            image_keywords = [k.strip() for k in image_keywords.split(",")]

        # Ensure tags is a list
        tags = response.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # Fallback: If tags is empty, generate from category and keywords
        if not tags:
            logger.warning(f"AI returned empty tags for article {article.id}, using fallback")
            tags = []
            # Add category as first tag
            if article.category:
                tags.append(article.category)
            # Add keywords from image_keywords if available
            if image_keywords:
                tags.extend(image_keywords[:5])
            # Add keywords from title
            title_words = [w for w in article.original_title.split() if len(w) > 3][:3]
            tags.extend(title_words)
            # Remove duplicates while preserving order
            seen = set()
            tags = [x for x in tags if not (x in seen or seen.add(x))]
            logger.info(f"Fallback tags generated: {tags}")

        # Build result
        result = {
            "body_html": body_html,
            "meta_title": response.get("meta_title") or article.original_title[:60],
            "meta_description": response.get("meta_description") or "",
            "slug": slug,
            "tags": tags,
            "image_keywords": image_keywords,
            "word_count": word_count,
        }

        logger.info(
            f"Article {article.id} written: {word_count} words, "
            f"tags={tags[:3]}, slug={slug}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to write article {article.id}: {e}")
        raise


async def generate_image_keywords(article: Article) -> list[str]:
    """
    Generate image search keywords for the article.
    Called after writing to get additional image suggestions.
    """
    try:
        prompt = f"""Based on this article title, suggest 3-5 keywords for finding relevant images.
Title: {article.original_title}
Category: {article.category or 'general'}

Return JSON: {{"keywords": ["keyword1", "keyword2", "keyword3"]}}"""

        response = await ai_gateway.call_ai(
            prompt=prompt,
            task_type="categorize",
            response_format={"type": "json_object"},
            max_tokens=128,
            temperature=0.5,
        )

        keywords = response.get("keywords", [])
        if isinstance(keywords, list):
            return keywords[:5]

    except Exception as e:
        logger.warning(f"Failed to generate image keywords: {e}")

    # Fallback
    return [
        article.category or "news",
        article.original_title[:30],
    ]
