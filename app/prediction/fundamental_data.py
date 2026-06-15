"""
L2: Fundamental Data Module for Prediction V2.

Fetches fundamental financial data for:
- US Stocks: P/E ratio, EPS, Revenue, Balance Sheet (via yfinance)
- Crypto: Market cap, volume, dominance (via CoinGecko)

CHỈ HỖ TRỢ: CRYPTO & US STOCK (không hỗ trợ VN stock)
"""
import logging
from typing import Optional

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class FundamentalDataFetcher:
    """Fetch and cache fundamental data for crypto and US stocks."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    async def get_us_stock_fundamentals(self, symbol: str) -> dict:
        """
        Get fundamental data for US stock using yfinance.
        Symbol: e.g., "AAPL", "GOOGL", "MSFT"
        """
        cache_key = f"fundamental:us:{symbol.upper()}"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                logger.debug(f"Fundamental cache hit: {symbol}")
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        # Fetch from yfinance
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            data = {
                "symbol": symbol.upper(),
                "market": "us",
                "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                "eps": info.get("trailingEps") or info.get("forwardEps"),
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "market_cap": info.get("marketCap"),
                "book_value": info.get("bookValue"),
                "debt_to_equity": info.get("debtToEquity"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            }

            # Cache result
            try:
                r = await self.get_redis()
                import json
                await r.setex(cache_key, self.settings.cache_ttl_fundamental, json.dumps(data))
            except Exception as e:
                logger.warning(f"Failed to cache fundamental data: {e}")

            return data

        except ImportError:
            logger.error("yfinance not installed")
            return {"error": "yfinance not available"}
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return {"error": str(e)}

    async def get_crypto_fundamentals(self, symbol: str) -> dict:
        """
        Get fundamental data for crypto using CoinGecko.
        Symbol: e.g., "bitcoin", "ethereum" (CoinGecko ID)
        """
        cache_key = f"fundamental:crypto:{symbol.lower()}"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                logger.debug(f"Crypto fundamental cache hit: {symbol}")
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        # Map common symbols to CoinGecko IDs
        symbol_map = {
            "btc": "bitcoin",
            "btcusdt": "bitcoin",
            "eth": "ethereum",
            "ethusdt": "ethereum",
            "bnb": "binancecoin",
            "sol": "solana",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "dot": "polkadot",
        }
        cg_id = symbol_map.get(symbol.lower(), symbol.lower())

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get coin data
                resp = await client.get(
                    f"https://api.coingecko.com/api/v3/coins/{cg_id}",
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "community_data": "false",
                        "developer_data": "false",
                    }
                )

                if resp.status_code == 404:
                    return {"error": f"Coin not found: {symbol}"}

                resp.raise_for_status()
                data = resp.json()
                market_data = data.get("market_data", {})

                result = {
                    "symbol": symbol.upper(),
                    "market": "crypto",
                    "coingecko_id": cg_id,
                    "market_cap": market_data.get("market_cap", {}).get("usd"),
                    "market_cap_rank": data.get("market_cap_rank"),
                    "volume_24h": market_data.get("total_volume", {}).get("usd"),
                    "price": market_data.get("current_price", {}).get("usd"),
                    "price_change_24h": market_data.get("price_change_24h"),
                    "price_change_pct_24h": market_data.get("price_change_percentage_24h"),
                    "ath": market_data.get("ath", {}).get("usd"),
                    "atl": market_data.get("atl", {}).get("usd"),
                    "ath_change_pct": market_data.get("ath_change_percentage", {}).get("usd"),
                    "circulating_supply": market_data.get("circulating_supply"),
                    "total_supply": market_data.get("total_supply"),
                    "max_supply": market_data.get("max_supply"),
                    " dominance": None,  # Calculated separately
                }

                # Cache result
                try:
                    r = await self.get_redis()
                    import json
                    await r.setex(cache_key, self.settings.cache_ttl_fundamental, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Failed to cache crypto fundamental: {e}")

                return result

        except ImportError:
            logger.error("httpx not installed")
            return {"error": "httpx not available"}
        except Exception as e:
            logger.error(f"Failed to fetch crypto fundamentals for {symbol}: {e}")
            return {"error": str(e)}

    async def get_fundamentals(self, symbol: str, market: Optional[str] = None) -> dict:
        """
        Get fundamentals for any supported symbol.
        Auto-detects market if not provided.
        """
        if market is None:
            from app.prediction.data_fetcher import detect_market
            market = detect_market(symbol)

        if market == "crypto":
            return await self.get_crypto_fundamentals(symbol)
        elif market == "us":
            return await self.get_us_stock_fundamentals(symbol)
        else:
            return {"error": f"Market {market} not supported for fundamentals. Only crypto & US stocks."}

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance
_fundamental_fetcher: Optional[FundamentalDataFetcher] = None


def get_fundamental_fetcher() -> FundamentalDataFetcher:
    """Get or create singleton instance."""
    global _fundamental_fetcher
    if _fundamental_fetcher is None:
        _fundamental_fetcher = FundamentalDataFetcher()
    return _fundamental_fetcher
