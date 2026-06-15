"""
L3: Macro Economic Data Module for Prediction V2.

Fetches macroeconomic indicators:
- Fed Funds Rate, CPI, GDP (via FRED API)
- VIX, DXY Dollar Index (via FRED or yfinance)
- Crypto TVL, yields (via DeFiLlama)

CHỈ HỖ TRỢ: CRYPTO & US STOCK (không hỗ trợ VN stock)
"""
import logging
from typing import Optional

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class MacroDataFetcher:
    """Fetch and cache macroeconomic data."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    async def get_fred_data(self, series_id: str) -> dict:
        """
        Fetch data from FRED API.
        Common series: DFF (Fed Funds), CPIAUCSL, GDP, DXY, VIXCLS
        """
        cache_key = f"macro:fred:{series_id}"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        if not self.settings.fred_api_key:
            # Fallback to yfinance for common indicators
            return await self._get_from_yfinance(series_id)

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": self.settings.fred_api_key,
                        "file_type": "json",
                        "limit": 1,
                        "sort_order": "desc",
                    }
                )

                if resp.status_code == 400:
                    return {"error": f"FRED series not found: {series_id}"}

                resp.raise_for_status()
                data = resp.json()
                observations = data.get("observations", [])

                if not observations:
                    return {"error": f"No data for {series_id}"}

                latest = observations[0]
                result = {
                    "series_id": series_id,
                    "value": float(latest["value"]) if latest["value"] != "." else None,
                    "date": latest["date"],
                    "source": "FRED",
                }

                # Cache for 6 hours
                try:
                    r = await self.get_redis()
                    import json
                    await r.setex(cache_key, self.settings.cache_ttl_macro, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Failed to cache macro data: {e}")

                return result

        except ImportError:
            logger.error("httpx not installed")
            return await self._get_from_yfinance(series_id)
        except Exception as e:
            logger.error(f"Failed to fetch FRED data for {series_id}: {e}")
            return await self._get_from_yfinance(series_id)

    async def _get_from_yfinance(self, series_id: str) -> dict:
        """Fallback to yfinance for common macro indicators."""
        try:
            import yfinance as yf

            # Map FRED series to yfinance tickers
            ticker_map = {
                "VIXCLS": "^VIX",
                "DXY": "DX-Y.NYB",
            }

            ticker_symbol = ticker_map.get(series_id)
            if not ticker_symbol:
                return {"error": f"No yfinance fallback for {series_id}"}

            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")

            if hist.empty:
                return {"error": f"No data for {ticker_symbol}"}

            latest = hist.iloc[-1]
            result = {
                "series_id": series_id,
                "value": float(latest["Close"]),
                "date": hist.index[-1].strftime("%Y-%m-%d"),
                "source": "yfinance",
            }

            return result

        except ImportError:
            return {"error": "Neither FRED API nor yfinance available"}
        except Exception as e:
            return {"error": str(e)}

    async def get_defillama_data(self) -> dict:
        """Fetch DeFiLlama TVL and yields data."""
        cache_key = "macro:defillama"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get DeFi TVL
                tvl_resp = await client.get("https://api.llama.fi/protocols")
                tvl_resp.raise_for_status()
                protocols = tvl_resp.json()

                # Get total DeFi TVL
                total_tvl = sum(p.get("tvl", 0) for p in protocols if isinstance(p.get("tvl"), (int, float)))

                # Get ETH yield rates
                yields_resp = await client.get("https://api.llama.fi/v2/yields?pool=ethereum-steth")
                yields_resp.raise_for_status()
                yields_data = yields_resp.json()

                eth_yield = None
                if yields_data and len(yields_data) > 0:
                    pool = yields_data[0]
                    eth_yield = pool.get("apy", 0)

                result = {
                    "total_defi_tvl": total_tvl,
                    "eth_staking_yield": eth_yield,
                    "protocols_count": len(protocols),
                    "source": "DeFiLlama",
                }

                # Cache for 1 hour
                try:
                    r = await self.get_redis()
                    import json
                    await r.setex(cache_key, self.settings.cache_ttl_onchain, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Failed to cache DeFiLlama data: {e}")

                return result

        except ImportError:
            logger.error("httpx not installed")
            return {"error": "httpx not available"}
        except Exception as e:
            logger.error(f"Failed to fetch DeFiLlama data: {e}")
            return {"error": str(e)}

    async def get_all_macro_data(self) -> dict:
        """Fetch all macro indicators."""
        results = {}

        # Key FRED indicators
        fred_series = {
            "fed_funds_rate": "DFF",
            "cpi": "CPIAUCSL",
            "gdp": "GDP",
            "unemployment": "UNRATE",
            "sp500": "SP500",
        }

        for key, series_id in fred_series.items():
            results[key] = await self.get_fred_data(series_id)

        # VIX and DXY via yfinance
        results["vix"] = await self.get_fred_data("VIXCLS")
        results["dxy"] = await self.get_fred_data("DXY")

        # DeFi data
        results["defi"] = await self.get_defillama_data()

        return results

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance
_macro_fetcher: Optional[MacroDataFetcher] = None


def get_macro_fetcher() -> MacroDataFetcher:
    """Get or create singleton instance."""
    global _macro_fetcher
    if _macro_fetcher is None:
        _macro_fetcher = MacroDataFetcher()
    return _macro_fetcher
