"""
Facebook message formatting and sanitization.

Handles:
- Message text formatting from articles
- HTML tag and link stripping
- Sanitization for clean posts
- Emoji mapping for categories
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text)


def strip_all_links(text: str) -> str:
    """
    Strip ALL URLs/links from text thoroughly.
    
    Removes:
    - HTML anchor tags and their content
    - href attributes
    - http/https URLs
    - www. URLs
    - example.com, linews.ai, linews.com, linews.vn and related domains
    - Any remaining URL-like patterns (.com, .org, .net, .io, .co domains)
    """
    if not text:
        return ""

    text = re.sub(r'<a[^>]*>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'href=["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'www\.\S+', '', text, flags=re.IGNORECASE)
    text = re.sub(
        r'(?:litimez\.com|litimez\.vn|linews?\.com|linews?\.vn)\S*',
        '',
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(r'\S+\.(?:com|org|net|io|co)\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def sanitize_message(message: str) -> str:
    """
    Final sanitization to ensure no links or suspicious content.
    This is the last line of defense before posting.
    """
    if not message:
        return ""

    url_patterns = [
        r'https?://\S+',
        r'www\.\S+',
        r'\S+\.(?:com|org|net|io|co|info|xyz|top|vn)\S*',
    ]
    
    for pattern in url_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            logger.warning(f"Found URL pattern '{pattern}' in message, removing...")
            message = re.sub(pattern, '', message, flags=re.IGNORECASE)

    message = re.sub(r'\[https?://[^\]]+\]', '', message)
    message = re.sub(r'\(https?://[^\)]+\)', '', message)

    domains_to_remove = ['litimez', 'linews', 'litime']
    for domain in domains_to_remove:
        message = re.sub(rf'(?<!@){domain}\S*', '', message, flags=re.IGNORECASE)

    lines = message.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        cleaned_lines.append(cleaned_line)
    message = '\n'.join(cleaned_lines)

    message = message.rstrip('.')

    return message


def get_category_emoji(category: str) -> str:
    """Get emoji for category."""
    emoji_map = {
        "tech": "💻",
        "technology": "💻",
        "ai": "🤖",
        "software": "💻",
        "hardware": "🔧",
        "internet": "🌐",
        "science": "🔬",
        "finance": "💰",
        "financial": "💰",
        "stock": "📈",
        "stocks": "📈",
        "crypto": "🪙",
        "cryptocurrency": "🪙",
        "banking": "🏦",
        "economy": "📊",
        "business": "💼",
        "marketing": "📢",
        "real_estate": "🏠",
        "startup": "🚀",
        "politics": "🏛️",
        "world": "🌍",
        "vietnam": "🇻🇳",
        "asia": "🌏",
        "usa": "🇺🇸",
        "europe": "🇪🇺",
        "sports": "⚽",
        "entertainment": "🎬",
        "health": "🏥",
        "education": "📚",
        "travel": "✈️",
        "food": "🍜",
        "lifestyle": "🌿",
        "gaming": "🎮",
        "security": "🔒",
        "default": "📰",
    }
    return emoji_map.get(category.lower(), emoji_map["default"])


def get_category_prefix(category: str) -> str:
    """Get category prefix for message."""
    prefix_map = {
        "tech": "CÔNG NGHỆ",
        "technology": "CÔNG NGHỆ",
        "ai": "TRÍ TUỆ NHÂN TẠO",
        "finance": "TÀI CHÍNH",
        "financial": "TÀI CHÍNH",
        "stock": "CHỨNG KHOÁN",
        "stocks": "CHỨNG KHOÁN",
        "crypto": "CRYPTO",
        "business": "KINH DOANH",
        "world": "THẾ GIỚI",
        "vietnam": "VIỆT NAM",
        "sports": "THỂ THAO",
        "entertainment": "GIẢI TRÍ",
        "health": "SỨC KHỎE",
        "education": "GIÁO DỤC",
    }
    return prefix_map.get(category.lower(), "")


def format_article_for_facebook(article) -> tuple[str, Optional[str]]:
    """
    Format an article for Facebook posting (no links).
    
    Returns:
        Tuple of (message, image_url)
    """
    emoji = get_category_emoji(getattr(article, 'category', 'default'))
    prefix = get_category_prefix(getattr(article, 'category', ''))
    
    title = strip_all_links(getattr(article, 'meta_title', '') or getattr(article, 'original_title', ''))
    
    message_parts = []
    
    if prefix:
        message_parts.append(f"📌 {prefix}")
        message_parts.append("")
    
    message_parts.append(f"{emoji} {title}")
    message_parts.append("")
    
    if hasattr(article, 'original_summary') and article.original_summary:
        message_parts.append("")
        message_parts.append(article.original_summary)
    
    message_parts.append("")
    message_parts.append("━━━━━━━━━━━━━━━━━━━━")
    message_parts.append("")
    message_parts.append("✨ Theo dõi @Linews để cập nhật tin mới nhất!")
    
    raw_message = "\n".join(message_parts)
    message = sanitize_message(raw_message)
    
    image_url = getattr(article, 'original_image_url', None)
    if not image_url:
        image_url = getattr(article, 'featured_image_url', None)
    if not image_url:
        images = getattr(article, 'crawled_images', None)
        if images and len(images) > 0:
            image_url = images[0].get('url') if isinstance(images[0], dict) else None
    
    return message, image_url
