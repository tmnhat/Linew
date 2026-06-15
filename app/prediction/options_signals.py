"""
Options & Derivatives Signals — Put/Call ratio, Implied Volatility.

Sources:
  - yfinance ticker.options → US stocks (FREE, khong can API key)
  - Deribit public API → BTC/ETH options (FREE, khong can API key)

Khong ap dung cho VN stocks (thi truong options VN chua co).

Cache: Redis 2h (options data thay doi intraday nhung khong can realtime)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OPTIONS_CACHE_PREFIX = "linew:options:"
OPTIONS_CACHE_TTL = 7200  # 2 gio


async def get_options_signals(symbol: str, market: str) -> dict:
    """
    Lay options signals cho mot symbol.

    Returns:
        {
          "put_call_ratio": float,         # > 1.2 → fear (contrarian bullish)
          "implied_volatility": float,     # IV% cua ATM options
          "iv_rank": float,               # IV so voi 52-week range (0-100)
          "options_signal": str,           # "BULLISH_HEDGE" / "BEARISH_HEDGE" / "NEUTRAL"
          "interpretation": str,           # Mo ta bang tieng Viet
        }
    """
    if market not in ("us", "crypto"):
        return {}   # VN chua co options market

    # Check cache
    cached = await _get_cache(symbol)
    if cached:
        return cached

    data = {}
    try:
        if market == "us":
            data = await _get_us_options(symbol)
        elif market == "crypto":
            data = await _get_crypto_options(symbol)
    except Exception as e:
        logger.warning(f"Options signals failed for {symbol}: {e}")

    if data:
        await _set_cache(symbol, data)

    return data


async def _get_us_options(symbol: str) -> dict:
    """Lay options data tu yfinance cho US stocks."""
    import asyncio
    import yfinance as yf

    def _fetch():
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return {}

            # Dung expiration gan nhat (1-2 tuan)
            exp = expirations[0] if len(expirations) > 0 else None
            if not exp:
                return {}

            chain = ticker.option_chain(exp)
            calls = chain.calls
            puts  = chain.puts

            if calls.empty or puts.empty:
                return {}

            # Put/Call Volume ratio
            total_call_vol = calls["volume"].fillna(0).sum()
            total_put_vol  = puts["volume"].fillna(0).sum()
            pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 1.0

            # Implied Volatility cua ATM options
            current_price = ticker.fast_info.last_price
            if current_price:
                # Tim strike gan nhat voi current price
                atm_calls = calls.iloc[(calls["strike"] - current_price).abs().argsort()[:3]]
                avg_iv_call = atm_calls["impliedVolatility"].mean()
            else:
                avg_iv_call = calls["impliedVolatility"].median()

            iv_pct = float(avg_iv_call) * 100 if avg_iv_call else None

            # Interpret signal
            signal, interp = _interpret_options_signal(pcr, iv_pct)

            return {
                "put_call_ratio": round(pcr, 2),
                "implied_volatility": round(iv_pct, 1) if iv_pct else None,
                "options_signal": signal,
                "interpretation": interp,
                "_source": "yfinance_options",
            }
        except Exception as e:
            logger.debug(f"yfinance options failed for {symbol}: {e}")
            return {}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)


async def _get_crypto_options(symbol: str) -> dict:
    """
    Lay options data tu Deribit Public API.
    Deribit chi co BTC va ETH options voi thanh khoan du lon.
    """
    import httpx

    # Map symbol → Deribit currency
    sym_clean = symbol.upper().replace("-USD", "").replace("USDT", "")
    if sym_clean not in ("BTC", "ETH"):
        return {}  # Deribit chi co du liquidity cho BTC/ETH

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Lay summary cho tat ca options cua currency
            resp = await client.get(
                "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
                params={"currency": sym_clean, "kind": "option"},
            )
            if resp.status_code != 200:
                return {}

            instruments = resp.json().get("result", [])
            if not instruments:
                return {}

            # Tinh Put/Call ratio tu open interest
            total_call_oi = sum(i.get("open_interest", 0) for i in instruments if "-C" in i.get("instrument_name", ""))
            total_put_oi  = sum(i.get("open_interest", 0) for i in instruments if "-P" in i.get("instrument_name", ""))
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

            # Average IV tu cac ATM options gan nhat
            ivs = [i.get("mark_iv", 0) for i in instruments if i.get("mark_iv") and i.get("mark_iv") > 0]
            avg_iv = sum(ivs) / len(ivs) if ivs else None

            signal, interp = _interpret_options_signal(pcr, avg_iv)

            return {
                "put_call_ratio": round(pcr, 2),
                "implied_volatility": round(avg_iv, 1) if avg_iv else None,
                "options_signal": signal,
                "interpretation": interp,
                "_source": "deribit_public",
            }

    except Exception as e:
        logger.debug(f"Deribit API failed for {symbol}: {e}")

    return {}


def _interpret_options_signal(pcr: Optional[float], iv: Optional[float]) -> tuple[str, str]:
    """Dien giai options signals."""
    signal = "NEUTRAL"
    parts = []

    if pcr is not None:
        if pcr > 1.3:
            signal = "BULLISH_CONTRARIAN"  # Qua nhieu put → contrarian bullish
            parts.append(f"P/C ratio cao ({pcr:.2f}) → thi truong dang mua nhieu put bao hiem, thuong la dau hieu day")
        elif pcr > 1.0:
            parts.append(f"P/C ratio tren 1.0 ({pcr:.2f}) → sentiment hoi phong thu")
        elif pcr < 0.6:
            signal = "BEARISH_CONTRARIAN"  # Qua nhieu call → euphoria → bearish
            parts.append(f"P/C ratio thap ({pcr:.2f}) → thi truong lac quan qua muc, can than dao chieu")
        else:
            parts.append(f"P/C ratio: {pcr:.2f} (binh thuong)")

    if iv is not None:
        if iv > 80:
            parts.append(f"IV rat cao ({iv:.0f}%) → thi truong dang rat so hai, co hoi mua sau khi so giam")
        elif iv > 50:
            parts.append(f"IV cao ({iv:.0f}%) → uncertainty lon, options dat")
        elif iv < 20:
            parts.append(f"IV thap ({iv:.0f}%) → thi truong qua yeu tinh, sap co bien dong")
        else:
            parts.append(f"IV: {iv:.0f}% (binh thuong)")

    interp = " | ".join(parts) if parts else "Khong co du lieu options"
    return signal, interp


async def _get_cache(symbol: str) -> Optional[dict]:
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        cached = await redis.get(f"{OPTIONS_CACHE_PREFIX}{symbol.upper()}")
        return json.loads(cached) if cached else None
    except Exception:
        return None


async def _set_cache(symbol: str, data: dict):
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(f"{OPTIONS_CACHE_PREFIX}{symbol.upper()}", OPTIONS_CACHE_TTL, json.dumps(data, default=str))
    except Exception:
        pass
