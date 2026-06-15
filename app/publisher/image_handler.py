"""
Image handling for WordPress uploads.
Optimized to use original URLs when possible to save bandwidth and storage.
"""
import io
import logging
import re
from typing import Optional

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


# CDNs that require authentication/signature (must download these)
PROTECTED_CDNS = [
    'guim.co.uk',       # The Guardian
    'theguardian.com',   # Guardian article images
    'i.guim.co.uk',      # Guardian CDN
]

# CDNs that are public and can be used directly
PUBLIC_CDNS = [
    # Major CDNs
    'cdn.mos.cms.futurecdn.net',  # Futurecdn (TechRadar, etc.)
    'images.unsplash.com',          # Unsplash
    'picsum.photos',               # Lorem Picsum
    'via.placeholder.com',          # Placeholder
    'i.imgur.com',                 # Imgur
    'ibb.co',                       # ImageBB
    'cdnimages',                    # Generic CDN
    # News sites
    'media.cnn.com',               # CNN
    'media.heraldsun.com.au',      # Herald Sun
    'static.theaustralian.com.au', # The Australian
    'news.com.au',                  # News.com.au
    'nypost.com',                  # NY Post
    'nytimes.com',                 # NYT
    'bbc.co.uk',                   # BBC
    'bbc.com',                     # BBC
    'reuters.com',                 # Reuters
    'apnews.com',                  # AP News
    'afp.com',                     # AFP
    # Tech sites
    'cdn.vox-cdn.com',             # Vox
    'cdn.theverge.com',            # The Verge
    'cdn.arstechnica.com',         # Ars Technica
    'techcrunch.com/wp-content',   # TechCrunch
    'cdn.mashable.com',            # Mashable
    'i.insider.com',               # Insider
    # Business/Finance
    'cdn.cnbc.com',                # CNBC
    'cdn-fs.benzinga.com',         # Benzinga
    'images.mktw.net',             # MarketWatch
    's.wsj.net',                  # WSJ
    'si.wsj.net',                 # WSJ images
    # Entertainment
    'media.vanillaforums.com',     # Various
    'pmd.pmDd.co',                 # Various
    # Generic patterns that should work
    'wp.com',                      # WordPress.com CDN
    'cloudfront.net',              # CloudFront
    'akamai.net',                  # Akamai
    'fastly.net',                  # Fastly
    'cdnjs.cloudflare.com',        # CloudFlare CDNJS
    'img.youtube.com',             # YouTube thumbnails
    'i.ytimg.com',                # YouTube images
    # Social platforms
    'pbs.twimg.com',              # Twitter/X images
    'platform.twitter.com',        # Twitter cards
    'graph.facebook.com',          # Facebook
    'instagram.com',              # Instagram
    'cdninstagram.com',            # Instagram CDN
    # Stock image sites
    'gettyimages.com',             # Getty
    'gettyimages.com.au',          # Getty Australia
    'media.gettyimages.com',       # Getty media
    # News/Article specific
    'ichef.bbci.co.uk',           # BBC images
    'ichef.',                      # BBC variants
    'news.gov.',                   # Various gov
    # Additional common CDNs
    'res.cloudinary.com',          # Cloudinary
    'images-na.ssl-images-amazon.com',  # Amazon
    'media.amazon.com',           # Amazon media
    'store-images.s-microsoft.com', # Microsoft Store
]


def is_image_url_public(url: str) -> bool:
    """
    Check if an image URL is publicly accessible without authentication.
    Returns True if we can use the URL directly, False if we need to download.
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Check if it's a protected CDN
    for cdn in PROTECTED_CDNS:
        if cdn in url_lower:
            return False
    
    # Check if it's a known public CDN
    for cdn in PUBLIC_CDNS:
        if cdn in url_lower:
            return True
    
    # Default: assume public but log warning
    logger.info(f"Unknown CDN, assuming public: {url[:80]}...")
    return True


async def test_image_accessible(url: str) -> bool:
    """
    Test if an image URL is accessible with a quick HEAD request.
    Returns True if the image can be fetched.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*",
        }
        
        # Add referer for known CDNs
        if "theguardian.com" in url or "guim.co.uk" in url:
            headers["Referer"] = "https://www.theguardian.com/"
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.head(url, headers=headers)
            if response.status_code == 200:
                return True
            logger.warning(f"Image not accessible: {response.status_code} - {url[:80]}")
            return False
    except Exception as e:
        logger.warning(f"Failed to test image access: {e} - {url[:80]}")
        return False


def clean_image_url(url: str) -> str:
    """
    Clean image URL by removing tracking parameters while keeping essential ones.
    """
    try:
        from urllib.parse import urlparse, parse_qs, urlencode
        
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        
        # Parameters to remove (tracking, signatures)
        remove_params = {
            'sig', 'signature', 'token', 'x-token',
            'expires', 'expiry', 'usg',
        }
        
        # Parameters to keep (image settings)
        keep_params = {
            'w', 'width', 'h', 'height', 'q', 'quality',
            'fmt', 'format', 'auto', 'fit', 's',
        }
        
        clean_qs = {k: v for k, v in qs.items() 
                     if k.lower() not in remove_params and k.lower() in keep_params}
        
        clean_query = urlencode(clean_qs, doseq=True)
        clean_url = parsed._replace(query=clean_query).geturl()
        
        if clean_url.endswith('?'):
            clean_url = clean_url[:-1]
            
        return clean_url
    except Exception:
        return url


async def get_image_from_article_page(article_url: str, image_url: str) -> Optional[str]:
    """
    Try to get a fresh image URL from the article page HTML.
    Returns the new URL if found, None otherwise.
    """
    try:
        from app.config import get_settings
        
        settings = get_settings()
        
        # Try FlareSolverr first for Cloudflare-protected sites (Guardian, etc.)
        if "theguardian.com" in article_url or "guim.co.uk" in image_url:
            if settings.flaresolverr_url:
                logger.info(f"Trying FlareSolverr for Guardian article: {article_url}")
                new_url = await get_image_url_via_flaresolverr(article_url)
                if new_url:
                    return new_url
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(article_url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch article page: {response.status_code}")
                return None
                
            html = response.text
            
            # Extract og:image from HTML using multiple patterns
            import html as html_module
            
            # More comprehensive patterns for og:image
            patterns = [
                # Standard og:image patterns
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']og:image["\']',
                # Twitter cards
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
                # Schema.org
                r'<meta[^>]+itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+itemprop=["\']image["\']',
            ]
            
            for pattern in patterns:
                og_match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if og_match:
                    og_url = html_module.unescape(og_match.group(1))
                    if og_url and og_url.startswith('http'):
                        logger.info(f"Found fresh og:image from article page: {og_url[:80]}...")
                        return og_url
            
            # Fallback: try to find image in JSON-LD structured data
            jsonld_pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            jsonld_matches = re.findall(jsonld_pattern, html, re.DOTALL)
            for jsonld in jsonld_matches:
                try:
                    import json
                    data = json.loads(jsonld)
                    if isinstance(data, dict):
                        image = data.get('image')
                        if isinstance(image, str) and image.startswith('http'):
                            return image
                        elif isinstance(image, dict) and 'url' in image:
                            return image['url']
                        elif isinstance(image, list) and len(image) > 0:
                            first = image[0]
                            if isinstance(first, str):
                                return first
                            elif isinstance(first, dict) and 'url' in first:
                                return first['url']
                except:
                    continue
            
    except Exception as e:
        logger.warning(f"Failed to get image from article page: {e}")
    
    return None


async def get_image_url_via_flaresolverr(article_url: str) -> Optional[str]:
    """
    Fetch article page via FlareSolverr and extract the og:image URL.
    Returns the URL if found.
    """
    try:
        import random
        from app.config import get_settings
        
        settings = get_settings()
        
        if not settings.flaresolverr_url:
            return None
        
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {
                "cmd": "request.get",
                "url": article_url,
                "maxTimeout": 60000,
            }
            
            # Clean up URL
            flaresolverr_url = settings.flaresolverr_url.rstrip('/')
            if flaresolverr_url.endswith('/v1'):
                flaresolverr_url = flaresolverr_url[:-3]
            
            response = await client.post(
                f"{flaresolverr_url}/v1",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "ok" and "solution" in data:
                html = data["solution"].get("response", "")
                if html and len(html) > 500:
                    import html as html_module
                    
                    patterns = [
                        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                        r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                    ]
                    
                    for pattern in patterns:
                        og_match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                        if og_match:
                            og_url = html_module.unescape(og_match.group(1))
                            if og_url and og_url.startswith('http'):
                                logger.info(f"Found og:image via FlareSolverr: {og_url[:80]}...")
                                return og_url
                                
    except Exception as e:
        logger.warning(f"FlareSolverr image fetch failed: {e}")
    
    return None


async def download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download image from URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        
        # Guardian images need specific headers
        if "guim.co.uk" in url:
            headers.update({
                "Referer": "https://www.theguardian.com/",
            })
        
        clean_url = clean_image_url(url)
        
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(clean_url, headers=headers)
            
            if response.status_code in (401, 403):
                logger.warning(f"Image requires authentication: {url[:80]}")
                return None
                
            response.raise_for_status()
            content = response.content
            if len(content) > 1000:
                logger.info(f"Downloaded image: {len(content)} bytes from {clean_url}")
                return content
            else:
                logger.warning(f"Image too small: {len(content)} bytes")
                return None
    except Exception as e:
        logger.warning(f"Failed to download image {url}: {e}")
        return None


def resize_image(image_bytes: bytes, max_width: int = 1200, quality: int = 85) -> bytes:
    """Resize image if needed."""
    try:
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()

    except Exception as e:
        logger.warning(f"Image resize failed: {e}")
        return image_bytes


async def get_featured_image_info(
    image_url: str,
    slug: str,
    source_credit: str = "",
    article_url: str = "",
) -> Optional[dict]:
    """
    Get featured image info for WordPress.
    
    Attempts to download and upload image to WordPress media library.
    Falls back to external URL if upload fails.
    
    Returns dict with:
    - type: 'media' (uploaded to WordPress) or 'url' (external)
    - media_id: WordPress media ID (if type='media')
    - url: Image URL (WordPress URL or external URL)
    - caption: Source credit text
    """
    if not image_url:
        logger.warning("No image URL provided")
        return None
    
    # Clean the URL
    image_url = clean_image_url(image_url)
    
    # First, try to download and upload to WordPress
    try:
        from app.publisher.wordpress import get_wordpress_client
        client = get_wordpress_client()
        
        logger.info(f"Attempting to download and upload featured image: {image_url[:80]}...")
        image_bytes = await download_image(image_url)
        
        if image_bytes:
            # Resize image if needed
            image_bytes = resize_image(image_bytes)
            
            # Create filename
            filename = f"{slug[:40]}-{hash(image_bytes) % 10000}.jpg"
            
            # Upload to WordPress
            result = client.upload_media(
                image_bytes=image_bytes,
                filename=filename,
                mime_type="image/jpeg",
                alt_text=source_credit,
                caption=source_credit,
            )
            
            if result:
                logger.info(f"Successfully uploaded featured image to WordPress: media_id={result.get('id')}")
                return {
                    "type": "media",
                    "media_id": result.get("id"),
                    "url": result.get("url"),
                    "caption": source_credit,
                    "alt": source_credit,
                }
            else:
                logger.warning(f"Failed to upload featured image to WordPress, using external URL")
        else:
            logger.warning(f"Failed to download featured image")
    except Exception as e:
        logger.warning(f"Error in featured image upload attempt: {e}")
    
    # Fallback: test if image is accessible and use external URL
    if await test_image_accessible(image_url):
        logger.info(f"Using external URL for featured image: {image_url[:80]}...")
        return {
            "type": "url",
            "url": image_url,
            "caption": source_credit,
            "alt": source_credit,
        }
    
    # Try to find a better URL from the article page
    if article_url:
        fresh_url = await get_image_from_article_page(article_url, image_url)
        if fresh_url:
            fresh_url = clean_image_url(fresh_url)
            if await test_image_accessible(fresh_url):
                logger.info(f"Using fresh image URL from article page: {fresh_url[:80]}...")
                return {
                    "type": "url",
                    "url": fresh_url,
                    "caption": source_credit,
                    "alt": source_credit,
                }
    
    logger.warning(f"Featured image not accessible: {image_url[:80]}")
    return None


async def process_content_images(
    images: list[dict],
    slug: str,
    source_credit: str = "",
    max_images: int = 10,
) -> list[dict]:
    """
    Process content images from crawled_images.
    
    For public images: Returns URL mapping without download
    For protected images: Downloads and uploads
    
    Returns list of {"original_url": str, "url": str, "type": str, "alt": str}
    """
    results = []
    
    for i, img in enumerate(images[:max_images]):
        img_url = img.get("url", "")
        if not img_url:
            continue
        
        alt_text = img.get("alt", source_credit) or source_credit
        img_url = clean_image_url(img_url)
        
        # Check if public
        if is_image_url_public(img_url):
            if await test_image_accessible(img_url):
                results.append({
                    "original_url": img_url,
                    "url": img_url,
                    "type": "external",
                    "alt": alt_text,
                })
                logger.info(f"Using external image: {img_url[:80]}")
                continue
        
        # Try download and upload
        try:
            image_bytes = await download_image(img_url)
            if not image_bytes:
                logger.warning(f"Failed to download content image: {img_url}")
                continue
            
            image_bytes = resize_image(image_bytes)
            
            from app.publisher.wordpress import get_wordpress_client
            client = get_wordpress_client()
            
            filename = f"{slug[:40]}-img{i+1}-{hash(image_bytes) % 10000}.jpg"
            
            result = client.upload_media(
                image_bytes=image_bytes,
                filename=filename,
                mime_type="image/jpeg",
                alt_text=alt_text,
                caption=alt_text,
            )
            
            if result:
                results.append({
                    "original_url": img_url,
                    "url": result.get("url"),
                    "type": "internal",
                    "alt": alt_text,
                })
                logger.info(f"Uploaded content image: {result.get('url')}")
        except Exception as e:
            logger.warning(f"Error processing image {img_url}: {e}")
            continue
    
    return results


async def search_unsplash_images(keywords: list[str], count: int = 5) -> list[dict]:
    """
    Search for images on Unsplash using their public API.
    
    Args:
        keywords: List of search keywords (e.g., ["tech", "business"])
        count: Number of images to return (default 5)
    
    Returns:
        List of dicts with {"id", "url", "thumb", "credit", "credit_url"}
    """
    if not keywords:
        return []
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        # Build search query from keywords
        query = " ".join(keywords[:3])  # Use max 3 keywords
        logger.info(f"Searching Unsplash for: {query}")
        
        # Try to use Unsplash API if key is available
        if settings.unsplash_access_key:
            # Full API call with access key
            headers = {
                "Authorization": f"Client-ID {settings.unsplash_access_key}",
                "Accept-Version": "v1",
            }
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://api.unsplash.com/search/photos",
                    headers=headers,
                    params={
                        "query": query,
                        "per_page": count,
                        "orientation": "landscape",
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for photo in data.get("results", [])[:count]:
                        results.append({
                            "id": photo.get("id", ""),
                            "url": photo.get("urls", {}).get("regular", ""),
                            "thumb": photo.get("urls", {}).get("thumb", ""),
                            "credit": f"Photo by {photo.get('user', {}).get('name', 'Unsplash')}",
                            "credit_url": photo.get("user", {}).get("links", {}).get("html", "https://unsplash.com"),
                        })
                    if results:
                        logger.info(f"Found {len(results)} images from Unsplash API")
                        return results
        
        # Fallback: Use known good images from Unsplash (images.unsplash.com)
        # Using a predefined list of high-quality, reliable images
        logger.info("Using predefined fallback images")
        fallback_urls = [
            "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80",
            "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80",
            "https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=1200&q=80",
            "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=1200&q=80",
            "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
        ]
        
        results = []
        for i in range(min(count, len(fallback_urls))):
            img_url = fallback_urls[i]
            results.append({
                "id": f"fallback_{i}",
                "url": img_url,
                "thumb": img_url.replace("w=1200", "w=400"),
                "credit": "Unsplash",
                "credit_url": "https://unsplash.com",
            })
        
        return results
        
    except Exception as e:
        logger.warning(f"Unsplash search failed: {e}")
        return []


async def download_and_upload_image(url: str, slug: str, alt_text: str = "") -> Optional[dict]:
    """
    Download an image and upload it to WordPress.
    
    Args:
        url: Image URL to download
        slug: Article slug for filename
        alt_text: Alt text for the image
    
    Returns:
        Dict with {"url", "media_id"} or None if failed
    """
    try:
        from app.publisher.wordpress import get_wordpress_client
        client = get_wordpress_client()
        
        # Download with retry
        image_bytes = await download_image_with_retry(url, max_retries=3)
        if not image_bytes:
            logger.warning(f"Failed to download image: {url[:80]}")
            return None
        
        # Resize if needed
        image_bytes = resize_image(image_bytes)
        
        # Generate filename
        filename = f"{slug[:40]}-{abs(hash(url)) % 10000}.jpg"
        
        # Upload to WordPress
        result = client.upload_media(
            image_bytes=image_bytes,
            filename=filename,
            mime_type="image/jpeg",
            alt_text=alt_text,
            caption=alt_text,
        )
        
        if result:
            return {
                "url": result.get("url"),
                "media_id": result.get("id"),
            }
        
        return None
        
    except Exception as e:
        logger.warning(f"Download and upload failed for {url[:80]}: {e}")
        return None


async def download_image_with_retry(url: str, max_retries: int = 3, timeout: int = 30) -> Optional[bytes]:
    """
    Download image with retry logic for handling hotlink protection.
    
    Args:
        url: Image URL to download
        max_retries: Number of retry attempts (default 3)
        timeout: Request timeout in seconds
    
    Returns:
        Image bytes or None if all retries fail
    """
    # Add referer for known sites that block hotlinking
    # FIX: Added 36Kr and other Chinese sites
    referers = {
        "vnexpress.net": "https://vnexpress.net/",
        "thanhnien.vn": "https://thanhnien.vn/",
        "nytimes.com": "https://www.nytimes.com/",
        "bbc.com": "https://www.bbc.com/",
        "theguardian.com": "https://www.theguardian.com/",
        "reuters.com": "https://www.reuters.com/",
        "apnews.com": "https://www.apnews.com/",
        "cnn.com": "https://www.cnn.com/",
        "techcrunch.com": "https://techcrunch.com/",
        "bloomberg.com": "https://www.bloomberg.com/",
        # Chinese sites
        "36kr.com": "https://36kr.com/",
        "img.36kr.com": "https://36kr.com/",
        "krplus-cdn.bastpost.com": "https://36kr.com/",
        "xiaozhuan-cdn.com": "https://36kr.com/",
        "sinaimg.cn": "https://weibo.com/",
        "weibo.com": "https://weibo.com/",
        "qq.com": "https://www.qq.com/",
        "163.com": "https://www.163.com/",
        "sohu.com": "https://www.sohu.com/",
    }
    
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }
            
            # Add referer if known site
            url_lower = url.lower()
            for site, referer in referers.items():
                if site in url_lower:
                    headers["Referer"] = referer
                    break
            
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                # Check for hotlink blocking
                if response.status_code in (401, 403, 429):
                    logger.warning(f"Image blocked (status {response.status_code}), attempt {attempt + 1}/{max_retries}: {url[:80]}")
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    continue
                
                response.raise_for_status()
                content = response.content
                
                # Validate image content
                if len(content) > 1000:
                    logger.info(f"Downloaded image: {len(content)} bytes (attempt {attempt + 1})")
                    return content
                else:
                    logger.warning(f"Image too small: {len(content)} bytes")
                    
        except httpx.TimeoutException:
            logger.warning(f"Timeout downloading image, attempt {attempt + 1}/{max_retries}")
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code}, attempt {attempt + 1}/{max_retries}")
        except Exception as e:
            logger.warning(f"Download error: {e}, attempt {attempt + 1}/{max_retries}")
        
        if attempt < max_retries - 1:
            import asyncio
            await asyncio.sleep(1 * (attempt + 1))
    
    logger.warning(f"All {max_retries} attempts failed for: {url[:80]}")
    return None


# Fallback images by category - multiple options for variety
# Tech category: ~250 images covering programming, AI, cloud, cybersecurity, etc.
# Finance category: ~250 images covering stocks, crypto, business, economy, etc.
CATEGORY_FALLBACK_IMAGES = {
    "tech": [
        # Programming & Coding (50+)
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=1200&q=80",  # MacBook Pro
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",  # MacBook with code
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&q=80",  # MacBook coding
        "https://images.unsplash.com/photo-1628258334105-2a0b3d6efee1?w=1200&q=80",  # MacBook black table
        "https://images.unsplash.com/photo-1484417894907-623942c8ee29?w=1200&q=80",  # MacBook programming
        "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=1200&q=80",  # Computer monitor
        "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=1200&q=80",  # Gray laptop
        "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1200&q=80",  # Black laptop
        "https://images.unsplash.com/photo-1595675024853-0f3ec9098ac7?w=1200&q=80",  # Silver laptop
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",  # HTML codes
        "https://images.unsplash.com/photo-1523800503107-5bc3ba2a6f81?w=1200&q=80",  # Gray laptop coding
        "https://images.unsplash.com/photo-1577375729152-4c8b5fcda381?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1607705703571-c5a8695f18f6?w=1200&q=80",  # Samsung monitor
        "https://images.unsplash.com/photo-1499673610122-01c7122c5dcb?w=1200&q=80",  # MacBook Air
        "https://images.unsplash.com/photo-1509966756634-9c23dd6e6815?w=1200&q=80",  # Laptop showing codes
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Circuit board
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",  # Tech
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",  # Cyber security
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",  # Tech workspace
        "https://images.unsplash.com/photo-1537432376769-00f5c2f4c8d2?w=1200&q=80",  # Developer coding
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=1200&q=80",  # Code on screen
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",  # MacBook desk
        "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=1200&q=80",  # Laptop coding
        "https://images.unsplash.com/photo-1544256718-3bcf237f3974?w=1200&q=80",  # Code terminal
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",  # Code laptop
        "https://images.unsplash.com/photo-1581089778245-3ce67677f718?w=1200&q=80",  # Programmer
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",  # HTML code
        "https://images.unsplash.com/photo-1517134191118-9d595e4c8c2b?w=1200&q=80",  # Laptop setup
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Matrix code
        "https://images.unsplash.com/photo-1550439062-609e1531270e?w=1200&q=80",  # Code editor
        "https://images.unsplash.com/photo-1509966756634-9c23dd6e6815?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=1200&q=80",  # Code screen
        "https://images.unsplash.com/photo-1509967419530-da38b4704bc6?w=1200&q=80",  # Programming
        "https://images.unsplash.com/photo-1544256718-3bcf237f3974?w=1200&q=80",  # Terminal
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Digital code
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200&q=80",  # MacBook laptop
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",  # Laptop coding
        "https://images.unsplash.com/photo-1537432376769-00f5c2f4c8d2?w=1200&q=80",  # Desk coding
        
        # AI & Robotics (50+)
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&q=80",  # AI brain
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&q=80",  # AI robot
        "https://images.unsplash.com/photo-1485829404706-64b70704e7e9?w=1200&q=80",  # Robot
        "https://images.unsplash.com/photo-1507146153580-69a1fe6d8aa1?w=1200&q=80",  # Robot arm
        "https://images.unsplash.com/photo-1555255707-c0790f9d7d7e?w=1200&q=80",  # AI neural
        "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=1200&q=80",  # Robot face
        "https://images.unsplash.com/photo-1485199698948-d46a09e771c9?w=1200&q=80",  # Robot technology
        "https://images.unsplash.com/photo-1555685812-4b943f1cb0eb?w=1200&q=80",  # AI
        "https://images.unsplash.com/photo-1535378620166-273708d44e0c?w=1200&q=80",  # Robot
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Circuit
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",  # Security
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Matrix
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&q=80",  # Neural network
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&q=80",  # Futuristic AI
        "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?w=1200&q=80",  # AI art
        "https://images.unsplash.com/photo-1620714224005-9d67f7f5d9e7?w=1200&q=80",  # Robot AI
        "https://images.unsplash.com/photo-1617802690992-15d93263d3a9?w=1200&q=80",  # Tech abstract
        "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=1200&q=80",  # AI concept
        "https://images.unsplash.com/photo-1555255707-c0790f9d7d7e?w=1200&q=80",  # Brain AI
        "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=1200&q=80",  # Robot hand
        "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&q=80",  # AI
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Chip
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",  # Tech blue
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",  # Tech workspace
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=1200&q=80",  # Code
        "https://images.unsplash.com/photo-1550439062-609e1531270e?w=1200&q=80",  # Editor
        "https://images.unsplash.com/photo-1488229297570-58520851e68c?w=1200&q=80",  # Futuristic
        
        # Cloud & Data (40+)
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",  # Earth data
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1200&q=80",  # Cloud
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",  # Server
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=80",  # Cloud computing
        "https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=1200&q=80",  # Data center
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Data visualization
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",  # Cloud storage
        "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=1200&q=80",  # Network
        "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=1200&q=80",  # Server room
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?w=1200&q=80",  # Cloud
        "https://images.unsplash.com/photo-1591696205602-2f950c417cb9?w=1200&q=80",  # Data
        "https://images.unsplash.com/photo-1580894894513-541e068a3e2b?w=1200&q=80",  # Tech blue
        "https://images.unsplash.com/photo-1560732488-6b0df240254a?w=1200&q=80",  # Digital
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Circuit
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&q=80",  # Internet
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1200&q=80",  # Cloud sky
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",  # Security
        "https://images.unsplash.com/photo-1573984699409-5ce1c2f30b4e?w=1200&q=80",  # Data stream
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",  # Code
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Matrix
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",  # Tech
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",  # Server rack
        "https://images.unsplash.com/photo-1555252332-0b5f6dfc0f83?w=1200&q=80",  # Network
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&q=80",  # Tech team
        
        # Cybersecurity (30+)
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",  # Cyber
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Chip
        "https://images.unsplash.com/photo-1563986768494-4dee2763ff3f?w=1200&q=80",  # Security
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",  # Lock
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Code
        "https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=1200&q=80",  # Server
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&q=80",  # Internet
        "https://images.unsplash.com/photo-1560732488-6b0df240254a?w=1200&q=80",  # Digital
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Matrix
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",  # Server
        "https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=1200&q=80",  # Data center
        "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&q=80",  # AI
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",  # Tech
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",  # Blue tech
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Data viz
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=1200&q=80",  # MacBook
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&q=80",  # Coding
        "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=1200&q=80",  # Monitor
        "https://images.unsplash.com/photo-1604064641938-3bbee52942c7?w=1200&q=80",  # AI concept
        
        # Mobile & Devices (30+)
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&q=80",  # Smartphone
        "https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?w=1200&q=80",  # Phone
        "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=1200&q=80",  # Mobile
        "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=1200&q=80",  # Smartphone
        "https://images.unsplash.com/photo-1523206489230-c012c64b2b48?w=1200&q=80",  # Phone
        "https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=1200&q=80",  # Mobile tech
        "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&q=80",  # AI phone
        "https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=1200&q=80",  # iPhone
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&q=80",  # MacBook
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&q=80",  # Team tech
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",  # Workspace
        "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200&q=80",  # MacBook
        "https://images.unsplash.com/photo-1527192491265-7e15c55b1ed2?w=1200&q=80",  # Device
        "https://images.unsplash.com/photo-1553745987-ee20ed8fb4a7?w=1200&q=80",  # Phone
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&q=80",  # Mobile
        "https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?w=1200&q=80",  # Smartphone
        "https://images.unsplash.com/photo-1560732488-6b0df240254a?w=1200&q=80",  # Digital
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?w=1200&q=80",  # Cloud
        
        # Software & Apps (30+)
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",  # Code
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&q=80",  # MacBook
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",  # Desk
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=1200&q=80",  # Mac
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Circuit
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",  # Tech
        "https://images.unsplash.com/photo-1537432376769-00f5c2f4c8d2?w=1200&q=80",  # Coding
        "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1544256718-3bcf237f3974?w=1200&q=80",  # Terminal
        "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1200&q=80",  # Black laptop
        "https://images.unsplash.com/photo-1595675024853-0f3ec9098ac7?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=1200&q=80",  # Monitor
        "https://images.unsplash.com/photo-1607705703571-c5a8695f18f6?w=1200&q=80",  # Samsung
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200&q=80",  # MacBook
        "https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=1200&q=80",  # Laptop
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",  # Code
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",  # Mac
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",  # Chip
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",  # Matrix
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",  # HTML
        
        # Tech Abstract & Futuristic (20+)
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1200&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560732488-6b0df240254a?w=1200&q=80",
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",
        "https://images.unsplash.com/photo-1555255707-c0790f9d7d7e?w=1200&q=80",
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&q=80",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&q=80",
        "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?w=1200&q=80",
        "https://images.unsplash.com/photo-1617802690992-3bbee52942c7?w=1200&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",
        "https://images.unsplash.com/photo-1563986768494-4dee2763ff3f?w=1200&q=80",
        "https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=1200&q=80",
        "https://images.unsplash.com/photo-1573984699409-5ce1c2f30b4e?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",
        
        # More Programming & Development (50+)
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&q=80",
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=1200&q=80",
        "https://images.unsplash.com/photo-1484417894907-623942c8ee29?w=1200&q=80",
        "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=1200&q=80",
        "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=1200&q=80",
        "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1200&q=80",
        "https://images.unsplash.com/photo-1595675024853-0f3ec9098ac7?w=1200&q=80",
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",
        "https://images.unsplash.com/photo-1523800503107-5bc3ba2a6f81?w=1200&q=80",
        "https://images.unsplash.com/photo-1577375729152-4c8b5fcda381?w=1200&q=80",
        "https://images.unsplash.com/photo-1607705703571-c5a8695f18f6?w=1200&q=80",
        "https://images.unsplash.com/photo-1499673610122-01c7122c5dcb?w=1200&q=80",
        "https://images.unsplash.com/photo-1509966756634-9c23dd6e6815?w=1200&q=80",
        "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=1200&q=80",
        "https://images.unsplash.com/photo-1544256718-3bcf237f3974?w=1200&q=80",
        "https://images.unsplash.com/photo-1581089778245-3ce67677f718?w=1200&q=80",
        "https://images.unsplash.com/photo-1517134191118-9d595e4c8c2b?w=1200&q=80",
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=1200&q=80",
        "https://images.unsplash.com/photo-1550439062-609e1531270e?w=1200&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",
        "https://images.unsplash.com/photo-1537432376769-00f5c2f4c8d2?w=1200&q=80",
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=1200&q=80",
        "https://images.unsplash.com/photo-1628258334105-2a0b3d6efee1?w=1200&q=80",
        "https://images.unsplash.com/photo-1484417894907-623942c8ee29?w=1200&q=80",
        "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?w=1200&q=80",
        "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1200&q=80",
        "https://images.unsplash.com/photo-1595675024853-0f3ec9098ac7?w=1200&q=80",
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1200&q=80",
        "https://images.unsplash.com/photo-1523800503107-5bc3ba2a6f81?w=1200&q=80",
        "https://images.unsplash.com/photo-1577375729152-4c8b5fcda381?w=1200&q=80",
        "https://images.unsplash.com/photo-1607705703571-c5a8695f18f6?w=1200&q=80",
        "https://images.unsplash.com/photo-1499673610122-01c7122c5dcb?w=1200&q=80",
        "https://images.unsplash.com/photo-1509966756634-9c23dd6e6815?w=1200&q=80",
        "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=1200&q=80",
        "https://images.unsplash.com/photo-1544256718-3bcf237f3974?w=1200&q=80",
        "https://images.unsplash.com/photo-1581089778245-3ce67677f718?w=1200&q=80",
        "https://images.unsplash.com/photo-1517134191118-9d595e4c8c2b?w=1200&q=80",
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=1200&q=80",
        "https://images.unsplash.com/photo-1550439062-609e1531270e?w=1200&q=80",
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=1200&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1200&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80",
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560732488-6b0df240254a?w=1200&q=80",
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80",
        "https://images.unsplash.com/photo-1555255707-c0790f9d7d7e?w=1200&q=80",
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&q=80",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&q=80",
        "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?w=1200&q=80",
        "https://images.unsplash.com/photo-1617802690992-3bbee52942c7?w=1200&q=80",
        "https://images.unsplash.com/photo-1563986768494-4dee2763ff3f?w=1200&q=80",
        "https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=1200&q=80",
        "https://images.unsplash.com/photo-1573984699409-5ce1c2f30b4e?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",
        "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=1200&q=80",
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=80",
        "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&q=80",
        "https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=1200&q=80",
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&q=80",
        "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=1200&q=80",
        "https://images.unsplash.com/photo-1523206489230-c012c64b2b48?w=1200&q=80",
        "https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=1200&q=80",
        "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=1200&q=80",
        "https://images.unsplash.com/photo-1527192491265-7e15c55b1ed2?w=1200&q=80",
        "https://images.unsplash.com/photo-1553745987-ee20ed8fb4a7?w=1200&q=80",
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&q=80",
        "https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?w=1200&q=80",
        "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=1200&q=80",
        "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&q=80",
        "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=1200&q=80",
        "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=1200&q=80",
        "https://images.unsplash.com/photo-1485199698948-d46a09e771c9?w=1200&q=80",
        "https://images.unsplash.com/photo-1555685812-4b943f1cb0eb?w=1200&q=80",
        "https://images.unsplash.com/photo-1535378620166-273708d44e0c?w=1200&q=80",
        "https://images.unsplash.com/photo-1488229297570-58520851e68c?w=1200&q=80",
        "https://images.unsplash.com/photo-1562279804-8783c89f1e5f?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
    ],
    "finance": [
        # Stock Market & Trading (60+)
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Red blue lights
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",  # Monitor graph
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Stock chart
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",  # Graph display
        "https://images.unsplash.com/photo-1579226905180-636b76d96082?w=1200&q=80",  # MacBook stock
        "https://images.unsplash.com/photo-1612461313144-fc1676a1bf17?w=1200&q=80",  # Phone laptop
        "https://images.unsplash.com/photo-1645226880663-81561dcab0ae?w=1200&q=80",  # Phone chart
        "https://images.unsplash.com/photo-1768055104929-cf2317674a80?w=1200&q=80",  # Trader charts
        "https://images.unsplash.com/photo-1767424196045-030bbde122a4?w=1200&q=80",  # Hand tablet
        "https://images.unsplash.com/photo-1766218329569-53c9270bb305?w=1200&q=80",  # Hands typing
        "https://images.unsplash.com/photo-1762279389020-eeeb69c25813?w=1200&q=80",  # Abstract lines
        "https://images.unsplash.com/photo-1761850167081-473019536383?w=1200&q=80",  # Trader phone
        "https://images.unsplash.com/photo-1612178991541-b48cc8e92a4d?w=1200&q=80",  # Phone screen
        "https://images.unsplash.com/photo-1767424412548-1a1ac7f4b9bc?w=1200&q=80",  # Trading screens
        "https://images.unsplash.com/photo-1649003515353-c58a239cf662?w=1200&q=80",  # Game screenshot
        "https://images.unsplash.com/photo-1648275913341-7973ae7bc9b3?w=1200&q=80",  # Clock numbers
        "https://images.unsplash.com/photo-1665656653092-684fdd316aca?w=1200&q=80",  # Gold trophy
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",  # Chart monitor
        "https://images.unsplash.com/photo-1579226905180-636b76d96082?w=1200&q=80",  # Stock MacBook
        "https://images.unsplash.com/photo-1612461313144-fc1676a1bf17?w=1200&q=80",  # Trading setup
        "https://images.unsplash.com/photo-1576850706430-130a8e6b73c3?w=1200&q=80",  # Stock market
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",  # Trading floor
        "https://images.unsplash.com/photo-1641858784936-e1dea9a3d1e1?w=1200&q=80",  # Market data
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Financial lines
        "https://images.unsplash.com/photo-1576354302919-96748cb8299e?w=1200&q=80",  # Stock chart
        "https://images.unsplash.com/photo-1621261478068-9d5b31768ebe?w=1200&q=80",  # Trading
        
        # Business & Office (50+)
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",  # Skyscraper
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200&q=80",  # Business man
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",  # Laptop meeting
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",  # Analytics
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&q=80",  # Business person
        "https://images.unsplash.com/photo-1497215842964-222b430dc094?w=1200&q=80",  # Office building
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1200&q=80",  # Co-working
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80",  # Team meeting
        "https://images.unsplash.com/photo-1553028826-f4804a6dba3b?w=1200&q=80",  # Business
        "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=1200&q=80",  # Office
        "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1200&q=80",  # Meeting
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80",  # Office space
        "https://images.unsplash.com/photo-1497215842964-222b430dc094?w=1200&q=80",  # Building
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1200&q=80",  # Business
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&q=80",  # Tech team
        "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1200&q=80",  # Meeting
        "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1200&q=80",  # Handshake
        "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=1200&q=80",  # Boardroom
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",  # Laptop business
        "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=1200&q=80",  # Office work
        
        # Money & Currency (40+)
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",  # Money chart
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",  # Gold bars
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",  # Gold
        "https://images.unsplash.com/photo-1580519542036-c47de6196ba5?w=1200&q=80",  # Coins
        "https://images.unsplash.com/photo-1620336655052-b57986f5a26a?w=1200&q=80",  # Money
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Financial
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",  # Gold
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",  # Charts
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",  # Finance
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",  # Money
        "https://images.unsplash.com/photo-1518544801976-3e159e50e5bb?w=1200&q=80",  # Dollar
        "https://images.unsplash.com/photo-1541364983171-a8ba01e95cfc?w=1200&q=80",  # Coins
        "https://images.unsplash.com/photo-1605792657660-596af9009e82?w=1200&q=80",  # Money
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",  # Financial
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Stock
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",  # Gold bars
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",  # Finance gold
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",  # Growth
        "https://images.unsplash.com/photo-1580894894513-541e068a3e2b?w=1200&q=80",  # Money
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",  # Finance
        
        # Cryptocurrency & Blockchain (50+)
        "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=1200&q=80",  # Bitcoin
        "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=1200&q=80",  # Crypto
        "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=1200&q=80",  # Bitcoin gold
        "https://images.unsplash.com/photo-1648364155378-47b5db5fc2c8?w=1200&q=80",  # Blockchain
        "https://images.unsplash.com/photo-1621330396173-e41b1cafd17f?w=1200&q=80",  # Crypto coin
        "https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=1200&q=80",  # Bitcoin
        "https://images.unsplash.com/photo-1620283085439-3960a6c4702b?w=1200&q=80",  # Ethereum
        "https://images.unsplash.com/photo-1640366094205-4a9e8a9a8c6d?w=1200&q=80",  # Crypto
        "https://images.unsplash.com/photo-1623227413711-23ca38c9d5a6?w=1200&q=80",  # Bitcoin coin
        "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=1200&q=80",  # Phone crypto
        "https://images.unsplash.com/photo-1620799139834-6b8f844fbe61?w=1200&q=80",  # Laptop crypto
        "https://images.unsplash.com/photo-1621416894569-0f39f0c6d00c?w=1200&q=80",  # Trading
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200&q=80",  # DeFi
        "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=1200&q=80",  # NFT
        "https://images.unsplash.com/photo-1621753978844-219f8fb2a45c?w=1200&q=80",  # Crypto
        "https://images.unsplash.com/photo-1622470953794-aa9c70b8c042?w=1200&q=80",  # Bitcoin
        "https://images.unsplash.com/photo-1645282303998-4b7c265ceac4?w=1200&q=80",  # Blockchain
        "https://images.unsplash.com/photo-1621261478068-9d5b31768ebe?w=1200&q=80",  # Trading
        "https://images.unsplash.com/photo-1620121478247-ec786b9be2fa?w=1200&q=80",  # Crypto art
        "https://images.unsplash.com/photo-1621252179027-94459d27d3ee?w=1200&q=80",  # Ethereum
        
        # Charts & Data Visualization (50+)
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Dashboard
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",  # Analytics
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Data viz
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",  # Cloud data
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1200&q=80",  # Business chart
        "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=1200&q=80",  # Graph
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Analytics
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",  # Marketing
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",  # Financial
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",  # Money chart
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Stock lines
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",  # Monitor
        "https://images.unsplash.com/photo-1579226905180-636b76d96082?w=1200&q=80",  # MacBook
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Charts
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",  # Growth
        "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=1200&q=80",  # Analytics
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Dashboard
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",  # Data
        "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?w=1200&q=80",  # Storage
        "https://images.unsplash.com/photo-1576354302919-96748cb8299e?w=1200&q=80",  # Chart
        
        # Banking & Financial (30+)
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",  # Bank
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",  # Finance
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",  # Money
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",  # Growth
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",  # Gold
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",  # Finance
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",  # Market
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",  # Banking
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",  # Financial
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",  # Data
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",  # Business
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",  # Meeting
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200&q=80",  # Business
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",  # Building
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&q=80",  # Person
        "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1200&q=80",  # Team
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80",  # Meeting
        "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=1200&q=80",  # Office
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80",  # Workspace
        
        # Economy & Investment (20+)
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",
        "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=1200&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200&q=80",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&q=80",
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80",
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1200&q=80",
        "https://images.unsplash.com/photo-1576354302919-96748cb8299e?w=1200&q=80",
        "https://images.unsplash.com/photo-1641858784936-e1dea9a3d1e1?w=1200&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
        "https://images.unsplash.com/photo-1576850706430-130a8e6b73c3?w=1200&q=80",
        
        # Economy & Investment (50+)
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",
        "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=1200&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200&q=80",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&q=80",
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80",
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1200&q=80",
        "https://images.unsplash.com/photo-1576354302919-96748cb8299e?w=1200&q=80",
        "https://images.unsplash.com/photo-1641858784936-e1dea9a3d1e1?w=1200&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
        "https://images.unsplash.com/photo-1576850706430-130a8e6b73c3?w=1200&q=80",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",
        "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=1200&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200&q=80",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&q=80",
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80",
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1200&q=80",
        "https://images.unsplash.com/photo-1576354302919-96748cb8299e?w=1200&q=80",
        "https://images.unsplash.com/photo-1641858784936-e1dea9a3d1e1?w=1200&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
        "https://images.unsplash.com/photo-1576850706430-130a8e6b73c3?w=1200&q=80",
        "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=1200&q=80",
        "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=1200&q=80",
        "https://images.unsplash.com/photo-1622630998477-20aa7376f3ef?w=1200&q=80",
        "https://images.unsplash.com/photo-1648364155378-47b5db5fc2c8?w=1200&q=80",
        "https://images.unsplash.com/photo-1621330396173-e41b1cafd17f?w=1200&q=80",
        "https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=1200&q=80",
        "https://images.unsplash.com/photo-1620283085439-3960a6c4702b?w=1200&q=80",
        "https://images.unsplash.com/photo-1640366094205-4a9e8a9a8c6d?w=1200&q=80",
        "https://images.unsplash.com/photo-1623227413711-23ca38c9d5a6?w=1200&q=80",
        "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=1200&q=80",
        "https://images.unsplash.com/photo-1620799139834-6b8f844fbe61?w=1200&q=80",
        "https://images.unsplash.com/photo-1621416894569-0f39f0c6d00c?w=1200&q=80",
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200&q=80",
        "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=1200&q=80",
        "https://images.unsplash.com/photo-1621753978844-219f8fb2a45c?w=1200&q=80",
        "https://images.unsplash.com/photo-1622470953794-aa9c70b8c042?w=1200&q=80",
        "https://images.unsplash.com/photo-1645282303998-4b7c265ceac4?w=1200&q=80",
        "https://images.unsplash.com/photo-1621261478068-9d5b31768ebe?w=1200&q=80",
        "https://images.unsplash.com/photo-1620121478247-ec786b9be2fa?w=1200&q=80",
        "https://images.unsplash.com/photo-1621252179027-94459d27d3ee?w=1200&q=80",
        "https://images.unsplash.com/photo-1576850706430-130a8e6b73c3?w=1200&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",
        "https://images.unsplash.com/photo-1580519542036-c47de6196ba5?w=1200&q=80",
        "https://images.unsplash.com/photo-1620336655052-b57986f5a26a?w=1200&q=80",
        "https://images.unsplash.com/photo-1518544801976-3e159e50e5bb?w=1200&q=80",
        "https://images.unsplash.com/photo-1541364983171-a8ba01e95cfc?w=1200&q=80",
        "https://images.unsplash.com/photo-1605792657660-596af9009e82?w=1200&q=80",
        "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=1200&q=80",
        "https://images.unsplash.com/photo-1553028826-f4804a6dba3b?w=1200&q=80",
        "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1200&q=80",
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80",
        "https://images.unsplash.com/photo-1497215842964-222b430dc094?w=1200&q=80",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1200&q=80",
        "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=1200&q=80",
        "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1200&q=80",
        "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1200&q=80",
        "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=1200&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
        "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=1200&q=80",
        "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1200&q=80",
        "https://images.unsplash.com/photo-1565373679580-fc0cb538f49a?w=1200&q=80",
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=1200&q=80",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80",
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?w=1200&q=80",
        "https://images.unsplash.com/photo-1579226905180-636b76d96082?w=1200&q=80",
        "https://images.unsplash.com/photo-1612461313144-fc1676a1bf17?w=1200&q=80",
        "https://images.unsplash.com/photo-1645226880663-81561dcab0ae?w=1200&q=80",
        "https://images.unsplash.com/photo-1768055104929-cf2317674a80?w=1200&q=80",
        "https://images.unsplash.com/photo-1767424196045-030bbde122a4?w=1200&q=80",
        "https://images.unsplash.com/photo-1766218329569-53c9270bb305?w=1200&q=80",
        "https://images.unsplash.com/photo-1762279389020-eeeb69c25813?w=1200&q=80",
        "https://images.unsplash.com/photo-1761850167081-473019536383?w=1200&q=80",
        "https://images.unsplash.com/photo-1612178991541-b48cc8e92a4d?w=1200&q=80",
        "https://images.unsplash.com/photo-1767424412548-1a1ac7f4b9bc?w=1200&q=80",
        "https://images.unsplash.com/photo-1576850706430-130a8e6b73c3?w=1200&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=1200&q=80",
        "https://images.unsplash.com/photo-1641858784936-e1dea9a3d1e1?w=1200&q=80",
        "https://images.unsplash.com/photo-1576354302919-96748cb8299e?w=1200&q=80",
        "https://images.unsplash.com/photo-1621261478068-9d5b31768ebe?w=1200&q=80",
    ],
    "science": [
        "https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=1200&q=80",
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=1200&q=80",
        "https://images.unsplash.com/photo-1559757175-0eb30cd8c063?w=1200&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
        "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=1200&q=80",
    ],
    "health": [
        "https://images.unsplash.com/photo-1559757148-5c350d0d3e56?w=1200&q=80",
        "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?w=1200&q=80",
        "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=1200&q=80",
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1200&q=80",
    ],
    "sports": [
        "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=1200&q=80",
        "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=1200&q=80",
        "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=1200&q=80",
        "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=1200&q=80",
    ],
    "entertainment": [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1200&q=80",
        "https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=1200&q=80",
        "https://images.unsplash.com/photo-1514306191717-452ec28c7814?w=1200&q=80",
        "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1200&q=80",
    ],
    "politics": [
        "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=1200&q=80",
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=1200&q=80",
        "https://images.unsplash.com/photo-1575320181282-9afab399332c?w=1200&q=80",
        "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80",
    ],
    "world": [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
        "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1200&q=80",
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1200&q=80",
        "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1200&q=80",
    ],
    "news": [
        "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=1200&q=80",
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80",
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200&q=80",
        "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1200&q=80",
    ],
    "gaming": [
        "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=1200&q=80",
        "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=1200&q=80",
        "https://images.unsplash.com/photo-1552820728-8b83bb6b2b94?w=1200&q=80",
        "https://images.unsplash.com/photo-1593305841991-05c297ba4575?w=1200&q=80",
    ],
    "other": [
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80",
        "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80",
        "https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=1200&q=80",
        "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=1200&q=80",
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",
    ],
}

# Default fallback images
DEFAULT_FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80",
    "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80",
    "https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=1200&q=80",
    "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=1200&q=80",
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80",
]


def get_random_fallback_image(category: str = None, seed: str = None) -> str:
    """
    Get a random fallback image URL based on category.
    Uses seed for deterministic selection based on article slug.
    """
    import hashlib
    
    # Get images for category or use default
    if category:
        category_lower = category.lower()
        images = CATEGORY_FALLBACK_IMAGES.get(category_lower, CATEGORY_FALLBACK_IMAGES["other"])
    else:
        images = DEFAULT_FALLBACK_IMAGES
    
    # Use seed for deterministic selection (based on article slug)
    if seed:
        hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        index = hash_val % len(images)
        return images[index]
    
    # Random selection
    return random.choice(images)


async def get_fallback_image_info(category: str = None, slug: str = None, source_credit: str = "") -> dict:
    """
    Get a fallback image info dict for WordPress.
    Used when no original image is available.
    """
    image_url = get_random_fallback_image(category, slug)
    return {
        "type": "url",
        "url": image_url,
        "caption": source_credit or "Featured Image",
        "alt": source_credit or "Featured Image",
        "is_fallback": True,
    }


async def get_category_fallback_image(category: str) -> Optional[str]:
    """Get a fallback image URL based on article category."""
    return get_random_fallback_image(category)
