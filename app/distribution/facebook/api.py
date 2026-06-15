"""
Facebook Graph API integration.

Handles:
- Photo upload to Facebook
- Page post creation
- API error handling
"""
import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"


def get_graph_api_url() -> str:
    """Get the Facebook Graph API URL with configured version."""
    from app.config import get_settings
    settings = get_settings()
    return f"{GRAPH_API_BASE}/{settings.facebook_api_version}"

# Facebook API error codes
ERROR_TOKEN_EXPIRED = 190
ERROR_PERMISSION_DENIED = 200
ERROR_RATE_LIMIT = 4


async def upload_photo_to_facebook(
    client: httpx.AsyncClient,
    page_id: str,
    access_token: str,
    image_url: str
) -> Optional[str]:
    """
    Upload a photo to Facebook and return the photo ID.
    
    Returns:
        Photo ID if successful, None otherwise.
    """
    try:
        response = await client.post(
            f"{get_graph_api_url()}/{page_id}/photos",
            data={
                "url": image_url,
                "published": "false",
                "access_token": access_token,
            },
            timeout=60.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data:
                photo_id = data["id"]
                logger.info(f"Uploaded photo to Facebook: {photo_id}")
                return photo_id
        
        logger.warning(f"Photo upload failed: {response.status_code} - {response.text}")
        return None
        
    except httpx.TimeoutException:
        logger.error("Photo upload timed out")
        return None
    except Exception as e:
        logger.error(f"Photo upload error: {e}")
        return None


async def create_photo_post(
    client: httpx.AsyncClient,
    page_id: str,
    access_token: str,
    photo_id: str,
    message: str,
    link: Optional[str] = None,
) -> Optional[dict]:
    """
    Create a post with the uploaded photo.
    
    Returns:
        Dict with post_id and post_url if successful.
    """
    try:
        data = {
            "access_token": access_token,
            "message": message,
            "attached_media": f'[{{"media_fbid": "{photo_id}"}}]',
        }
        
        # FIX: Only include link if we explicitly want it
        # For no-link posts, don't include link parameter
        if link is not None:
            data["link"] = link
        
        response = await client.post(
            f"{get_graph_api_url()}/{page_id}/feed",
            data=data,
            timeout=30.0,
        )
        
        if response.status_code == 200:
            result = response.json()
            post_id = result.get("id")
            post_url = f"https://www.facebook.com/{page_id}/posts/{post_id}" if post_id else None
            logger.info(f"Created Facebook post: {post_id}")
            return {
                "post_id": post_id,
                "post_url": post_url,
            }
        
        # Parse error
        try:
            error_data = response.json()
            error_code = error_data.get("error", {}).get("code")
            error_msg = error_data.get("error", {}).get("message", "")
            
            if error_code == ERROR_TOKEN_EXPIRED:
                logger.error("Facebook access token expired")
            elif error_code == ERROR_PERMISSION_DENIED:
                logger.error("Facebook permission denied")
            elif error_code == ERROR_RATE_LIMIT:
                logger.warning("Facebook rate limit hit")
            
            return {"error": error_msg, "error_code": error_code}
        except:
            pass
        
        logger.warning(f"Post creation failed: {response.status_code} - {response.text}")
        return {"error": f"HTTP {response.status_code}"}
        
    except httpx.TimeoutException:
        logger.error("Post creation timed out")
        return {"error": "timeout"}
    except Exception as e:
        logger.error(f"Post creation error: {e}")
        return {"error": str(e)}


async def post_photo_to_facebook(
    page_id: str,
    access_token: str,
    image_url: str,
    message: str,
    no_link: bool = True,
) -> Optional[dict]:
    """
    Post a photo with message to Facebook Page.
    
    Args:
        page_id: Facebook Page ID
        access_token: Page access token
        image_url: URL of the image to post
        message: Post message
        no_link: If True, don't include any link in the post
    
    Returns:
        Dict with post_id and post_url if successful.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Upload photo (don't publish yet)
        photo_id = await upload_photo_to_facebook(client, page_id, access_token, image_url)
        
        if not photo_id:
            return {"error": "photo_upload_failed"}
        
        # Step 2: Create post with photo (without link)
        # FIX: Pass None for link to ensure no-link post
        link = None if no_link else None  # Explicitly set to None for no-link
        
        result = await create_photo_post(
            client, page_id, access_token, photo_id, message, link=link
        )
        
        return result


async def test_facebook_connection(page_id: str, access_token: str) -> dict:
    """
    Test Facebook API connection.
    
    Returns:
        Dict with connection status and page info.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
            f"{get_graph_api_url()}/{page_id}",
                params={"access_token": access_token, "fields": "id,name,fan_count"},
                timeout=10.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "connected": True,
                    "page": {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "fan_count": data.get("fan_count"),
                    },
                }
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "")
                    error_code = error_data.get("error", {}).get("code")
                    return {
                        "connected": False,
                        "error": error_msg,
                        "error_code": error_code,
                    }
                except:
                    pass
                
                return {"connected": False, "error": f"HTTP {response.status_code}"}
                
    except Exception as e:
        return {"connected": False, "error": str(e)}
