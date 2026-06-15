"""
RSS Feed Crawler using feedparser.
"""
import logging
from datetime import datetime
from typing import Optional
import feedparser
import re

logger = logging.getLogger(__name__)


class RawSignal:
    """Represents a parsed RSS item."""
    def __init__(
        self,
        title: str,
        url: str,
        summary: Optional[str],
        image_url: Optional[str],
        published_at: Optional[datetime],
        author: Optional[str] = None,
        content: Optional[str] = None,
    ):
        self.title = title
        self.url = url
        self.summary = summary
        self.content = content  # Added for compatibility with signal processing
        self.image_url = image_url
        self.published_at = published_at
        self.author = author

    def __repr__(self):
        return f"RawSignal(title={self.title[:50]}..., url={self.url})"


def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters."""
    # Remove common tracking parameters
    tracking_params = [
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
        "fbclid", "gclid", "msclkid", "dclid", "twclid",
        "igshid", "mc_cid", "mc_eid",
        "ref", "ref_src", "ref_url",
    ]
    try:
        from urllib.parse import urlparse, parse_qs, urlencode
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        # Remove tracking params
        clean_qs = {k: v for k, v in qs.items() if k not in tracking_params}
        clean_query = urlencode(clean_qs, doseq=True)
        normalized = parsed._replace(query=clean_query).geturl()
        return normalized
    except Exception:
        return url


def extract_image_from_entry(entry: dict) -> Optional[str]:
    """Extract image URL from RSS entry."""
    # Try various common image fields
    for field in ["media_content", "media_thumbnail", "enclosure"]:
        if field in entry:
            data = entry[field]
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        url = item.get("url")
                        if url:
                            return url
            elif isinstance(data, dict):
                url = data.get("url")
                if url:
                    return url

    # Try image field in content
    content = entry.get("content", [])
    if isinstance(content, list) and content:
        html = content[0].get("value", "") if isinstance(content[0], dict) else str(content[0])
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
        if img_match:
            return img_match.group(1)

    # Try summary_html or summary
    for field in ["summary_detail", "summary"]:
        detail = entry.get(field, {})
        if isinstance(detail, dict):
            html = detail.get("value", "")
        else:
            html = str(detail) if detail else ""
        if html:
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
            if img_match:
                return img_match.group(1)

    return None


def parse_published_date(entry: dict) -> Optional[datetime]:
    """Parse published date from entry."""
    for field in ["published_parsed", "updated_parsed", "created_parsed"]:
        if field in entry and entry[field]:
            try:
                import time
                return datetime.fromtimestamp(time.mktime(entry[field]))
            except (ValueError, TypeError, OSError):
                continue

    # Try parsing string directly
    for date_str in [entry.get("published"), entry.get("updated"), entry.get("created")]:
        if date_str:
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(date_str)
            except Exception:
                continue

    return None


def parse_feed(feed_url: str) -> list[RawSignal]:
    """
    Parse RSS/Atom feed and return list of RawSignals.
    """
    try:
        logger.info(f"Parsing feed: {feed_url}")
        feed = feedparser.parse(feed_url)

        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed {feed_url} has parsing issues: {feed.bozo_exception}")

        signals = []
        for entry in feed.entries:
            try:
                # Extract title
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Extract URL
                link = entry.get("link", "")
                if not link:
                    # Try alternative link formats
                    links = entry.get("links", [])
                    for l in links:
                        if l.get("rel") == "alternate" or not l.get("rel"):
                            link = l.get("href", "")
                            break
                if not link:
                    continue

                # Normalize URL
                link = normalize_url(link)

                # Extract summary - keep HTML for image extraction later
                summary = None
                for summary_field in ["content", "summary", "description"]:
                    detail = entry.get(summary_field)
                    if detail:
                        if isinstance(detail, dict):
                            summary = detail.get("value", "")
                        else:
                            summary = str(detail)
                        # Clean up excessive whitespace but keep structure and images
                        summary = re.sub(r'\s+', ' ', summary).strip()
                        if summary:
                            break

                # Extract image
                image_url = extract_image_from_entry(entry)

                # Parse date
                published_at = parse_published_date(entry)

                # Extract author
                author = None
                if entry.get("author"):
                    author = entry.get("author")
                elif entry.get("author_detail", {}).get("name"):
                    author = entry.get("author_detail", {}).get("name")

                signal = RawSignal(
                    title=title,
                    url=link,
                    summary=summary[:2000] if summary else None,  # Limit length
                    image_url=image_url,
                    published_at=published_at,
                    author=author,
                )
                signals.append(signal)

            except Exception as e:
                logger.warning(f"Failed to parse entry in {feed_url}: {e}")
                continue

        logger.info(f"Parsed {len(signals)} signals from {feed_url}")
        return signals

    except Exception as e:
        logger.error(f"Failed to parse feed {feed_url}: {e}")
        return []
