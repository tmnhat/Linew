"""
Google Indexing API integration for SEO.
https://developers.google.com/search/apis/indexing-api/v3-quickstart
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from app.config import get_settings

logger = logging.getLogger(__name__)


class IndexAction(str, Enum):
    """Actions for Google Indexing API"""
    URL_UPDATED = "URL_UPDATED"  # For new or updated content
    URL_DELETED = "URL_DELETED"  # For removed content


@dataclass
class IndexResult:
    """Result of an indexing operation"""
    url: str
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None


class GoogleIndexingAPI:
    """
    Google Indexing API client.
    
    Requires:
    1. Service account with Indexing API access
    2. Site verification in Google Search Console
    3. Service account email added to Search Console
    """
    
    SCOPES = ["https://www.googleapis.com/auth/indexing"]
    ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    
    def __init__(self):
        self.settings = get_settings()
        self._credentials = None
        self._client = None
    
    async def _get_credentials(self):
        """Get OAuth2 credentials from service account JSON"""
        if self._credentials is None:
            if not self.settings.google_service_account_json:
                logger.warning("Google service account JSON not configured")
                return None
            
            try:
                import json
                service_account_info = json.loads(self.settings.google_service_account_json)
                self._credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=self.SCOPES
                )
                logger.info("Google service account credentials loaded")
            except Exception as e:
                logger.error(f"Failed to load Google service account: {e}")
                return None
        
        return self._credentials
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with auth"""
        if self._client is None:
            credentials = await self._get_credentials()
            if credentials:
                # Refresh credentials
                credentials.refresh(Request())
                token = credentials.token
                
                self._client = httpx.AsyncClient(
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
            else:
                self._client = httpx.AsyncClient(timeout=30.0)
        
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def index_url(self, url: str, action: IndexAction = IndexAction.URL_UPDATED) -> IndexResult:
        """
        Submit a URL to Google Indexing API.
        
        Args:
            url: The URL to index
            action: URL_UPDATED for new/changed, URL_DELETED for removed
            
        Returns:
            IndexResult with success status and any error message
        """
        credentials = await self._get_credentials()
        if not credentials:
            return IndexResult(
                url=url,
                success=False,
                error_message="Google service account not configured"
            )
        
        try:
            client = await self._get_client()
            
            payload = {
                "url": url,
                "type": action.value
            }
            
            response = await client.post(self.ENDPOINT, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Indexed {url}: {data.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('type')}")
                return IndexResult(
                    url=url,
                    success=True,
                    timestamp=datetime.utcnow()
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to index {url}: {error_msg}")
                return IndexResult(
                    url=url,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            logger.error(f"Exception indexing {url}: {e}")
            return IndexResult(
                url=url,
                success=False,
                error_message=str(e)
            )
    
    async def index_batch(self, urls: List[str], action: IndexAction = IndexAction.URL_UPDATED) -> List[IndexResult]:
        """
        Submit multiple URLs to Google Indexing API.
        Note: Google's API has a limit of 100 URLs per batch, but we process one at a time
        for simplicity.
        
        Args:
            urls: List of URLs to index
            action: URL_UPDATED or URL_DELETED
            
        Returns:
            List of IndexResult for each URL
        """
        results = []
        
        for url in urls:
            result = await self.index_url(url, action)
            results.append(result)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return results
    
    async def delete_url(self, url: str) -> IndexResult:
        """
        Remove a URL from Google index.
        
        Args:
            url: The URL to remove
            
        Returns:
            IndexResult with success status
        """
        return await self.index_url(url, IndexAction.URL_DELETED)
    
    async def test_connection(self) -> dict:
        """
        Test Google Indexing API connection.
        
        Returns:
            dict with connection status
        """
        if not self.settings.google_service_account_json:
            return {
                "status": "not_configured",
                "message": "Google service account JSON not set in settings"
            }
        
        if not self.settings.google_site_url:
            return {
                "status": "not_configured",
                "message": "Google site URL not set in settings"
            }
        
        try:
            credentials = await self._get_credentials()
            if not credentials:
                return {
                    "status": "auth_failed",
                    "message": "Failed to authenticate with service account"
                }
            
            # Try to get an access token
            credentials.refresh(Request())
            
            return {
                "status": "connected",
                "message": "Successfully connected to Google Indexing API",
                "site_url": self.settings.google_site_url
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


# Singleton instance
_indexing_api: Optional[GoogleIndexingAPI] = None


async def get_google_indexing_api() -> GoogleIndexingAPI:
    """Get or create Google Indexing API instance"""
    global _indexing_api
    if _indexing_api is None:
        _indexing_api = GoogleIndexingAPI()
    return _indexing_api


async def close_google_indexing_api():
    """Close Google Indexing API client"""
    global _indexing_api
    if _indexing_api:
        await _indexing_api.close()
        _indexing_api = None
