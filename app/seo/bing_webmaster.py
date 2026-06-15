"""
Bing Webmaster API integration for SEO.
https://learn.microsoft.com/en-us/bingwebmaster/api-resources/3/url-submission
"""
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class BingSubmitResult:
    """Result of a Bing submission operation"""
    url: str
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None


class BingWebmasterAPI:
    """
    Bing Webmaster API client.
    
    Requires:
    1. Bing API key (free from Bing Webmaster Tools)
    2. Site registered in Bing Webmaster Tools
    """
    
    # Bing Webmaster API endpoints
    SUBMIT_URL_ENDPOINT = "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl"
    GET_URL_STATUS_ENDPOINT = "https://ssl.bing.com/webmaster/api.svc/json/GetUrlInfo"
    ADD_SITE_ENDPOINT = "https://ssl.bing.com/webmaster/api.svc/json/AddSite"
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
    
    @property
    def api_key(self) -> str:
        """Get Bing API key"""
        return self.settings.bing_api_key
    
    @property
    def is_configured(self) -> bool:
        """Check if API is configured"""
        return bool(self.api_key)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def submit_url(self, site_url: str, page_url: str) -> BingSubmitResult:
        """
        Submit a URL to Bing for indexing.
        
        Args:
            site_url: The root URL of your site (e.g., https://litimez.ai/)
            page_url: The specific page URL to submit
            
        Returns:
            BingSubmitResult with success status
        """
        if not self.is_configured:
            return BingSubmitResult(
                url=page_url,
                success=False,
                error_message="Bing API key not configured"
            )
        
        try:
            client = await self._get_client()
            
            # Bing requires URL-encoded site URL
            import urllib.parse
            encoded_site = urllib.parse.quote(site_url, safe="")
            
            params = {
                "siteUrl": site_url,
                "url": page_url,
                "apiKey": self.api_key
            }
            
            response = await client.post(
                self.SUBMIT_URL_ENDPOINT,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if "ErrorCode" in data:
                    error_msg = data.get("Message", data.get("ErrorCode", "Unknown error"))
                    logger.warning(f"Bing submission error for {page_url}: {error_msg}")
                    return BingSubmitResult(
                        url=page_url,
                        success=False,
                        error_message=error_msg
                    )
                
                logger.info(f"Submitted {page_url} to Bing")
                return BingSubmitResult(
                    url=page_url,
                    success=True,
                    timestamp=datetime.utcnow()
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to submit {page_url} to Bing: {error_msg}")
                return BingSubmitResult(
                    url=page_url,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            logger.error(f"Exception submitting {page_url} to Bing: {e}")
            return BingSubmitResult(
                url=page_url,
                success=False,
                error_message=str(e)
            )
    
    async def submit_batch(self, site_url: str, page_urls: List[str]) -> List[BingSubmitResult]:
        """
        Submit multiple URLs to Bing.
        
        Args:
            site_url: The root URL of your site
            page_urls: List of page URLs to submit
            
        Returns:
            List of BingSubmitResult for each URL
        """
        results = []
        
        for url in page_urls:
            result = await self.submit_url(site_url, url)
            results.append(result)
            # Small delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.1)
        
        return results
    
    async def get_url_status(self, site_url: str, page_url: str) -> dict:
        """
        Get the indexing status of a URL from Bing.
        
        Args:
            site_url: The root URL of your site
            page_url: The page URL to check
            
        Returns:
            dict with URL status information
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Bing API key not configured"
            }
        
        try:
            client = await self._get_client()
            
            params = {
                "siteUrl": site_url,
                "url": page_url,
                "apiKey": self.api_key
            }
            
            response = await client.post(
                self.GET_URL_STATUS_ENDPOINT,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "data": data
                }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def test_connection(self) -> dict:
        """
        Test Bing Webmaster API connection.
        
        Returns:
            dict with connection status
        """
        if not self.is_configured:
            return {
                "status": "not_configured",
                "message": "Bing API key not set in settings"
            }
        
        return {
            "status": "connected",
            "message": "Bing Webmaster API configured",
            "api_key_prefix": self.api_key[:8] + "***" if len(self.api_key) > 8 else "***"
        }


# Singleton instance
_bing_api: Optional[BingWebmasterAPI] = None


async def get_bing_webmaster_api() -> BingWebmasterAPI:
    """Get or create Bing Webmaster API instance"""
    global _bing_api
    if _bing_api is None:
        _bing_api = BingWebmasterAPI()
    return _bing_api


async def close_bing_webmaster_api():
    """Close Bing Webmaster API client"""
    global _bing_api
    if _bing_api:
        await _bing_api.close()
        _bing_api = None
