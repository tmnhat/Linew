"""
WordPress REST API client for publishing articles.
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# WordPress App Password format: xxxx-xxxx-xxxx-xxxx (4 groups of 4 chars)
APP_PASSWORD_PATTERN = re.compile(r'^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$')


async def process_article_images(
    article,
    content: str,
    slug: str,
    source_credit: str,
) -> tuple[str, list[dict], Optional[dict]]:
    """
    Process images for an article with 2-tier fallback system.

    TIER 1: Images from crawled_images (original article)
    TIER 2: Fallback category-based images

    NOTE: Unsplash fallback has been DISABLED - articles now use source images only.

    IMPORTANT: Must ensure NO [IMAGE_X] placeholders remain in content.
    If placeholders exist, they MUST be replaced with real images.

    Returns:
        - content: Updated HTML with images inserted (NO placeholders)
        - content_images: List of processed image info
        - featured_image: Featured image info dict
    """
    from app.publisher.image_handler import (
        download_image_with_retry,
        resize_image,
        get_random_fallback_image,
    )

    content_images = []
    featured_image = None
    slug_for_filename = slug or f"article-{hash(content) % 100000}"
    has_placeholders = '[IMAGE_' in content

    logger.info(f"=== IMAGE PROCESSING START ===")
    logger.info(f"Article: {article.original_title[:50] if hasattr(article, 'original_title') else 'Unknown'}")
    logger.info(f"Has placeholders: {has_placeholders}")
    logger.info(f"Has crawled_images: {hasattr(article, 'crawled_images') and bool(article.crawled_images)}")
    if hasattr(article, 'crawled_images') and article.crawled_images:
        logger.info(f"Crawled images count: {len(article.crawled_images)}")
        for i, img in enumerate(article.crawled_images[:3]):
            img_url = img.get("url") if isinstance(img, dict) else img
            logger.info(f"  Crawled image {i+1}: {img_url[:80] if img_url else 'None'}")

    # === TIER 1: Try crawled images first ===
    if hasattr(article, 'crawled_images') and article.crawled_images:
        logger.info(f"Processing {len(article.crawled_images)} crawled images...")

        for i, img_data in enumerate(article.crawled_images[:10]):  # Max 10 images
            img_url = img_data.get("url") if isinstance(img_data, dict) else img_data
            if not img_url:
                logger.warning(f"  Image {i+1}: No URL, skipping")
                continue

            img_alt = img_data.get("alt", source_credit) if isinstance(img_data, dict) else source_credit

            logger.info(f"  Downloading image {i+1}: {img_url[:80]}...")
            # Download with retry (handles hotlink protection)
            image_bytes = await download_image_with_retry(img_url, max_retries=3)
            if not image_bytes:
                logger.warning(f"  Image {i+1}: Download failed (hotlink blocked or timeout)")
                continue

            # Resize if needed
            image_bytes = resize_image(image_bytes)

            # Upload to WordPress
            try:
                from app.publisher.wordpress import get_wordpress_client
                client = get_wordpress_client()
                filename = f"{slug_for_filename[:40]}-{i+1}-{abs(hash(img_url)) % 10000}.jpg"

                logger.info(f"  Uploading image {i+1} to WordPress...")
                result = client.upload_media(
                    image_bytes=image_bytes,
                    filename=filename,
                    mime_type="image/jpeg",
                    alt_text=img_alt,
                    caption=img_alt,
                )

                if result:
                    img_info = {
                        "original_url": img_url,
                        "url": result.get("url"),
                        "type": "internal",
                        "alt": img_alt,
                        "media_id": result.get("id"),
                    }
                    content_images.append(img_info)
                    logger.info(f"  Image {i+1}: Uploaded successfully to {result.get('url')[:60]}")
                else:
                    # Fallback: try to use the original URL directly if upload failed
                    logger.warning(f"  Image {i+1}: Upload failed, using original URL directly")
                    content_images.append({
                        "original_url": img_url,
                        "url": img_url,
                        "type": "external",
                        "alt": img_alt,
                    })

            except Exception as e:
                logger.warning(f"  Image {i+1}: Error uploading: {e}")
                # Still add as external fallback
                content_images.append({
                    "original_url": img_url,
                    "url": img_url,
                    "type": "external",
                    "alt": img_alt,
                })
                continue

    logger.info(f"After Tier 1: {len(content_images)} images available")

    # === TIER 2: Unsplash DISABLED ===
    # Articles now use source images only from crawled content
    # Keeping code here for future reference but not executing
    # if len(content_images) < 3:
    #     MAX_UNSPLASH_IMAGES = 1
    #     ... (Unsplash logic removed)

    logger.info(f"After Tier 2: {len(content_images)} images available (Unsplash disabled)")

    # === REPLACE ALL PLACEHOLDERS WITH IMAGES ===
    # Use regex to find ALL placeholders first
    placeholder_matches = list(re.finditer(r'\[IMAGE_(\d+)\]', content))

    # === FIX 1: Track original images in content BEFORE any replacements ===
    # This helps us know if we should add fallback images or not
    original_content_had_images = '<img' in content

    if placeholder_matches:
        logger.info(f"Found {len(placeholder_matches)} image placeholders in content")
        logger.info(f"Original content had images: {original_content_had_images}")

        # === FIX 1: Replace placeholders in REVERSE order ===
        # If we replace from top to bottom, positions become stale after each replacement
        # By replacing from bottom to top, positions of earlier placeholders don't change
        placeholder_matches.reverse()

        # === CRITICAL FIX: Prevent duplicate images ===
        # Track which images have been used to prevent duplication
        used_image_urls = set()
        images_to_use = []
        fallback_images_used = 0

        if content_images:
            # Skip the first image if it's being used as featured
            if len(content_images) > 1:
                images_to_use = content_images[1:]  # Skip first (used as featured)
                logger.info(f"Skipping first image for content (used as featured): {content_images[0].get('url')[:60]}")
                logger.info(f"Using {len(images_to_use)} images for content")
            else:
                # Only one image - it's the featured, don't use in content
                logger.warning("Only one image available - using as featured only, not in content")
                images_to_use = []

        # Replace each placeholder
        for match in placeholder_matches:
            placeholder_idx = int(match.group(1)) - 1  # 0-indexed
            placeholder_text = match.group(0)
            position = match.start()

            # Determine which image to use
            if images_to_use:
                # Use existing image - CRITICAL: don't reuse images
                # Find the next unused image
                img_found = False
                for i, img_info in enumerate(images_to_use):
                    img_url = img_info.get("url", "")
                    # Skip if this URL has already been used in content
                    if img_url and img_url not in used_image_urls:
                        used_image_urls.add(img_url)
                        img_found = True
                        break

                if not img_found:
                    # === FIX 2: Only add fallback if content truly has NO images ===
                    # If original content already had images or we've already added some,
                    # just remove the placeholder without adding more images
                    if original_content_had_images or used_image_urls:
                        logger.warning("Content already has images, removing placeholder without adding fallback")
                        content = content[:position] + content[position + len(placeholder_text):]
                        continue
                    # ================================================================
                    
                    # Only use fallback when there's truly no image in content
                    logger.warning("All content images used, downloading fallback for remaining placeholders")
                    fallback_url = get_random_fallback_image(
                        category=getattr(article, 'category', None),
                        seed=f"{slug}-{fallback_images_used}"
                    )
                    fallback_images_used += 1

                    try:
                        from app.publisher.wordpress import get_wordpress_client
                        client = get_wordpress_client()

                        image_bytes = await download_image_with_retry(fallback_url, max_retries=3)
                        if image_bytes:
                            image_bytes = resize_image(image_bytes)
                            filename = f"{slug_for_filename[:40]}-fallback-{fallback_images_used}.jpg"

                            result = client.upload_media(
                                image_bytes=image_bytes,
                                filename=filename,
                                mime_type="image/jpeg",
                                alt_text="Illustration",
                                caption="Illustration",
                            )

                            if result:
                                img_url = result.get("url")
                                img_info = {
                                    "url": img_url,
                                    "type": "fallback",
                                    "alt": "Illustration",
                                    "media_id": result.get("id"),
                                }
                                used_image_urls.add(img_url)

                                caption_text = "Illustration"
                                img_html = f'<figure class="wp-block-image size-large"><img src="{img_url}" alt="Illustration" loading="lazy" /><figcaption class="wp-element-caption">{caption_text}</figcaption></figure>'
                                content = content[:position] + img_html + content[position + len(placeholder_text):]
                                logger.info(f"Replaced {placeholder_text} with fallback image")
                                continue
                            else:
                                img_url = fallback_url
                        else:
                            img_url = fallback_url

                        # Use fallback URL directly
                        img_html = f'<figure class="wp-block-image size-large"><img src="{img_url}" alt="Illustration" loading="lazy" /><figcaption class="wp-element-caption">Illustration</figcaption></figure>'
                        content = content[:position] + img_html + content[position + len(placeholder_text):]
                        logger.warning(f"Used fallback URL directly for {placeholder_text}")
                        continue

                    except Exception as e:
                        logger.error(f"Error downloading fallback image: {e}")
                        content = content[:position] + content[position + len(placeholder_text):]
                        continue

                # Now img_info is set to an unused image
                img_url = img_info.get("url", "")
                img_alt = img_info.get("alt", source_credit) or source_credit
                credit = img_info.get("credit", "")
                credit_url = img_info.get("credit_url", "")

                caption_text = img_alt
                if credit and credit_url:
                    caption_text = f'{img_alt} <a href="{credit_url}" target="_blank">{credit}</a>'
                elif credit:
                    caption_text = f'{img_alt} - {credit}'

                img_html = f'<figure class="wp-block-image size-large"><img src="{img_url}" alt="{img_alt}" loading="lazy" /><figcaption class="wp-element-caption">{caption_text}</figcaption></figure>'
                content = content[:position] + img_html + content[position + len(placeholder_text):]
                logger.info(f"Replaced {placeholder_text} with image at position {position} (used: {len(used_image_urls)})")
            else:
                # === FIX 2: Only add fallback if content truly has NO images ===
                # If original content already had images, OR we've already added fallbacks,
                # just remove the placeholder without adding more images
                if original_content_had_images or fallback_images_used > 0:
                    logger.warning("Content already has images or fallbacks added, removing placeholder without adding more fallback")
                    content = content[:position] + content[position + len(placeholder_text):]
                    continue
                # ================================================================
                
                # Only use fallback when there's truly no image in content
                logger.warning(f"No images available for {placeholder_text}, downloading fallback")

                fallback_url = get_random_fallback_image(
                    category=getattr(article, 'category', None),
                    seed=f"{slug}-{fallback_images_used}"
                )
                fallback_images_used += 1

                try:
                    from app.publisher.wordpress import get_wordpress_client
                    client = get_wordpress_client()

                    image_bytes = await download_image_with_retry(fallback_url, max_retries=3)
                    if image_bytes:
                        image_bytes = resize_image(image_bytes)
                        filename = f"{slug_for_filename[:40]}-fallback-{fallback_images_used}.jpg"

                        result = client.upload_media(
                            image_bytes=image_bytes,
                            filename=filename,
                            mime_type="image/jpeg",
                            alt_text="Illustration",
                            caption="Illustration",
                        )

                        if result:
                            img_url = result.get("url")
                            caption_text = "Illustration"
                            img_html = f'<figure class="wp-block-image size-large"><img src="{img_url}" alt="Illustration" loading="lazy" /><figcaption class="wp-element-caption">{caption_text}</figcaption></figure>'
                            content = content[:position] + img_html + content[position + len(placeholder_text):]
                            content_images.append({
                                "url": img_url,
                                "type": "fallback",
                                "alt": "Illustration",
                                "media_id": result.get("id"),
                            })
                            logger.info(f"Replaced {placeholder_text} with fallback image")
                        else:
                            # Use fallback URL directly
                            img_html = f'<figure class="wp-block-image size-large"><img src="{fallback_url}" alt="Illustration" loading="lazy" /><figcaption class="wp-element-caption">Illustration</figcaption></figure>'
                            content = content[:position] + img_html + content[position + len(placeholder_text):]
                            logger.warning(f"Used fallback URL directly for {placeholder_text}")
                    else:
                        # Remove placeholder if download fails
                        content = content[:position] + content[position + len(placeholder_text):]
                        logger.warning(f"Removed {placeholder_text} - download failed")

                except Exception as e:
                    logger.error(f"Error replacing {placeholder_text}: {e}")
                    content = content[:position] + content[position + len(placeholder_text):]

        # === FINAL CHECK: Remove ANY remaining placeholders ===
        final_placeholders = re.findall(r'\[IMAGE_\d+\]', content)
        if final_placeholders:
            logger.error(f"CRITICAL: {len(final_placeholders)} placeholders still remain! Force removing...")
            content = re.sub(r'\[IMAGE_\d+\]', '', content)
        else:
            logger.info("All placeholders replaced successfully")

    # === If no placeholders but no images either, distribute images evenly ===
    elif not content_images:
        logger.info("No placeholders and no images, will check for fallback...")
        # This case is handled below in Tier 3

    elif content_images and '[IMAGE_' not in content:
        # === FIX 2: Only distribute images if content has NO images yet ===
        # If content already has <img> tags from AI writing, don't add more
        if '<img' in content:
            logger.info("Content already has images (from AI writing), skipping image distribution")
        else:
            logger.info("No placeholders found, distributing images evenly...")
            
            # === CRITICAL FIX: Skip first image (used as featured) ===
            # The first crawled image is used as featured image by WordPress
            # We should only use images[1:] for content to prevent duplication
            
            images_for_content = content_images[1:] if len(content_images) > 1 else []
            if content_images:
                logger.info(f"Skipping first image for content (used as featured): {content_images[0].get('url')[:60]}")
                logger.info(f"Using {len(images_for_content)} images for content")
            
            if not images_for_content:
                logger.info("No images left for content after skipping featured, will add fallback if needed")
                # Fall through to the fallback section below

            # Limit total images to avoid excessive stock images
            MAX_TOTAL_IMAGES = 3
            
            all_img_html = []
            for img_info in images_for_content[:MAX_TOTAL_IMAGES]:
                img_url = img_info.get("url", "")
                img_alt = img_info.get("alt", source_credit) or source_credit
                credit = img_info.get("credit", "")

                if img_url:
                    caption_text = img_alt
                    if credit:
                        caption_text = f'{img_alt} - {credit}'

                    img_html = f'<figure class="wp-block-image size-large"><img src="{img_url}" alt="{img_alt}" loading="lazy" /><figcaption class="wp-element-caption">{caption_text}</figcaption></figure>'
                    all_img_html.append(img_html)

            if all_img_html:
                # Split content and insert images at strategic points
                parts = content.split('</p>')
                num_parts = len(parts)
                num_images = len(all_img_html)

                if num_parts >= 2:
                    # Calculate insertion points
                    step = num_parts / (num_images + 1)
                    insert_points = []
                    for i in range(num_images):
                        idx = int((i + 1) * step)
                        idx = min(idx, num_parts - 1)
                        insert_points.append(idx)

                    # Insert images
                    insert_points.sort(reverse=True)
                    for i, idx in enumerate(insert_points):
                        if idx < len(parts) and i < len(all_img_html):
                            parts.insert(idx, '\n' + all_img_html[i] + '\n')

                    content = '</p>'.join(parts)
                else:
                    # Append images at the end
                    content = content + '\n\n' + '\n\n'.join(all_img_html)

    # === ENSURE AT LEAST ONE IMAGE IN CONTENT ===
    # If content has no images, add a fallback image at the start
    # NOTE: We do NOT add featured image here to avoid duplication
    # The featured image will be set via WordPress's featured_media field
    if '<img' not in content and not content_images:
        logger.warning("Content has no images, adding fallback...")
        
        fallback_url = get_random_fallback_image(
            category=getattr(article, 'category', None),
            seed=slug
        )
        
        try:
            from app.publisher.wordpress import get_wordpress_client
            client = get_wordpress_client()
            
            image_bytes = await download_image_with_retry(fallback_url, max_retries=3)
            if image_bytes:
                image_bytes = resize_image(image_bytes)
                filename = f"{slug_for_filename[:40]}-fallback-content.jpg"
                
                result = client.upload_media(
                    image_bytes=image_bytes,
                    filename=filename,
                    mime_type="image/jpeg",
                    alt_text="Illustration",
                    caption="Illustration",
                )
                
                if result:
                    # This is a content-only image, NOT a featured image
                    content_images.append({
                        "url": result.get("url"),
                        "type": "fallback_content",
                        "alt": "Illustration",
                        "media_id": result.get("id"),
                        "is_content_only": True,  # Flag to prevent using as featured
                    })
                    img_html = f'<figure class="wp-block-image size-large"><img src="{result.get("url")}" alt="Illustration" loading="lazy" /><figcaption class="wp-element-caption">Illustration</figcaption></figure>'
                    content = img_html + '\n\n' + content
                    logger.info("Added fallback image to content (content-only, not featured)")
        except Exception as e:
            logger.warning(f"Failed to add fallback image: {e}")

    # === Set featured image ===
    # Priority: content_images first, then fallback options
    if not featured_image:
        if content_images:
            # Find first image that is NOT marked as content_only
            for img in content_images:
                if not img.get("is_content_only"):
                    featured_image = img.copy()
                    featured_image["is_featured"] = True
                    logger.info(f"Featured image set from content_images: {featured_image.get('url')}")
                    break
            else:
                # All images are content-only, use the first one anyway
                featured_image = content_images[0].copy()
                featured_image["is_featured"] = True
                logger.warning("All images are content-only, using first as featured")
        
        # === ADDITIONAL FALLBACK: Check if content has <img> tags ===
        # If content has images but they're not in content_images, we need to extract them
        if not featured_image and '<img' in content:
            logger.info("Content has <img> tags but no content_images, searching for featured...")
            # Try to find first image URL from content
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
            if img_match:
                img_url = img_match.group(1)
                featured_image = {
                    "url": img_url,
                    "type": "inline",
                    "alt": "Featured Image",
                    "is_featured": True,
                }
                logger.info(f"Featured image extracted from content: {img_url[:60]}")

    # === FINAL VALIDATION: Ensure NO placeholders remain ===
    final_placeholders = re.findall(r'\[IMAGE_\d+\]', content)
    if final_placeholders:
        logger.error(f"CRITICAL: {len(final_placeholders)} placeholders still in content! Forcing cleanup...")
        content = re.sub(r'\[IMAGE_\d+\]', '', content)

    # === FINAL LOGGING ===
    logger.info(f"=== IMAGE PROCESSING COMPLETE ===")
    logger.info(f"Content has <img>: {'<img' in content}")
    placeholder_count = len(re.findall(r'\[IMAGE_\d+\]', content))
    logger.info(f"Final placeholders: {placeholder_count}")
    logger.info(f"Total content_images: {len(content_images)}")
    logger.info(f"Featured image: {featured_image.get('url')[:60] if featured_image and featured_image.get('url') else 'None'}")

    return content, content_images, featured_image


def validate_wp_password(password: str) -> tuple[bool, str]:
    """
    Validate WordPress password format.
    Returns (is_valid, message).
    
    WordPress App Passwords are in format: xxxx-xxxx-xxxx-xxxx
    Regular passwords can be any string but require Basic Auth plugin.
    """
    if not password or len(password) < 8:
        return False, "Password too short"
    
    if APP_PASSWORD_PATTERN.match(password):
        return True, "Valid App Password format"
    
    # Check if it looks like it might be a regular password
    if len(password) >= 12:
        return True, "Regular password (Basic Auth plugin required)"
    
    return True, "Password set (may need Basic Auth plugin)"


class WordPressClient:
    """WordPress REST API client with retry logic."""

    def __init__(self):
        self.site_url = settings.wp_url.rstrip("/")
        self.username = settings.wp_username
        self.app_password = settings.wp_app_password
        self.api_url = f"{self.site_url}/wp-json/wp/v2"

        # Create session with retry strategy
        self.session = requests.Session()

        # Use Basic Auth (username + app password OR regular password)
        # For WordPress, we can use username:password or username:app_password
        self.session.auth = HTTPBasicAuth(self.username, self.app_password)

        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Linew/1.0",
        })

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def test_connection(self) -> dict:
        """Test WordPress connection and validate credentials."""
        # Validate password format
        is_valid, message = validate_wp_password(self.app_password)
        
        try:
            response = self.session.get(f"{self.api_url}/users/me", timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "connected": True,
                    "user": {
                        "id": user_data.get("id"),
                        "name": user_data.get("name"),
                        "email": user_data.get("email"),
                    },
                    "password_valid": True,
                    "password_info": message,
                }
            elif response.status_code == 401:
                return {
                    "connected": False,
                    "error": "Authentication failed - check username/password",
                    "password_format": message,
                    "password_hint": "Use App Password (format: xxxx-xxxx-xxxx-xxxx) from WordPress Users > Application Passwords",
                }
            elif response.status_code == 403:
                return {
                    "connected": False,
                    "error": "Forbidden - REST API may be disabled",
                    "hint": "Enable REST API in WordPress Settings > Permalinks",
                }
            else:
                return {"connected": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"connected": False, "error": str(e), "password_format": message}

    def upload_media(
        self,
        image_bytes: bytes,
        filename: str,
        mime_type: str = "image/jpeg",
        alt_text: str = "",
        caption: str = "",
        as_featured: bool = False,
    ) -> Optional[dict]:
        """Upload media to WordPress."""
        try:
            files = {
                "file": (filename, image_bytes, mime_type),
            }
            data = {}
            if alt_text:
                data["alt_text"] = alt_text
            if caption:
                data["caption"] = caption
            if as_featured:
                data["featured_media"] = True

            # For file uploads, we need to create a new session without Content-Type header
            # because multipart/form-data needs its own Content-Type with boundary
            upload_session = requests.Session()
            upload_session.auth = self.session.auth
            upload_session.headers.update({
                "User-Agent": "Linew/1.0",
            })
            
            response = upload_session.post(
                f"{self.api_url}/media",
                files=files,
                data=data if data else None,
                timeout=60,
            )

            if response.status_code in (200, 201):
                result = response.json()
                logger.info(f"Uploaded media: {result.get('source_url')}")
                return {
                    "id": result.get("id"),
                    "url": result.get("source_url"),
                    "alt_text": result.get("alt_text"),
                }
            else:
                logger.error(f"Media upload failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Media upload error: {e}")
            return None

    def map_category(self, category_name: str) -> Optional[int]:
        """Map category name to WordPress category ID."""
        try:
            # Search for existing category
            response = self.session.get(
                f"{self.api_url}/categories",
                params={"search": category_name, "per_page": 10},
                timeout=10,
            )

            if response.status_code == 200:
                categories = response.json()
                for cat in categories:
                    if cat["name"].lower() == category_name.lower():
                        return cat["id"]

            # Create new category
            response = self.session.post(
                f"{self.api_url}/categories",
                json={"name": category_name},
                timeout=10,
            )

            if response.status_code in (200, 201):
                result = response.json()
                logger.info(f"Created category: {category_name} (ID: {result['id']})")
                return result["id"]
            else:
                logger.error(f"Category creation failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Category mapping error: {e}")
            return None

    def check_slug_exists(self, slug: str) -> Optional[dict]:
        """
        Check if a slug already exists in WordPress.
        Returns the existing post info if found, None otherwise.
        """
        try:
            # Search for posts with this slug using the slug search endpoint
            response = self.session.get(
                f"{self.api_url}/posts",
                params={"slug": slug, "status": "any", "per_page": 1},
                timeout=10,
            )

            if response.status_code == 200:
                posts = response.json()
                if posts:
                    existing_post = posts[0]
                    logger.warning(f"Slug '{slug}' already exists: {existing_post.get('link')}")
                    return {
                        "exists": True,
                        "post_id": existing_post.get("id"),
                        "post_url": existing_post.get("link"),
                        "post_title": existing_post.get("title", {}).get("rendered", ""),
                    }
                return {"exists": False}

            logger.error(f"Slug check failed: {response.status_code}")
            return {"exists": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Slug check error: {e}")
            return {"exists": False, "error": str(e)}

    def check_duplicate_by_meta(self, meta_key: str, meta_value: str) -> Optional[dict]:
        """
        Check if a post with specific meta field value already exists.
        This is used to detect duplicates based on title_hash stored in post meta.

        Uses custom WordPress REST API endpoint (linew/v1/posts-by-meta) which
        bypasses WordPress meta_query issues with JSON meta values by using direct SQL.

        Returns dict with exists=True and post info if found, or exists=False if not found.
        """
        try:
            # Use custom endpoint that bypasses WordPress meta_query issues
            response = self.session.get(
                f"{self.site_url}/wp-json/linew/v1/posts-by-meta",
                params={
                    "meta_key": meta_key,
                    "meta_value": meta_value,
                    "per_page": 1,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("exists") and data.get("posts"):
                    post = data["posts"][0]
                    logger.warning(
                        f"Post with {meta_key}='{meta_value[:16]}...' already exists: "
                        f"ID={post.get('id')}, Title='{post.get('title', '')[:60]}'"
                    )
                    return {
                        "exists": True,
                        "post_id": post.get("id"),
                        "post_url": post.get("url"),
                        "post_title": post.get("title", ""),
                    }
                return {"exists": False}

            logger.warning(f"posts-by-meta endpoint returned {response.status_code}, falling back")
            return {"exists": False}

        except Exception as e:
            logger.error(f"Meta duplicate check error: {e}")
            return {"exists": False}

    def create_tags(self, tag_names: list[str]) -> list[int]:
        """Create or get WordPress tag IDs."""
        logger.info(f"create_tags called with: {tag_names} (type: {type(tag_names)})")
        tag_ids = []
        
        # Ensure tag_names is a list
        if not tag_names:
            logger.warning("create_tags: tag_names is empty")
            return tag_ids
            
        if not isinstance(tag_names, list):
            logger.warning(f"create_tags: tag_names is not a list, it's {type(tag_names)}")
            # Try to convert
            if isinstance(tag_names, str):
                tag_names = [t.strip() for t in tag_names.split(",") if t.strip()]
            else:
                return tag_ids
        
        for tag_name in tag_names:
            if not tag_name or not isinstance(tag_name, str):
                logger.warning(f"Skipping invalid tag: {tag_name}")
                continue
                
            try:
                # Search for existing tag
                response = self.session.get(
                    f"{self.api_url}/tags",
                    params={"search": tag_name, "per_page": 10},
                    timeout=10,
                )

                if response.status_code == 200:
                    tags = response.json()
                    tag_id = None
                    for tag in tags:
                        if tag["name"].lower() == tag_name.lower():
                            tag_id = tag["id"]
                            logger.info(f"Found existing tag: {tag_name} (id: {tag_id})")
                            break

                    if not tag_id:
                        # Create new tag
                        response = self.session.post(
                            f"{self.api_url}/tags",
                            json={"name": tag_name},
                            timeout=10,
                        )
                        if response.status_code in (200, 201):
                            tag_id = response.json()["id"]
                            logger.info(f"Created new tag: {tag_name} (id: {tag_id})")

                    if tag_id:
                        tag_ids.append(tag_id)

            except Exception as e:
                logger.warning(f"Tag creation error for {tag_name}: {e}")
                continue
        
        logger.info(f"create_tags returning: {tag_ids}")
        return tag_ids

    def create_post(self, article) -> dict:
        """
        Create WordPress post from article.
        
        Enhanced with retry logic for transient errors (429, 500, 502, 503, 504).
        """
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # === FIX: Check for duplicate using BOTH slug AND title_hash ===
                
                # Check 1: Slug exists (original check)
                if article.slug:
                    slug_check = self.check_slug_exists(article.slug)
                    if slug_check and slug_check.get("exists"):
                        existing = slug_check
                        logger.warning(
                            f"DUPLICATE (slug): Post with slug '{article.slug}' already exists. "
                            f"Returning existing post: {existing.get('post_url')}"
                        )
                        return {
                            "duplicate": True,
                            "wp_post_id": existing.get("post_id"),
                            "wp_url": existing.get("post_url"),
                            "message": "Post with this slug already exists",
                        }

                # Check 2: title_hash exists (NEW - prevents same news in different languages)
                if hasattr(article, 'title_hash') and article.title_hash:
                    meta_check = self.check_duplicate_by_meta("linew_title_hash", article.title_hash)
                    if meta_check and meta_check.get("exists"):
                        existing = meta_check
                        logger.warning(
                            f"DUPLICATE (title_hash): Post with title_hash '{article.title_hash[:16]}...' already exists. "
                            f"Title: '{existing.get('post_title', '')[:60]}'. "
                            f"URL: {existing.get('post_url')}"
                        )
                        return {
                            "duplicate": True,
                            "wp_post_id": existing.get("post_id"),
                            "wp_url": existing.get("post_url"),
                            "message": "Post with same source title already exists (different language)",
                        }

                # Prepare content - DO NOT add featured image here to avoid duplication
                # Featured image will be displayed by WordPress via featured_media field
                content = article.body_html or ""

                # Build post data
                post_data = {
                    "title": article.meta_title or article.original_title,
                    "content": content,
                    "status": "publish",
                    "slug": article.slug,
                }

                # Add featured_media as a proper field
                if article.featured_image_wp_id:
                    post_data["featured_media"] = article.featured_image_wp_id

                # Add meta description and title_hash for duplicate detection
                meta_fields = {}
                if article.meta_description:
                    meta_fields["_yoast_meta_description"] = article.meta_description
                    meta_fields["_meta_description"] = article.meta_description
                
                # Store title_hash for duplicate detection across languages
                if hasattr(article, 'title_hash') and article.title_hash:
                    meta_fields["linew_title_hash"] = article.title_hash
                
                if meta_fields:
                    post_data["meta"] = meta_fields

                # Add category
                if article.category:
                    category_id = self.map_category(article.category)
                    if category_id:
                        post_data["categories"] = [category_id]

                # CRITICAL: Log article.tags BEFORE any processing
                logger.info(f"=== CREATE_POST TAGS DEBUG ===")
                logger.info(f"article.tags = {article.tags}")
                logger.info(f"article.tags type = {type(article.tags)}")
                logger.info(f"bool(article.tags) = {bool(article.tags)}")
                logger.info(f"len(article.tags) if list = {len(article.tags) if isinstance(article.tags, list) else 'N/A'}")
                logger.info(f"=== END TAGS DEBUG ===")
                
                # Add tags
                # Ensure tags is a list - handle JSON string or other formats
                article_tags = article.tags
                if article_tags:
                    # Handle JSON string (if tags was stored as JSON string)
                    if isinstance(article_tags, str):
                        try:
                            import json
                            article_tags = json.loads(article_tags)
                        except (json.JSONDecodeError, TypeError):
                            # If it's a comma-separated string, split it
                            article_tags = [t.strip() for t in article_tags.split(",") if t.strip()]
                    
                    # Ensure it's a list
                    if isinstance(article_tags, list) and article_tags:
                        logger.info(f"Creating tags for post: {article_tags}")
                        tag_ids = self.create_tags(article_tags)
                        if tag_ids:
                            post_data["tags"] = tag_ids
                            logger.info(f"Tags added successfully: {tag_ids}")
                        else:
                            logger.warning(f"create_tags returned empty list for: {article_tags}")
                    else:
                        logger.warning(f"article.tags is empty or invalid: {article_tags} (type: {type(article_tags)})")

                # Create post
                # Add _embed parameter to include tags in response
                logger.info(f"post_data['tags'] = {post_data.get('tags', 'NOT SET')}")
                response = self.session.post(
                    f"{self.api_url}/posts?_embed",
                    json=post_data,
                    timeout=30,
                )
                logger.info(f"post_data sent to WP: title={post_data.get('title', 'N/A')[:50]}, categories={post_data.get('categories')}, tags={post_data.get('tags')}")

                if response.status_code in (200, 201):
                    result = response.json()
                    logger.info(f"Created post: {result.get('link')}")
                    logger.info(f"WP response tags: {result.get('tags', 'N/A')}")
                    logger.info(f"WP response _embedded: {result.get('_embedded', {}).get('term:post_tag', 'N/A')}")
                    return {
                        "wp_post_id": result.get("id"),
                        "wp_url": result.get("link"),
                        "wp_response": result,
                    }
                
                # Handle transient errors with retry
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"WordPress transient error {response.status_code} for {article.slug}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Post creation failed after {max_retries} attempts: {response.status_code}")
                        return {
                            "error": f"HTTP {response.status_code}",
                            "response": response.text,
                        }
                
                # Non-retryable error
                logger.error(f"Post creation failed: {response.status_code} - {response.text}")
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text,
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Post creation error: {e}, retrying in {delay}s (attempt {attempt + 1})")
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"Post creation failed after {max_retries} attempts: {e}")
                    return {"error": str(e)}
        
        return {"error": "Unknown error after retries"}

    def update_post(self, wp_post_id: int, data: dict) -> Optional[dict]:
        """Update an existing WordPress post (uses PATCH for partial updates)."""
        try:
            # WordPress uses PATCH for partial updates
            response = self.session.post(
                f"{self.api_url}/posts/{wp_post_id}",
                json=data,
                timeout=30,
            )

            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "wp_post_id": result.get("id"),
                    "wp_url": result.get("link"),
                    "wp_response": result,
                }
            else:
                logger.error(f"Post update failed: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Post update error: {e}")
            return {"error": str(e)}

    def unpublish_post(self, wp_post_id: int) -> Optional[dict]:
        """Unpublish a post (set to draft)."""
        return self.update_post(wp_post_id, {"status": "draft"})

    def set_external_featured_image(self, wp_post_id: int, image_url: str) -> Optional[dict]:
        """Set external URL as featured image without uploading."""
        try:
            response = self.session.post(
                f"{self.site_url}/wp-json/linew/v1/set-featured-image",
                json={
                    "post_id": wp_post_id,
                    "image_url": image_url,
                },
                timeout=30,
            )

            if response.status_code in (200, 201):
                result = response.json()
                logger.info(f"Set external featured image for post {wp_post_id}: {image_url[:60]}...")
                return result
            else:
                logger.warning(f"Failed to set external featured image: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.warning(f"Error setting external featured image: {e}")
            return None


# Singleton instance
_wp_client: Optional[WordPressClient] = None


def get_wordpress_client() -> WordPressClient:
    """Get or create WordPress client."""
    global _wp_client
    if _wp_client is None:
        _wp_client = WordPressClient()
    return _wp_client


async def publish_article_to_wordpress(session, article, source_name: str = None) -> dict:
    """
    Publish article to WordPress with comprehensive image handling.
    
    3-Tier Image System:
    - Tier 1: Images from crawled_images (original article content)
    - Tier 2: Images from Unsplash (AI-generated keywords fallback)
    - Tier 3: Category-based fallback images
    
    Flow:
    1. Get article body_html (may have [IMAGE_1] placeholders)
    2. Process images through 3-tier system
    3. Replace placeholders or distribute images evenly
    4. Set featured image
    5. Create WordPress post
    6. Set featured image via REST API
    """
    client = get_wordpress_client()
    logger.info(f"Publishing article: {article.original_title[:50]}...")
    logger.info(f"Article tags for publishing: {article.tags} (type: {type(article.tags)})")
    
    # Import fallback image function
    from app.publisher.image_handler import get_random_fallback_image
    
    # Get source credit
    if source_name:
        source_credit = f"Ảnh: {source_name}"
    elif hasattr(article, 'source') and article.source:
        source_credit = f"Ảnh: {article.source.name}"
    else:
        source_credit = "Nguồn"

    # Get slug for filenames
    slug = article.slug or f"article-{hash(article.original_title) % 100000}"

    # Get body_html
    content = article.body_html or ""

    # Log initial state
    logger.info(f"Original image URL: {article.original_image_url}")
    logger.info(f"Crawled images: {len(article.crawled_images) if article.crawled_images else 0}")
    logger.info(f"Image keywords: {article.image_keywords if hasattr(article, 'image_keywords') else []}")
    logger.info(f"Has placeholders: {'[IMAGE_' in content}")

    # === PROCESS IMAGES WITH 3-TIER SYSTEM ===
    content, content_images, featured_image = await process_article_images(
        article=article,
        content=content,
        slug=slug,
        source_credit=source_credit,
    )

    # === CRITICAL: Featured image must ALWAYS be set ===
    # Strategy: Upload featured image FIRST, then include media_id in create_post
    featured_image_url = None
    featured_image_wp_id = None
    
    # === STEP 1: Determine the featured image URL (all fallbacks) ===
    # Fallback 1: Use featured_image from process_article_images (already uploaded to WP)
    if featured_image:
        featured_image_url = featured_image.get("url")
        if featured_image.get("type") == "internal" and featured_image.get("media_id"):
            featured_image_wp_id = featured_image.get("media_id")
        logger.info(f"Featured image from process: {featured_image_url}")
    
    # Fallback 2: Try crawled_images original URLs
    if not featured_image_url and hasattr(article, 'crawled_images') and article.crawled_images:
        for img_data in article.crawled_images[:3]:
            img_url = img_data.get("url") if isinstance(img_data, dict) else img_data
            if img_url:
                featured_image_url = img_url
                logger.info(f"Using crawled image as featured: {featured_image_url}")
                break
    
    # Fallback 3: Try original_image_url from RSS
    if not featured_image_url and article.original_image_url:
        featured_image_url = article.original_image_url
        logger.info(f"Using original_image_url as featured: {featured_image_url}")
    
    # Fallback 4: Extract image from content HTML
    if not featured_image_url and '<img' in content:
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if img_match:
            inline_img_url = img_match.group(1)
            featured_image_url = inline_img_url
            logger.info(f"Featured image extracted from content: {inline_img_url[:60]}")
    
    # Fallback 5: Use category-based fallback image (ALWAYS as last resort)
    if not featured_image_url:
        from app.publisher.image_handler import get_random_fallback_image
        featured_image_url = get_random_fallback_image(
            category=getattr(article, 'category', None),
            seed=f"{slug}-featured"
        )
        logger.warning(f"No source image available, using fallback: {featured_image_url}")
    
    # Emergency fallback - MUST have a URL
    if not featured_image_url:
        logger.error("CRITICAL: featured_image_url is still None!")
        from app.publisher.image_handler import get_random_fallback_image
        featured_image_url = get_random_fallback_image(
            category="other",
            seed=f"{slug}-emergency"
        )
    
    logger.info(f"Final featured_image_url: {featured_image_url[:80]}")
    
    # === STEP 2: Upload featured image to WordPress BEFORE creating post ===
    # This ensures we have a valid media_id to include in create_post
    if not featured_image_wp_id:
        logger.info("Uploading featured image to WordPress...")
        try:
            from app.publisher.image_handler import download_image_with_retry, resize_image
            image_bytes = await download_image_with_retry(featured_image_url, max_retries=3)
            if image_bytes:
                image_bytes = resize_image(image_bytes)
                filename = f"{slug[:40]}-featured-{abs(hash(featured_image_url)) % 10000}.jpg"
                upload_result = client.upload_media(
                    image_bytes=image_bytes,
                    filename=filename,
                    mime_type="image/jpeg",
                    alt_text=source_credit or "Featured Image",
                    caption=source_credit or "Featured Image",
                )
                if upload_result and upload_result.get("id"):
                    featured_image_wp_id = upload_result.get("id")
                    logger.info(f"Featured image uploaded: media_id={featured_image_wp_id}")
                else:
                    logger.warning(f"Featured image upload returned no ID: {upload_result}")
            else:
                logger.warning(f"Failed to download featured image: {featured_image_url}")
        except Exception as e:
            logger.error(f"Featured image upload failed: {e}")
    
    # === STEP 3: Set article.featured_image_wp_id for create_post ===
    if featured_image_wp_id:
        article.featured_image_wp_id = featured_image_wp_id
        logger.info(f"article.featured_image_wp_id set: {featured_image_wp_id}")


    # === CRITICAL: NO IMAGE DUPLICATION ===
    # WordPress themes automatically show featured image at top of post
    # We must NOT add the same image to content if it's already the featured image
    # This prevents the same image from appearing twice
    
    # Count images currently in content
    content_image_count = len(re.findall(r'<img', content))
    logger.info(f"Content already has {content_image_count} images")
    
    # === GUARANTEE AT LEAST ONE IMAGE IN CONTENT ===
    # Always ensure content has at least one image
    if '<img' not in content:
        logger.warning("No images in content! Adding content-only fallback...")
        
        # Get a fallback image for content (not used as featured)
        fallback_url = get_random_fallback_image(
            category=getattr(article, 'category', None),
            seed=f"{slug}-content"
        )
        
        # Add to content only
        content_img_html = f'<figure class="wp-block-image size-large"><img src="{fallback_url}" alt="Illustration" loading="lazy" /><figcaption class="wp-element-caption">Illustration</figcaption></figure>'
        content = content_img_html + '\n\n' + content
        logger.info(f"Added content-only fallback image")
        
    # === LOG: Content has images, featured image is separate ===
    elif featured_image_url and '<img' in content:
        logger.info(f"Content has images, featured image will be displayed separately by WordPress")

    # === CRITICAL VALIDATION: NO PLACEHOLDERS ALLOWED ===
    placeholder_matches = re.findall(r'\[IMAGE_\d+\]', content)
    if placeholder_matches:
        logger.error(
            f"CRITICAL: {len(placeholder_matches)} image placeholders still exist in content! "
            f"Blocking publish. Placeholders: {placeholder_matches[:5]}"
        )
        return {
            "error": "image_placeholders_not_replaced",
            "reason": f"Content contains {len(placeholder_matches)} unresolved image placeholders. "
                      f"Cannot publish until all [IMAGE_X] markers are replaced with real images.",
            "placeholders": placeholder_matches[:10],
        }

    # Log final state
    logger.info(f"Content preview (first 200 chars): {content[:200]}")
    logger.info(f"Content has img tag: {'<img' in content}")
    logger.info(f"Content images count: {len(content_images)}")
    logger.info(f"Placeholders remaining: 0")

    # === VALIDATION: Check minimum content requirements ===
    # Strip HTML tags to get actual text content
    text_content = re.sub(r'<[^>]+>', '', content)
    text_content = re.sub(r'\s+', ' ', text_content).strip()
    text_length = len(text_content)

    # Get word count
    word_count = getattr(article, 'word_count', 0) or 0

    # Minimum requirements: at least 50 words OR at least 200 characters of text
    MIN_WORDS = 50
    MIN_TEXT_LENGTH = 200

    if word_count < MIN_WORDS and text_length < MIN_TEXT_LENGTH:
        logger.warning(
            f"Article content too short: {word_count} words, {text_length} chars. "
            f"Skipping publish. Requirements: {MIN_WORDS} words OR {MIN_TEXT_LENGTH} chars."
        )
        return {
            "error": "content_too_short",
            "reason": f"Content too short: {word_count} words, {text_length} chars. Need {MIN_WORDS} words or {MIN_TEXT_LENGTH} chars.",
            "word_count": word_count,
            "text_length": text_length,
        }

    # Update article body_html with new content
    article.body_html = content

    # === FIX: Check for duplicate BEFORE creating WordPress post ===
    # Check by title_hash to catch duplicates even with different slugs
    from sqlalchemy import select
    from app.models.article import Article, ArticleState
    
    dup_stmt = select(Article).where(
        Article.title_hash == article.title_hash,
        Article.state == ArticleState.PUBLISHED.value,
        Article.wp_url.isnot(None),
        Article.id != article.id,
    )
    dup_result = await session.execute(dup_stmt)
    existing_pub = dup_result.scalar_one_or_none()
    
    if existing_pub:
        logger.warning(
            f"DUPLICATE BY TITLE HASH at publish time: Article '{article.original_title[:50]}' "
            f"(ID: {article.id}) matches published article '{existing_pub.original_title[:50]}' "
            f"(ID: {existing_pub.id}, URL: {existing_pub.wp_url})"
        )
        return {
            "duplicate": True,
            "skipped": True,
            "reason": "duplicate_title_hash",
            "existing_wp_url": existing_pub.wp_url,
        }

    # Create post
    result = client.create_post(article)

    # === FIX: Handle duplicate slug detection ===
    if result.get("duplicate"):
        existing_url = result.get("wp_url")
        logger.warning(
            f"DUPLICATE POST DETECTED: Article '{article.original_title[:50]}' "
            f"already exists at {existing_url}. Skipping publish."
        )
        return {
            "duplicate": True,
            "skipped": True,
            "reason": "duplicate_slug",
            "existing_wp_url": existing_url,
            "existing_wp_post_id": result.get("wp_post_id"),
        }

    if "error" in result:
        return result

    wp_post_id = result.get("wp_post_id")

    # === VERIFY FEATURED IMAGE ===
    # At this point, featured image should already be set via create_post
    # Verify by checking if the post response contains featured_media
    wp_response = result.get("wp_response", {})
    featured_media_in_response = wp_response.get("featured_media_source_url") or wp_response.get("featured_image")
    
    if featured_media_in_response:
        logger.info(f"Featured image verified in create_post response: {featured_media_in_response[:60]}")
        featured_image_set = True
    elif featured_image_wp_id:
        # Try to set via update_post as fallback
        try:
            update_result = client.update_post(wp_post_id, {"featured_media": featured_image_wp_id})
            if "error" not in update_result:
                logger.info(f"Featured image set via update_post: media_id={featured_image_wp_id}")
                featured_image_set = True
            else:
                logger.warning(f"Failed to set featured via update_post: {update_result}")
                featured_image_set = False
        except Exception as e:
            logger.warning(f"Featured image verification failed: {e}")
            featured_image_set = False
    else:
        logger.error("CRITICAL: No featured_image_wp_id available!")
        featured_image_set = False

    # === FINAL STATUS ===
    if featured_image_set:
        logger.info(f"SUCCESS: Featured image verified for post {wp_post_id}")
    else:
        logger.error(f"WARNING: Featured image may not be set for post {wp_post_id}")

    # Log final status
    logger.info(f"=== PUBLISH COMPLETE ===")
    logger.info(f"Article ID: {article.id}")
    logger.info(f"WP Post ID: {wp_post_id}")
    logger.info(f"Featured Image WP ID: {featured_image_wp_id}")
    logger.info(f"Featured Image URL: {featured_image_url[:80] if featured_image_url else 'None'}...")
    logger.info(f"Featured Image Set: {featured_image_set}")
    logger.info(f"Content Images Count: {len(content_images)}")
    logger.info(f"Content has img tag: {'<img' in content}")

    return {
        "wp_post_id": wp_post_id,
        "wp_url": result.get("wp_url"),
        "featured_image_wp_id": featured_image_wp_id,
        "featured_image_url": featured_image_url,
        "featured_image_set": featured_image_set,
        "content_images_count": len(content_images),
        "published_at": datetime.utcnow(),
        "wp_response": result.get("wp_response"),
    }


async def ping_on_article_publish(wp_url: str):
    """
    Ping search engines after article publish.
    This runs asynchronously to not block the publish response.
    """
    try:
        from app.seo.ping_service import ping_on_publish
        result = await ping_on_publish(wp_url)
        if result.is_success:
            logger.info(f"Search engines notified: {wp_url}")
        else:
            logger.warning(f"Search engine ping partial/failed: {wp_url} - {result.error_message}")
    except Exception as e:
        logger.error(f"Failed to ping search engines: {e}")
