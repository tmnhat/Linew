"""
Ping Service - Combined service for Google and Bing index submission.
Automatically notifies search engines when articles are published.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from app.config import get_settings
from app.seo.google_indexing import (
    GoogleIndexingAPI, 
    IndexAction, 
    IndexResult,
    get_google_indexing_api
)
from app.seo.bing_webmaster import (
    BingWebmasterAPI,
    BingSubmitResult,
    get_bing_webmaster_api
)

logger = logging.getLogger(__name__)


class PingStatus(str, Enum):
    """Status of a ping operation"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PingResult:
    """Combined result of ping operation"""
    url: str
    google_result: Optional[IndexResult] = None
    bing_result: Optional[BingSubmitResult] = None
    status: PingStatus = PingStatus.SKIPPED
    
    @property
    def is_success(self) -> bool:
        return self.status in [PingStatus.SUCCESS, PingStatus.PARTIAL]
    
    @property
    def error_message(self) -> Optional[str]:
        errors = []
        if self.google_result and not self.google_result.success:
            errors.append(f"Google: {self.google_result.error_message}")
        if self.bing_result and not self.bing_result.success:
            errors.append(f"Bing: {self.bing_result.error_message}")
        return "; ".join(errors) if errors else None


class PingService:
    """
    Combined ping service for search engines.
    
    Handles:
    - Google Indexing API
    - Bing Webmaster API
    - Automatic retry on failure
    - Logging and monitoring
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._google_api: Optional[GoogleIndexingAPI] = None
        self._bing_api: Optional[BingWebmasterAPI] = None
    
    @property
    def is_enabled(self) -> bool:
        """Check if ping service is enabled"""
        return (
            bool(self.settings.google_service_account_json) or 
            bool(self.settings.bing_api_key)
        )
    
    async def _get_google_api(self) -> GoogleIndexingAPI:
        """Get Google Indexing API instance"""
        if self._google_api is None:
            self._google_api = await get_google_indexing_api()
        return self._google_api
    
    async def _get_bing_api(self) -> BingWebmasterAPI:
        """Get Bing Webmaster API instance"""
        if self._bing_api is None:
            self._bing_api = await get_bing_webmaster_api()
        return self._bing_api
    
    async def ping_url(
        self, 
        url: str, 
        action: str = "publish",
        notify_google: bool = True,
        notify_bing: bool = True
    ) -> PingResult:
        """
        Ping search engines about a URL change.
        
        Args:
            url: The URL that changed
            action: Type of change (publish, update, delete)
            notify_google: Whether to notify Google
            notify_bing: Whether to notify Bing
            
        Returns:
            PingResult with status of each ping
        """
        result = PingResult(url=url)
        
        google_success = False
        bing_success = False
        
        # Google ping
        if notify_google and self.settings.google_service_account_json:
            try:
                google_api = await self._get_google_api()
                index_action = (
                    IndexAction.URL_DELETED if action == "delete" 
                    else IndexAction.URL_UPDATED
                )
                result.google_result = await google_api.index_url(url, index_action)
                google_success = result.google_result.success
                
                if google_success:
                    logger.info(f"Google indexed: {url}")
                else:
                    logger.warning(f"Google failed: {url} - {result.google_result.error_message}")
            except Exception as e:
                logger.error(f"Google ping exception: {e}")
        
        # Bing ping
        if notify_bing and self.settings.bing_api_key:
            try:
                bing_api = await self._get_bing_api()
                result.bing_result = await bing_api.submit_url(
                    self.settings.google_site_url,
                    url
                )
                bing_success = result.bing_result.success
                
                if bing_success:
                    logger.info(f"Bing submitted: {url}")
                else:
                    logger.warning(f"Bing failed: {url} - {result.bing_result.error_message}")
            except Exception as e:
                logger.error(f"Bing ping exception: {e}")
        
        # Determine overall status
        if google_success and bing_success:
            result.status = PingStatus.SUCCESS
        elif google_success or bing_success:
            result.status = PingStatus.PARTIAL
        elif not self.is_enabled:
            result.status = PingStatus.SKIPPED
        else:
            result.status = PingStatus.FAILED
        
        return result
    
    async def ping_batch(
        self,
        urls: List[str],
        action: str = "publish"
    ) -> List[PingResult]:
        """
        Ping multiple URLs.
        
        Args:
            urls: List of URLs to ping
            action: Type of change
            
        Returns:
            List of PingResult for each URL
        """
        results = []
        
        for url in urls:
            result = await self.ping_url(url, action)
            results.append(result)
        
        return results
    
    async def unindex_url(self, url: str) -> PingResult:
        """
        Remove a URL from search engine indexes.
        
        Args:
            url: The URL to remove
            
        Returns:
            PingResult with removal status
        """
        return await self.ping_url(url, action="delete")
    
    async def test_connections(self) -> Dict[str, Any]:
        """
        Test connection to both APIs.
        
        Returns:
            dict with status of each API
        """
        results = {
            "google": {"status": "not_configured"},
            "bing": {"status": "not_configured"},
            "overall": "ok"
        }
        
        # Test Google
        if self.settings.google_service_account_json:
            try:
                google_api = await self._get_google_api()
                results["google"] = await google_api.test_connection()
            except Exception as e:
                results["google"] = {"status": "error", "message": str(e)}
        
        # Test Bing
        if self.settings.bing_api_key:
            try:
                bing_api = await self._get_bing_api()
                results["bing"] = await bing_api.test_connection()
            except Exception as e:
                results["bing"] = {"status": "error", "message": str(e)}
        
        # Overall status
        if not self.is_enabled:
            results["overall"] = "disabled"
        elif results["google"].get("status") == "connected" and results["bing"].get("status") == "connected":
            results["overall"] = "ok"
        elif results["google"].get("status") == "connected" or results["bing"].get("status") == "connected":
            results["overall"] = "partial"
        else:
            results["overall"] = "error"
        
        return results
    
    async def close(self):
        """Close API clients"""
        from app.seo.google_indexing import close_google_indexing_api
        from app.seo.bing_webmaster import close_bing_webmaster_api
        
        await close_google_indexing_api()
        await close_bing_webmaster_api()
        self._google_api = None
        self._bing_api = None


# Singleton instance
_ping_service: Optional[PingService] = None


async def get_ping_service() -> PingService:
    """Get or create PingService instance"""
    global _ping_service
    if _ping_service is None:
        _ping_service = PingService()
    return _ping_service


async def close_ping_service():
    """Close PingService"""
    global _ping_service
    if _ping_service:
        await _ping_service.close()
        _ping_service = None


async def ping_on_publish(url: str) -> PingResult:
    """
    Convenience function to ping on article publish.
    
    Args:
        url: The published article URL
        
    Returns:
        PingResult
    """
    service = await get_ping_service()
    return await service.ping_url(url, action="publish")


async def ping_on_update(url: str) -> PingResult:
    """
    Convenience function to ping on article update.
    
    Args:
        url: The updated article URL
        
    Returns:
        PingResult
    """
    service = await get_ping_service()
    return await service.ping_url(url, action="update")


async def ping_on_delete(url: str) -> PingResult:
    """
    Convenience function to ping on article delete.
    
    Args:
        url: The deleted article URL
        
    Returns:
        PingResult
    """
    service = await get_ping_service()
    return await service.unindex_url(url)
