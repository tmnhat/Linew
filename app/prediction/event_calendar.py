"""
L5: Event Calendar Module for Prediction V2.

Fetches important financial events:
- FOMC meeting dates (hardcoded for 2026)
- Earnings calendar (via Finnhub API)
- Dividend dates

CHỈ HỖ TRỢ: CRYPTO & US STOCK (không hỗ trợ VN stock)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

# FOMC Meeting Dates 2026 (Federal Reserve)
FOMC_MEETINGS_2026 = [
    {"date": "2026-01-28", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-01-29", "description": "FOMC Press Conference"},
    {"date": "2026-03-17", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-03-18", "description": "FOMC Press Conference"},
    {"date": "2026-05-05", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-05-06", "description": "FOMC Press Conference"},
    {"date": "2026-06-16", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-06-17", "description": "FOMC Press Conference"},
    {"date": "2026-07-28", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-07-29", "description": "FOMC Press Conference"},
    {"date": "2026-09-15", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-09-16", "description": "FOMC Press Conference"},
    {"date": "2026-11-03", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-11-04", "description": "FOMC Press Conference"},
    {"date": "2026-12-15", "description": "FOMC Meeting - Interest Rate Decision"},
    {"date": "2026-12-16", "description": "FOMC Press Conference"},
]


class EventCalendarFetcher:
    """Fetch and cache financial events."""

    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    def get_upcoming_fomc(self, days: int = 60) -> list:
        """Get upcoming FOMC meetings within specified days."""
        today = datetime.now().date()
        cutoff = today + timedelta(days=days)

        upcoming = []
        for meeting in FOMC_MEETINGS_2026:
            meeting_date = datetime.strptime(meeting["date"], "%Y-%m-%d").date()
            if today <= meeting_date <= cutoff:
                days_until = (meeting_date - today).days
                upcoming.append({
                    **meeting,
                    "days_until": days_until,
                    "type": "fomc",
                })

        return sorted(upcoming, key=lambda x: x["date"])

    async def get_earnings_calendar(self, symbol: str) -> dict:
        """Get upcoming earnings for US stock via Finnhub API."""
        cache_key = f"events:earnings:{symbol.upper()}"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        if not self.settings.finnhub_api_key:
            return {"error": "Finnhub API key not configured"}

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/calendar/earnings",
                    params={
                        "symbol": symbol.upper(),
                        "token": self.settings.finnhub_api_key,
                    }
                )

                if resp.status_code == 403:
                    return {"error": "Finnhub API key invalid or expired"}

                if resp.status_code == 429:
                    return {"error": "Finnhub API rate limit exceeded"}

                resp.raise_for_status()
                data = resp.json()

                earnings = data.get("earningsCalendar", [])
                result = {
                    "symbol": symbol.upper(),
                    "market": "us",
                    "upcoming_earnings": [
                        {
                            "date": e.get("date"),
                            "eps_est": e.get("epsEstimate"),
                            "eps_actual": e.get("epsActual"),
                            "revenue_est": e.get("revenueEstimate"),
                        }
                        for e in earnings[:5]
                    ],
                    "count": len(earnings),
                }

                # Cache for 12 hours
                try:
                    r = await self.get_redis()
                    import json
                    await r.setex(cache_key, self.settings.cache_ttl_events, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Failed to cache earnings: {e}")

                return result

        except ImportError:
            logger.error("httpx not installed")
            return {"error": "httpx not available"}
        except Exception as e:
            logger.error(f"Failed to fetch earnings for {symbol}: {e}")
            return {"error": str(e)}

    async def get_dividend_calendar(self, symbol: str) -> dict:
        """Get upcoming dividends for US stock via Finnhub API."""
        cache_key = f"events:dividends:{symbol.upper()}"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        if not self.settings.finnhub_api_key:
            return {"error": "Finnhub API key not configured"}

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"https://finnhub.io/api/v1/calendar/dividends",
                    params={
                        "symbol": symbol.upper(),
                        "token": self.settings.finnhub_api_key,
                    }
                )

                if resp.status_code in (403, 429):
                    return {"error": "Finnhub API unavailable"}

                resp.raise_for_status()
                data = resp.json()

                dividends = data.get("dividends", [])
                result = {
                    "symbol": symbol.upper(),
                    "upcoming_dividends": [
                        {
                            "date": d.get("date"),
                            "amount": d.get("amount"),
                            "pay_date": d.get("payDate"),
                        }
                        for d in dividends[:5]
                    ],
                }

                # Cache for 12 hours
                try:
                    r = await self.get_redis()
                    import json
                    await r.setex(cache_key, self.settings.cache_ttl_events, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Failed to cache dividends: {e}")

                return result

        except ImportError:
            return {"error": "httpx not available"}
        except Exception as e:
            logger.error(f"Failed to fetch dividends for {symbol}: {e}")
            return {"error": str(e)}

    async def get_ipo_calendar(self) -> dict:
        """Get upcoming IPOs via Finnhub API."""
        cache_key = "events:ipos"

        try:
            r = await self.get_redis()
            cached = await r.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        if not self.settings.finnhub_api_key:
            return {"error": "Finnhub API key not configured"}

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://finnhub.io/api/v1/calendar/ipo",
                    params={
                        "token": self.settings.finnhub_api_key,
                    }
                )

                if resp.status_code in (403, 429):
                    return {"error": "Finnhub API unavailable"}

                resp.raise_for_status()
                data = resp.json()

                ipos = data.get("ipoCalendar", [])
                result = {
                    "upcoming_ipos": [
                        {
                            "name": ipo.get("name"),
                            "date": ipo.get("date"),
                            "exchange": ipo.get("exchange"),
                        }
                        for ipo in ipos[:10]
                    ],
                }

                # Cache for 12 hours
                try:
                    r = await self.get_redis()
                    import json
                    await r.setex(cache_key, self.settings.cache_ttl_events, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Failed to cache IPOs: {e}")

                return result

        except ImportError:
            return {"error": "httpx not available"}
        except Exception as e:
            logger.error(f"Failed to fetch IPOs: {e}")
            return {"error": str(e)}

    async def get_all_events(self, symbol: Optional[str] = None) -> dict:
        """Get all upcoming financial events."""
        events = {
            "fomc": self.get_upcoming_fomc(),
        }

        if symbol:
            events["earnings"] = await self.get_earnings_calendar(symbol)
            events["dividends"] = await self.get_dividend_calendar(symbol)

        events["ipos"] = await self.get_ipo_calendar()

        return events

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance
_event_calendar: Optional[EventCalendarFetcher] = None


def get_event_calendar() -> EventCalendarFetcher:
    """Get or create singleton instance."""
    global _event_calendar
    if _event_calendar is None:
        _event_calendar = EventCalendarFetcher()
    return _event_calendar
