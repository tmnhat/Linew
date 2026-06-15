"""
Cross-Asset Correlation Engine.

Muc tieu:
  1. Altcoins ↔ BTC: BTC pump → alts pump sau 2-24h, BTC dump → alts dump manh hon
  2. US stocks ↔ S&P500: correlation voi market leader

Cache: Redis 6h (correlation matrix khong can cap nhat thuong xuyen)
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)
CORR_CACHE_PREFIX = "linew:correlation:"
CORR_CACHE_TTL = 6 * 3600  # 6 gio


async def get_correlation_context(symbol: str, market: str) -> dict:
    """
    Lay correlation context cho mot symbol.

    Returns:
        {
          "lead_asset": str,              # Tai san leading (BTC, SPY)
          "lead_asset_return_1d": float,  # Return cua lead asset hom nay
          "correlation_30d": float,       # Correlation coefficient
          "predicted_impact_pct": float,  # Du kien impact len symbol hom nay
          "context_str": str,             # Text for AI prompt
        }
    """
    cached = await _get_cache(symbol)
    if cached:
        return cached

    data = {}
    try:
        if market == "crypto":
            data = await _get_crypto_btc_correlation(symbol)
        elif market == "us":
            data = await _get_us_spy_correlation(symbol)
    except Exception as e:
        logger.warning(f"Correlation failed for {symbol}: {e}")

    if data:
        data["context_str"] = _format_corr_for_prompt(data, symbol, market)
        await _set_cache(symbol, data)

    return data


async def _get_us_spy_correlation(symbol: str) -> dict:
    """
    US stocks: tinh correlation voi S&P500 (SPY).
    S&P500 la leading asset cho US stock market.
    """
    import asyncio
    import yfinance as yf
    import pandas as pd

    def _fetch():
        try:
            # Lay symbol va SPY prices trong 60 ngay
            spy  = yf.Ticker("SPY").history(period="60d")["Close"]
            stock = yf.Ticker(symbol).history(period="60d")["Close"]

            if spy.empty or stock.empty or len(spy) < 20:
                return {}

            # Align dates
            combined = pd.DataFrame({"spy": spy, "stock": stock}).dropna()

            if len(combined) < 20:
                return {}

            # Return series
            spy_ret  = combined["spy"].pct_change().dropna()
            stock_ret = combined["stock"].pct_change().dropna()

            # Rolling 30d correlation
            corr_df = pd.DataFrame({"spy": spy_ret, "stock": stock_ret}).dropna()
            corr_val = corr_df["spy"].corr(corr_df["stock"]) if len(corr_df) >= 10 else 0

            # SPY return hom nay
            spy_today = float(spy_ret.iloc[-1]) * 100  # Convert to %

            # Predicted impact: corr * spy_return
            predicted_impact = corr_val * spy_today

            # SPY 24h trend
            spy_trend = "UP" if spy_today > 1 else ("DOWN" if spy_today < -1 else "FLAT")

            return {
                "lead_asset": "SPY",
                "lead_asset_return_1d": round(spy_today, 2),
                "spy_trend": spy_trend,
                "correlation_30d": round(float(corr_val), 2),
                "predicted_impact_pct": round(predicted_impact, 2),
            }
        except Exception as e:
            logger.debug(f"US stock correlation fetch failed: {e}")
            return {}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)


async def _get_crypto_btc_correlation(symbol: str) -> dict:
    """
    Altcoins: tinh correlation voi BTC trong 30 ngay.
    BTC la leading asset cho toan bo crypto market.
    """
    sym_clean = symbol.upper().replace("-USD", "").replace("USDT", "")
    if sym_clean == "BTC":
        return {}  # BTC khong can so sanh voi chinh no

    import asyncio
    import yfinance as yf
    import pandas as pd

    def _fetch():
        try:
            btc  = yf.Ticker("BTC-USD").history(period="60d")["Close"]
            coin = yf.Ticker(f"{sym_clean}-USD").history(period="60d")["Close"]

            if btc.empty or coin.empty or len(btc) < 20:
                return {}

            combined = pd.DataFrame({"btc": btc, "coin": coin}).dropna()
            if len(combined) < 15:
                return {}

            btc_ret  = combined["btc"].pct_change().dropna()
            coin_ret = combined["coin"].pct_change().dropna()

            corr_df = pd.DataFrame({"btc": btc_ret, "coin": coin_ret}).dropna()
            corr_val = corr_df["btc"].corr(corr_df["coin"]) if len(corr_df) >= 10 else 0

            btc_return_1d = float(btc_ret.iloc[-1]) * 100
            predicted_impact = corr_val * btc_return_1d

            # BTC 24h trend
            btc_24h = btc_return_1d
            btc_trend = "PUMP" if btc_24h > 2 else ("DUMP" if btc_24h < -2 else "FLAT")

            return {
                "lead_asset": "BTC",
                "lead_asset_return_1d": round(btc_24h, 2),
                "btc_trend": btc_trend,
                "correlation_30d": round(float(corr_val), 2),
                "predicted_impact_pct": round(predicted_impact, 2),
            }
        except Exception as e:
            logger.debug(f"Crypto correlation fetch failed: {e}")
            return {}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)


def _format_corr_for_prompt(data: dict, symbol: str, market: str) -> str:
    lead = data.get("lead_asset", "")
    lead_ret = data.get("lead_asset_return_1d")
    corr = data.get("correlation_30d")
    impact = data.get("predicted_impact_pct")

    lines = [f"TUONG QUAN VOI {lead}:"]
    if lead_ret is not None:
        direction = "tang" if lead_ret > 0 else "giam"
        lines.append(f"{lead} ngay qua: {lead_ret:+.1f}% ({direction})")
    if corr is not None:
        strength = "cao" if abs(corr) > 0.7 else ("trung binh" if abs(corr) > 0.4 else "thap")
        lines.append(f"Tuong quan 30 ngay: {corr:.2f} ({strength})")
    if impact is not None:
        lines.append(f"Du bao tac dong hom nay: {impact:+.1f}% (dua tren tuong quan)")

    btc_trend = data.get("btc_trend") or data.get("spy_trend")
    if btc_trend:
        lines.append(f"{lead} trend: {btc_trend}")

    return "\n".join(lines)


async def _get_cache(symbol: str) -> Optional[dict]:
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        d = await redis.get(f"{CORR_CACHE_PREFIX}{symbol.upper()}")
        return json.loads(d) if d else None
    except Exception:
        return None


async def _set_cache(symbol: str, data: dict):
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(f"{CORR_CACHE_PREFIX}{symbol.upper()}", CORR_CACHE_TTL, json.dumps(data, default=str))
    except Exception:
        pass
