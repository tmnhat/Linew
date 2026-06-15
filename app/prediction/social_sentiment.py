"""
Social Sentiment Layer — Lunarcrush (crypto), CryptoPanic.

Sources:
  Crypto:
    - Lunarcrush API: galaxy score, alt rank, social volume, sentiment
      → FREE tier: 100 req/day (du cho ~20 symbols, moi 1h)
      → Dang ky: https://lunarcrush.com/developers
    - CryptoPanic API: aggregated crypto news sentiment
      → FREE tier: unlimited read

Cache: Redis 1h
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)
SOCIAL_CACHE_PREFIX = "linew:social:"
SOCIAL_CACHE_TTL = 3600  # 1 gio


async def get_social_sentiment(symbol: str, market: str) -> dict:
    """
    Lay social sentiment cho mot symbol.

    Returns:
        {
          "social_score": float,      # 0-100 (Lunarcrush galaxy score)
          "sentiment_pct": float,     # % positive mentions
          "social_volume": int,       # So luong post/mentions
          "trending": bool,           # Dang trending khong?
          "sentiment_label": str,     # "Very Bullish" / "Bullish" / "Neutral" / "Bearish"
          "top_headlines": list[str], # Top 3 headlines
          "social_context_str": str,  # Text for AI prompt
        }
    """
    # Check cache
    cached = await _get_cache(symbol)
    if cached:
        return cached

    data = {}
    try:
        if market == "crypto":
            data = await _get_lunarcrush_sentiment(symbol)
            if not data:
                data = await _get_cryptopanic_sentiment(symbol)
        elif market == "us":
            data = await _get_cryptopanic_sentiment(symbol)
    except Exception as e:
        logger.warning(f"Social sentiment failed for {symbol}: {e}")

    if data:
        data["social_context_str"] = _format_social_for_prompt(data, symbol, market)
        await _set_cache(symbol, data)

    return data


async def _get_lunarcrush_sentiment(symbol: str) -> dict:
    """Lay data tu Lunarcrush API (free tier 100 req/day)."""
    from app.config import get_settings
    settings = get_settings()
    api_key = getattr(settings, "lunarcrush_api_key", "")
    if not api_key:
        logger.debug("LUNARCRUSH_API_KEY not set — skipping")
        return {}

    sym_clean = symbol.upper().replace("-USD", "").replace("USDT", "")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://lunarcrush.com/api4/public/coins/{sym_clean.lower()}/v1",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code != 200:
                return {}

            d = resp.json().get("data", {})
            if not d:
                return {}

            galaxy_score = d.get("galaxy_score")      # 0-100
            alt_rank     = d.get("alt_rank")          # Rank trong crypto
            sentiment    = d.get("sentiment")         # 0-5 (bullish/bearish)
            social_vol   = d.get("social_volume_24h")
            social_eng   = d.get("social_engagement_24h")

            # Normalize sentiment 0-5 → 0-100
            sent_pct = (sentiment / 5 * 100) if sentiment else 50

            label = _sentiment_label(sent_pct)
            trending = (alt_rank is not None and alt_rank < 50) or (social_vol and social_vol > 10000)

            return {
                "social_score": galaxy_score,
                "sentiment_pct": round(sent_pct, 1),
                "social_volume": social_vol,
                "alt_rank": alt_rank,
                "trending": trending,
                "sentiment_label": label,
                "_source": "lunarcrush",
            }

    except Exception as e:
        logger.debug(f"Lunarcrush failed for {symbol}: {e}")

    return {}


async def _get_cryptopanic_sentiment(symbol: str) -> dict:
    """
    Lay news sentiment tu CryptoPanic (free, khong can auth cho basic).
    Cun ho tro US stocks (AAPL, TSLA, v.v.)
    """
    sym_clean = symbol.upper().replace("-USD", "").replace("USDT", "")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://cryptopanic.com/api/free/v1/posts/",
                params={
                    "currencies": sym_clean,
                    "filter": "hot",
                    "public": "true",
                },
            )
            if resp.status_code != 200:
                return {}

            posts = resp.json().get("results", [])[:10]
            if not posts:
                return {}

            # Dem votes
            total_pos = sum(p.get("votes", {}).get("positive", 0) for p in posts)
            total_neg = sum(p.get("votes", {}).get("negative", 0) for p in posts)
            total     = total_pos + total_neg

            sent_pct = (total_pos / total * 100) if total > 0 else 50
            label    = _sentiment_label(sent_pct)

            headlines = [p.get("title", "") for p in posts[:3] if p.get("title")]

            return {
                "sentiment_pct": round(sent_pct, 1),
                "social_volume": len(posts),
                "trending": total > 100,
                "sentiment_label": label,
                "top_headlines": headlines,
                "_source": "cryptopanic",
            }

    except Exception as e:
        logger.debug(f"CryptoPanic failed for {symbol}: {e}")

    return {}


def _sentiment_label(pct: float) -> str:
    if pct >= 75: return "Very Bullish"
    elif pct >= 60: return "Bullish"
    elif pct >= 40: return "Neutral"
    elif pct >= 25: return "Bearish"
    else: return "Very Bearish"


def _format_social_for_prompt(data: dict, symbol: str, market: str) -> str:
    lines = [f"SOCIAL SENTIMENT ({symbol}):"]
    label = data.get("sentiment_label", "Neutral")
    pct   = data.get("sentiment_pct")
    vol   = data.get("social_volume")
    score = data.get("social_score")
    trending = data.get("trending", False)

    if score:     lines.append(f"Galaxy Score: {score}/100")
    if pct:       lines.append(f"Positive sentiment: {pct:.0f}% → {label}")
    if vol:       lines.append(f"Social mentions (24h): {vol:,}")
    if trending:  lines.append("Dang TRENDING tren mang xa hoi")

    headlines = data.get("top_headlines", [])
    if headlines:
        lines.append("Top tin:")
        for h in headlines[:2]:
            if h:
                lines.append(f"  - {h[:100]}")

    return "\n".join(lines)


async def _get_cache(symbol: str) -> Optional[dict]:
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        cached = await redis.get(f"{SOCIAL_CACHE_PREFIX}{symbol.upper()}")
        return json.loads(cached) if cached else None
    except Exception:
        return None


async def _set_cache(symbol: str, data: dict):
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(f"{SOCIAL_CACHE_PREFIX}{symbol.upper()}", SOCIAL_CACHE_TTL, json.dumps(data, default=str))
    except Exception:
        pass
