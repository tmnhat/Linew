"""
Web scraper with 4-tier escalation.
"""
import asyncio
import logging
import random
import re
from typing import Optional

import httpx
import trafilatura

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


async def fetch_with_headers(url: str, timeout: int = 30) -> Optional[str]:
    """
    Tier 2: HTTP direct with rotating headers and retry logic.
    
    Enhanced with exponential backoff for better resilience.
    """
    max_retries = 3
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
                timeout=timeout,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                content = response.text
                if len(content) > 500:
                    logger.info(f"Fetched {len(content)} bytes from {url}")
                    return content
                
                # Content too short - might be blocked
                if attempt < max_retries - 1:
                    delay = random.uniform(base_delay, base_delay * 2) * (2 ** attempt)
                    logger.warning(
                        f"Content too short ({len(content)} bytes) for {url}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Timeout fetching {url}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
        except httpx.HTTPStatusError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"HTTP {e.response.status_code} for {url}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"HTTP error for {url}: {e.response.status_code}")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Error fetching {url}: {e}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed to fetch {url} after {max_retries} attempts: {e}")

    return None


async def fetch_via_flaresolverr(url: str, timeout: int = 60) -> Optional[str]:
    """
    Tier 3: FlareSolverr for Cloudflare-protected sites.
    
    Enhanced with retry logic and exponential backoff.
    """
    max_retries = 3
    base_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                payload = {
                    "cmd": "request.get",
                    "url": url,
                    "maxTimeout": timeout * 1000,
                    "userAgent": random.choice(USER_AGENTS),
                }

                response = await client.post(
                    f"{settings.flaresolverr_url}/v1",
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ok" and "solution" in data:
                        content = data["solution"].get("response", "")
                        if content and len(content) > 500:
                            logger.info(f"FlareSolverr fetched {len(content)} bytes from {url}")
                            return content
                        
                        # Empty response - might be bot detection
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(
                                f"FlareSolverr returned empty content for {url}, "
                                f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                
                # Non-OK status or empty data
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"FlareSolverr returned status={data.get('status')} for {url}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"FlareSolverr timeout for {url}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
        except httpx.HTTPStatusError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"FlareSolverr HTTP {e.response.status_code} for {url}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"FlareSolverr error for {url}: {e}, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"FlareSolverr failed after {max_retries} attempts for {url}: {e}")

    # All retries exhausted
    logger.warning(f"FlareSolverr failed after {max_retries} attempts for {url}")
    return None


async def extract_main_content(html: str, url: str) -> tuple[Optional[str], list]:
    """
    Extract main article content and images using trafilatura.

    Returns:
        Tuple of (text_content, images_list)
    """
    images = []

    # Always extract images first from the raw HTML
    if html:
        images = extract_images_from_html(html, url)
        logger.info(f"Extracted {len(images)} images from HTML")

    try:
        # Try trafilatura with images enabled
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_images=True,
            url=url,
            favor_precision=True,
        )
        if text and len(text) > 200:
            return text, images or []

        # Fallback with better settings - try without favor_precision
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_images=True,
            url=url,
        )
        if text and len(text) > 200:
            return text, images or []

        # If trafilatura returns nothing useful, try to extract content manually
        # Look for article/main/content divs
        article_patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<main[^>]*>(.*?)</main>',
            r'<div[^>]*class=["\'][^"\']*article[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
        ]

        for pattern in article_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if len(match) > 500:
                    # Clean the HTML but keep basic formatting
                    clean_text = re.sub(r'<[^>]+>', ' ', match)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if len(clean_text) > 200:
                        return clean_text, images or []

    except Exception as e:
        logger.warning(f"Trafilatura extraction failed: {e}")

    return None, images or []


def _should_skip_image_url(url: str, base_domain: str = "") -> bool:
    """
    Check if an image URL should be skipped (not content image).
    Returns True if the URL should be skipped.
    
    FIX: Comprehensive filter for QR codes, social widgets, and non-content images.
    """
    url_lower = url.lower()
    
    # Comprehensive skip patterns for UI elements and non-content images
    skip_patterns = [
        # UI Elements
        'icon', 'icons', 'icon-', '-icon', 'icono',
        'logo', 'logos', '-logo',
        'avatar', 'avatars', 'user-', '-user', 'profile-',
        'favicon', 'favico',
        'button', 'btn-', '-btn', 'buttons',
        'nav-', '-nav', 'menu-', '-menu', 'hamburger',
        'header', 'footer', 'sidebar',
        'banner', 'promo', 'promotion',

        # Controls & Interactions
        'close', 'cancel', 'dismiss', 'exit',
        'play', 'pause', 'stop', 'mute', 'unmute', 'vol-', '-vol',
        'zoom', '-zoom', 'zoom-in', 'zoom-out', 'magnify',
        'expand', 'collapse', 'minimize', 'maximize',
        'share', 'like', 'heart', 'bookmark', 'save', 'print',
        'download', 'upload', 'attach', 'attachment',
        'reply', 'retweet', 'reblog', 'share',
        'arrow', 'chevron', 'caret', 'triangle',
        'check', 'checkbox', 'radio', 'toggle',
        'search', 'magnifier', 'lens',

        # Ads & Tracking
        'pixel', 'tracking', 'beacon', 'analytics',
        'ad-', '-ad', '/ads/', 'advertisement', 'sponsor',
        'banner', 'leaderboard', 'skyscraper',
        'marketing', 'campaign',

        # Loading & States
        'spinner', 'loading', 'loader', 'skeleton',
        'placeholder', 'dummy', 'blank', 'transparent',
        'data:image', 'base64',

        # Social & External
        'social', 'share-', '-share', 'widget',
        'badge', 'badge-',

        # Common non-content patterns
        'sprite', 'sprites', 'strip', 'tile',
        '1x1', '2x2', '88x31', '120x60', '125x125',
        'background', 'bg-', '-bg', 'overlay',

        # Common tracking/ads domains
        'doubleclick', 'googlesyndication', 'googleadservices',
        'facebook.net/tr', 'fbcdn', 'connect.facebook',
        'amazon-adsystem', 'adnxs', 'criteo',
        'taboola', 'outbrain', 'mgid',

        # FIX: QR Codes & Social Widgets (36Kr specific and general)
        # These are tracking widgets, not content images
        'qrcode', 'qr-code', 'qr_code', '/qr/', 'qr_',
        'qrimg', 'qr-img', 'qrcode_', '_qrcode',
        'weibo', 'weixin', 'wechat', 'tencent',
        'scan', 'scan-', '-scan',
        'follow', 'subscribe',
        'publicaccount', 'public-account', 'gongzhong',
        'sinaimg', 'weiboimg',
        
        # Additional Chinese social/tracking patterns
        'ws.36kr.com',  # 36Kr WebSocket/tracking
        'bdzs.36kr.com',  # 36Kr tracking
        'tui.36kr.com',  # 36Kr recommendation/tracking
        's.36kr.com',  # 36Kr short URL/tracking
        'stats.36kr.com',  # 36Kr statistics/tracking
        'e.36kr.com',  # 36Kr email tracking
        'm.36kr.com',  # 36Kr mobile/tracking
    ]
    
    # Check skip patterns
    if any(p in url_lower for p in skip_patterns):
        return True
    
    # Skip very short URLs (likely invalid or truncated)
    if len(url) < 30:
        return True
    
    # Skip URLs with suspicious patterns
    if any(susp in url_lower for susp in ['.gif', 'emoji', 'emoticon', 'sticker']):
        return True
    
    # Check width parameter if present
    import re as regex_module
    width_match = regex_module.search(r'w=(\d+)', url_lower)
    if width_match:
        width = int(width_match.group(1))
        # Skip small images even if width param is set
        if width < 200:
            return True
        # Skip very large images (>3000) as they might be banners
        if width > 3000 and base_domain not in url_lower:
            pass  # Allow large images from same domain
    
    # Check for suspicious file patterns
    filename = regex_module.search(r'/([^/]+\.[a-z]{3,4})(?:[?#]|$)', url_lower)
    if filename:
        fname = filename.group(1).lower()
        # Skip common non-content filenames
        bad_names = ['spinner.gif', 'loading.gif', 'pixel.gif', 'blank.gif', 'transparent.gif']
        if fname in bad_names:
            return True
    
    # Check domain - skip obvious external ad/tracking images
    if base_domain:
        img_domain_match = regex_module.search(r'https?://([^/]+)', url_lower)
        if img_domain_match:
            img_domain = img_domain_match.group(1).replace('www.', '')
            # Skip if different domain AND contains ad-related keywords
            if img_domain != base_domain:
                ad_domains = ['doubleclick', 'googlesyndication', 'googleadservices',
                             'facebook.net', 'amazon-adsystem', 'criteo', 'taboola',
                             'outbrain', 'adnxs', 'ads', 'tracking', 'pixel', 'beacon',
                             '36kr.com', 'krplus', 'bastpost', 'xiaozhuan']
                if any(ad in img_domain for ad in ad_domains):
                    return True
    
    return False


def extract_images_from_html(html: str, base_url: str = "", max_images: int = 20) -> list[dict]:
    """
    Extract image URLs from HTML using regex.
    Returns list of {"url": str, "alt": str, "credit": str}

    Improved to extract:
    - og:image (highest priority - article featured image)
    - Article content images (from article/main/body sections)
    - General content images (filtered for quality)
    
    FIX: All images now pass through _should_skip_image_url filter.
    """
    import re as regex_module
    import urllib.parse

    images = []
    try:
        # Parse base domain for filtering external ads/tracking images
        base_domain = ""
        if base_url:
            try:
                parsed = urllib.parse.urlparse(base_url)
                base_domain = parsed.netloc.replace('www.', '')
            except:
                pass

        # === PHASE 1: Extract og:image (highest priority) ===
        og_images = []
        og_patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+property=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        ]
        for pattern in og_patterns:
            matches = regex_module.findall(pattern, html, regex_module.IGNORECASE)
            og_images.extend(matches)

        # Add og:images first (highest priority) - BUT filter first!
        for og_url in og_images[:3]:  # Take up to 3 og images
            if base_url:
                og_url = urllib.parse.urljoin(base_url, og_url)
            if og_url.startswith('http'):
                # FIX: Filter og:images through skip check
                if _should_skip_image_url(og_url, base_domain):
                    continue
                if og_url not in [img.get('url') for img in images]:
                    images.insert(0, {"url": og_url, "alt": "", "credit": "Article Featured Image", "source": "og"})

        # === PHASE 2: Extract from article content sections (high quality) ===
        content_section_images = []
        article_patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<main[^>]*>(.*?)</main>',
            r'<div[^>]*class=["\'][^"\']*(?:content|article|post|entry|story|body)[^"\']*["\'][^>]*>(.*?)</div>',
        ]

        for pattern in article_patterns:
            section_matches = regex_module.findall(pattern, html, regex_module.DOTALL | regex_module.IGNORECASE)
            for section_html in section_matches:
                if len(section_html) > 1000:  # Only process substantial sections
                    # Extract images from this section
                    section_img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
                    section_imgs = regex_module.findall(section_img_pattern, section_html, regex_module.IGNORECASE)
                    # FIX: Filter content section images through skip check
                    for img_url in section_imgs:
                        if not _should_skip_image_url(img_url, base_domain):
                            content_section_images.append(img_url)

        # === PHASE 3: Extract from entire page (fallback) ===
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        img_matches = regex_module.findall(img_pattern, html, regex_module.IGNORECASE)

        # Also check data-src for lazy-loaded images
        lazy_pattern = r'data-src=["\']([^"\']+)["\']'
        lazy_matches = regex_module.findall(lazy_pattern, html, regex_module.IGNORECASE)

        # Also check data-lazy-src
        lazy_src_pattern = r'data-lazy-src=["\']([^"\']+)["\']'
        lazy_src_matches = regex_module.findall(lazy_src_pattern, html, regex_module.IGNORECASE)

        # Also check srcset for responsive images
        srcset_pattern = r'srcset=["\']([^"\']+)["\']'
        srcset_matches = regex_module.findall(srcset_pattern, html, regex_module.IGNORECASE)

        # Extract individual URLs from srcset
        all_urls = set()
        for match in srcset_matches:
            # srcset format: "url1 300w, url2 600w, url3 900w"
            urls = regex_module.findall(r'(https?://[^\s"\'<>,]+)', match)
            all_urls.update(urls)

        # Combine all URLs
        all_urls.update(img_matches)
        all_urls.update(lazy_matches)
        all_urls.update(lazy_src_matches)

        # === PHASE 4: Comprehensive filtering using helper function ===
        for url in all_urls:
            # Skip if already added
            if url in [img.get('url') for img in images]:
                continue

            # FIX: Use unified filter function for all URLs
            if _should_skip_image_url(url, base_domain):
                continue

            # Determine if from content section (higher priority)
            is_content_image = url in content_section_images

            images.append({
                "url": url,
                "alt": "",
                "credit": "",
                "source": "content" if is_content_image else "page"
            })

        return images
    except Exception as e:
        logger.warning(f"Image extraction failed: {e}")
        return []


async def fetch_article_content(
    article,
    source,
    use_flaresolverr: bool = False,
) -> tuple[str, str, list]:
    """
    Fetch full article content using 4-tier escalation.

    Returns:
        Tuple of (content, article_type, images)
        - content: full text or summary fallback
        - article_type: 'quick' or 'deep'
        - images: list of {"url": str, "alt": str, "credit": str}
    """
    article_type = "quick"
    content = None
    images = []

    # Tier 1: RSS content if already has enough data
    if article.original_summary and len(article.original_summary) > 500:
        logger.info(f"Using RSS summary (>500 chars) for {article.original_url}")
        # Try to extract images even from RSS content
        # First, try HTTP fetch for images only
        html_content = await fetch_with_headers(article.original_url)
        if html_content:
            extracted_images = extract_images_from_html(html_content, article.original_url)
            if extracted_images:
                images = extracted_images
                logger.info(f"Extracted {len(images)} images from article page for RSS summary")
        # Return summary with extracted images
        return article.original_summary, "quick", images

    # Tier 2: HTTP direct
    extracted_images = []
    content = await fetch_with_headers(article.original_url)
    if content:
        main_content, extracted_images = await extract_main_content(content, article.original_url)
        if main_content and len(main_content) > 500:
            article_type = "deep"
            logger.info(f"Fetched deep content ({len(main_content)} chars) for {article.original_url}")
            return main_content, "deep", extracted_images or []
        # Even if content is short, we may have extracted images - save them
        if extracted_images:
            logger.info(f"Extracted {len(extracted_images)} images from article (content too short)")

    # Tier 3: FlareSolverr
    if use_flaresolverr or (source and source.requires_flaresolverr):
        logger.info(f"Attempting FlareSolverr for {article.original_url}")
        content = await fetch_via_flaresolverr(article.original_url)
        if content:
            main_content, fs_images = await extract_main_content(content, article.original_url)
            # Merge images from FlareSolverr with previous images
            if fs_images:
                extracted_images = fs_images
            if main_content and len(main_content) > 500:
                article_type = "deep"
                logger.info(f"FlareSolverr fetched deep content ({len(main_content)} chars)")
                return main_content, "deep", extracted_images or []
            if fs_images:
                logger.info(f"Extracted {len(fs_images)} images from FlareSolverr (content too short)")

    # Tier 4: Fallback to RSS summary - ALWAYS preserve extracted images
    logger.info(f"Falling back to RSS summary for {article.original_url}")
    article_type = "quick"
    
    # === FIX: Try to extract ALL images from article HTML before using RSS fallback ===
    if not extracted_images:
        # Try to fetch HTML to extract images (even if content fetch failed)
        logger.info(f"No images extracted yet, trying to fetch HTML for images...")
        html_content = await fetch_with_headers(article.original_url)
        if html_content:
            extracted_images = extract_images_from_html(html_content, article.original_url)
            if extracted_images:
                logger.info(f"Extracted {len(extracted_images)} images from article HTML")
    
    # Also include original_image_url from RSS if available and not already in list
    if article.original_image_url:
        existing_urls = [img.get("url", "") for img in extracted_images]
        if article.original_image_url not in existing_urls:
            # Add to the end (featured image already captured by og:image if exists)
            extracted_images.append({
                "url": article.original_image_url,
                "alt": "",
                "credit": "",
                "source": "rss"
            })
            logger.info(f"Added original_image_url from RSS to image list")
    
    logger.info(f"Returning with {len(extracted_images)} images")
    return article.original_summary or "", "quick", extracted_images


async def fetch_multiple(urls: list[str], concurrency: int = 5) -> dict[str, Optional[str]]:
    """
    Fetch multiple URLs concurrently with rate limiting.
    """
    results = {}

    async def fetch_one(url: str) -> tuple[str, Optional[str]]:
        content = await fetch_with_headers(url)
        return url, content

    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_limited(url: str) -> tuple[str, Optional[str]]:
        async with semaphore:
            return await fetch_one(url)

    tasks = [fetch_limited(url) for url in urls]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, tuple):
            url, content = result
            results[url] = content
        else:
            logger.warning(f"Fetch failed: {result}")

    return results
