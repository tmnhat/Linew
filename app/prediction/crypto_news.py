"""
Crypto news fetcher - lấy tin tức crypto từ nhiều nguồn.
Hỗ trợ CoinGecko API (miễn phí) và RSS feeds.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
import feedparser

logger = logging.getLogger(__name__)


class CryptoNewsFetcher:
    """
    Fetcher cho crypto news từ nhiều nguồn.
    """
    
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    COINDESK_RSS = "https://www.coindesk.com/feed/"
    
    def __init__(self):
        self._coin_id_cache: dict[str, str] = {}
        self._coin_id_cache_time: Optional[datetime] = None
    
    async def get_coin_id(self, symbol: str) -> Optional[str]:
        """
        Convert trading symbol (BTCUSDT) sang CoinGecko coin ID (bitcoin).
        """
        symbol_upper = symbol.upper().replace("-USD", "").replace("USDT", "")
        
        # Check cache
        if symbol_upper in self._coin_id_cache:
            return self._coin_id_cache[symbol_upper]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search for coin
                response = await client.get(
                    f"{self.COINGECKO_API}/search",
                    params={"query": symbol_upper}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    coins = data.get("coins", [])
                    
                    if coins:
                        coin_id = coins[0]["id"]
                        self._coin_id_cache[symbol_upper] = coin_id
                        return coin_id
                        
        except Exception as e:
            logger.warning(f"Failed to get coin ID for {symbol}: {e}")
        
        return None
    
    async def get_market_data(self, coin_id: str) -> Optional[dict]:
        """
        Lấy market data từ CoinGecko.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.COINGECKO_API}/coins/{coin_id}",
                    params={
                        "localization": False,
                        "tickers": False,
                        "community_data": False,
                        "developer_data": False,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data.get("id"),
                        "symbol": data.get("symbol"),
                        "name": data.get("name"),
                        "market_cap_rank": data.get("market_cap_rank"),
                        "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd"),
                        "total_volume": data.get("market_data", {}).get("total_volume", {}).get("usd"),
                        "price_change_24h": data.get("market_data", {}).get("price_change_percentage_24h"),
                        "price_change_7d": data.get("market_data", {}).get("price_change_percentage_7d"),
                        "ath": data.get("market_data", {}).get("ath", {}).get("usd"),
                        "atl": data.get("market_data", {}).get("atl", {}).get("usd"),
                        "description": data.get("description", {}).get("en", "")[:500],
                    }
                    
        except Exception as e:
            logger.warning(f"Failed to get market data for {coin_id}: {e}")
        
        return None
    
    async def get_trending(self) -> list[dict]:
        """
        Lấy danh sách trending coins từ CoinGecko.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.COINGECKO_API}/search/trending")
                
                if response.status_code == 200:
                    data = response.json()
                    trending = []
                    
                    for coin in data.get("coins", [])[:10]:
                        item = coin.get("item", {})
                        trending.append({
                            "id": item.get("id"),
                            "symbol": item.get("symbol"),
                            "name": item.get("name"),
                            "market_cap_rank": item.get("market_cap_rank"),
                            "score": coin.get("score"),
                        })
                    
                    return trending
                    
        except Exception as e:
            logger.warning(f"Failed to get trending coins: {e}")
        
        return []
    
    async def get_global_data(self) -> Optional[dict]:
        """
        Lấy global crypto market data.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.COINGECKO_API}/global")
                
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    return {
                        "total_market_cap": data.get("total_market_cap", {}).get("usd"),
                        "total_volume": data.get("total_volume", {}).get("usd"),
                        "btc_dominance": data.get("market_cap_percentage", {}).get("btc"),
                        "eth_dominance": data.get("market_cap_percentage", {}).get("eth"),
                        "active_cryptocurrencies": data.get("active_cryptocurrencies"),
                        "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd"),
                    }
                    
        except Exception as e:
            logger.warning(f"Failed to get global data: {e}")
        
        return None
    
    async def fetch_coindesk_news(self, limit: int = 10) -> list[dict]:
        """
        Lấy tin tức từ CoinDesk RSS feed.
        """
        try:
            feed = feedparser.parse(self.COINDESK_RSS)
            
            news = []
            for entry in feed.entries[:limit]:
                news.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
            
            return news
            
        except Exception as e:
            logger.warning(f"Failed to fetch CoinDesk news: {e}")
            return []
    
    async def get_coin_news(self, symbol: str, limit: int = 5) -> list[str]:
        """
        Lấy news headlines cho một coin cụ thể.
        Kết hợp từ nhiều nguồn.
        
        Args:
            symbol: Trading symbol (VD: "BTCUSDT")
            limit: Số lượng headlines tối đa
            
        Returns:
            List of news headlines/summaries
        """
        news_headlines = []
        
        # Get coin ID
        coin_id = await self.get_coin_id(symbol)
        if not coin_id:
            # Fallback: search news by symbol
            coin_id = symbol.upper().replace("-USD", "").replace("USDT", "").lower()
        
        try:
            # Get recent news from CoinGecko
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.COINGECKO_API}/coins/{coin_id}/market_chart",
                    params={
                        "vs_currency": "usd",
                        "days": 7,
                        "interval": "daily",
                    }
                )
                
                # CoinGecko không có news API miễn phí
                # Thay vào đó, fetch general crypto news
                
        except Exception as e:
            logger.warning(f"Failed to get news for {symbol}: {e}")
        
        # Get general crypto news as fallback
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try CryptoCompare news API (free tier)
                response = await client.get(
                    "https://min-api.cryptocompare.com/data/v2/news/",
                    params={"lang": "EN", "categories": coin_id.upper()}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get("Data", [])[:limit]:
                        news_headlines.append(article.get("title", ""))
                        
        except Exception:
            pass
        
        # Get top crypto news if not enough
        if len(news_headlines) < limit:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "https://min-api.cryptocompare.com/data/v2/news/",
                        params={"lang": "EN", "categories": "Blockchain"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        for article in data.get("Data", [])[:limit - len(news_headlines)]:
                            title = article.get("title", "")
                            if title and title not in news_headlines:
                                news_headlines.append(title)
                                
            except Exception:
                pass
        
        return news_headlines[:limit]
    
    async def get_market_sentiment(self, symbol: str) -> dict:
        """
        Lấy market sentiment indicators cho một coin.
        Bao gồm fear & greed tương đối và social metrics.
        """
        sentiment = {
            "fear_greed_label": "neutral",
            "fear_greed_value": 50,
            "social_score": None,
            "reddit_posts": 0,
            "twitter_followers": None,
        }
        
        coin_id = await self.get_coin_id(symbol)
        if not coin_id:
            coin_id = symbol.upper().replace("-USD", "").replace("USDT", "").lower()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.COINGECKO_API}/coins/{coin_id}",
                    params={
                        "localization": False,
                        "tickers": False,
                        "market_data": True,
                        "community_data": True,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    market_data = data.get("market_data", {})
                    community_data = data.get("community_data", {})
                    
                    # Calculate fear/greed based on price changes
                    change_24h = market_data.get("price_change_percentage_24h", 0) or 0
                    change_7d = market_data.get("price_change_percentage_7d", 0) or 0
                    
                    if change_24h > 5 or change_7d > 10:
                        sentiment["fear_greed_label"] = "extreme_greed"
                        sentiment["fear_greed_value"] = 85
                    elif change_24h > 2 or change_7d > 5:
                        sentiment["fear_greed_label"] = "greed"
                        sentiment["fear_greed_value"] = 70
                    elif change_24h < -5 or change_7d < -10:
                        sentiment["fear_greed_label"] = "extreme_fear"
                        sentiment["fear_greed_value"] = 15
                    elif change_24h < -2 or change_7d < -5:
                        sentiment["fear_greed_label"] = "fear"
                        sentiment["fear_greed_value"] = 30
                    
                    # Social metrics
                    sentiment["social_score"] = community_data.get("twitter_followers_karma", 0)
                    sentiment["reddit_posts"] = community_data.get("reddit_subscribers", 0)
                    sentiment["twitter_followers"] = community_data.get("twitter_followers", 0)
                    
        except Exception as e:
            logger.warning(f"Failed to get sentiment for {symbol}: {e}")
        
        return sentiment


# Singleton instance
crypto_news_fetcher = CryptoNewsFetcher()


async def fetch_crypto_news(symbol: str, limit: int = 10) -> list[str]:
    """
    Helper function để fetch news cho một crypto symbol.
    
    Args:
        symbol: Trading symbol (VD: "BTCUSDT", "BTC-USD")
        limit: Số lượng headlines
        
    Returns:
        List of news headlines
    """
    # Normalize symbol
    normalized = symbol.upper().replace("-USD", "USDT").replace("/", "")
    if not normalized.endswith("USDT"):
        normalized = normalized + "USDT"
    
    return await crypto_news_fetcher.get_coin_news(normalized, limit)


async def get_crypto_global_sentiment() -> dict:
    """
    Lấy global crypto market sentiment.
    """
    return await crypto_news_fetcher.get_global_data()


async def get_coin_sentiment(symbol: str) -> dict:
    """
    Lấy sentiment cho một coin cụ thể.
    """
    return await crypto_news_fetcher.get_market_sentiment(symbol)
