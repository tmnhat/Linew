"""
Multi-timeframe Analysis — lay indicators tu 4h va 1h.

Sources:
  - Crypto: Binance API (interval=4h, 1h) — FREE, khong can API key
  - US stocks: yfinance (interval='1h', period='60d') — FREE

Output:
  {
    "4h": {"rsi": 65.2, "macd_signal": "bearish_cross", "sma20_slope": "up"},
    "1h": {"rsi": 71.3, "overbought": True, "volume_spike": True},
    "mtf_signal": "CAUTION"  # Tong hop signal cross-timeframe
  }
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


async def get_mtf_indicators(
    symbol: str,
    market: str,
) -> dict:
    """
    Fetch va tinh indicators cho 4h va 1h timeframes.

    Returns:
        Dict voi keys "4h", "1h", "mtf_signal", "mtf_context_str"
    """
    result = {"4h": {}, "1h": {}, "mtf_signal": "NEUTRAL", "mtf_context_str": ""}

    if market not in ("crypto", "us"):
        result["mtf_context_str"] = f"{market.upper()} stocks: chi co du lieu daily"
        return result

    try:
        if market == "crypto":
            data_4h = await _fetch_binance_mtf(symbol, "4h", 100)
            data_1h = await _fetch_binance_mtf(symbol, "1h", 48)
        else:  # US stocks
            data_4h = await _fetch_yfinance_mtf(symbol, "1h", "30d")   # yf: 1h = usable as 4h
            data_1h = await _fetch_yfinance_mtf(symbol, "1h", "7d")

        if data_4h:
            result["4h"] = _compute_mtf_indicators(data_4h, label="4h")
        if data_1h:
            result["1h"] = _compute_mtf_indicators(data_1h, label="1h")

        result["mtf_signal"] = _compute_mtf_signal(result["4h"], result["1h"])
        result["mtf_context_str"] = _format_mtf_for_prompt(result)

    except Exception as e:
        logger.warning(f"MTF fetch failed for {symbol}: {e}")

    return result


async def _fetch_binance_mtf(symbol: str, interval: str, limit: int) -> list[dict]:
    """Fetch klines tu Binance Public API (khong can key)."""
    import httpx

    # Normalize symbol
    sym = symbol.upper().replace("-USD", "USDT").replace("-", "")
    if not sym.endswith(("USDT", "BTC", "ETH", "BNB")):
        sym += "USDT"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": sym, "interval": interval, "limit": limit},
            )
            if resp.status_code == 200:
                raw = resp.json()
                return [
                    {
                        "open":   float(k[1]),
                        "high":   float(k[2]),
                        "low":    float(k[3]),
                        "close":  float(k[4]),
                        "volume": float(k[5]),
                    }
                    for k in raw
                ]
    except Exception as e:
        logger.debug(f"Binance MTF {symbol}/{interval} failed: {e}")

    return []


async def _fetch_yfinance_mtf(symbol: str, interval: str, period: str) -> list[dict]:
    """Fetch intraday data tu yfinance."""
    import asyncio
    import yfinance as yf

    def _fetch():
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return []
            return [
                {
                    "open":   float(row["Open"]),
                    "high":   float(row["High"]),
                    "low":    float(row["Low"]),
                    "close":  float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
                for _, row in df.iterrows()
            ]
        except Exception:
            return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)


def _compute_mtf_indicators(candles: list[dict], label: str) -> dict:
    """Tinh RSI, MACD, volume spike cho mot timeframe."""
    if len(candles) < 15:
        return {}

    closes  = [c["close"]  for c in candles]
    volumes = [c["volume"] for c in candles]

    # RSI (14)
    from app.prediction.indicators import calculate_rsi, calculate_macd
    rsi  = calculate_rsi(closes, 14)
    macd_line, macd_sig, macd_hist = calculate_macd(closes)

    # SMA slope (huong SMA20)
    sma20_now  = np.mean(closes[-20:])  if len(closes) >= 20 else None
    sma20_prev = np.mean(closes[-25:-5]) if len(closes) >= 25 else None
    sma_slope  = None
    if sma20_now and sma20_prev and sma20_prev > 0:
        sma_slope = "up" if sma20_now > sma20_prev * 1.001 else ("down" if sma20_now < sma20_prev * 0.999 else "flat")

    # Volume spike (volume > 2x trung binh 20 bars)
    avg_vol    = np.mean(volumes[-20:]) if len(volumes) >= 20 else None
    last_vol   = volumes[-1]
    vol_spike  = (last_vol > avg_vol * 2.0) if avg_vol else False

    # MACD cross signal
    macd_cross = None
    if macd_hist is not None and len(candles) >= 2:
        prev_hist = None
        try:
            _, _, prev_hist = calculate_macd(closes[:-1])
        except Exception:
            pass
        if prev_hist is not None and macd_hist is not None:
            if macd_hist > 0 and prev_hist <= 0:
                macd_cross = "bullish_cross"
            elif macd_hist < 0 and prev_hist >= 0:
                macd_cross = "bearish_cross"

    return {
        "rsi":         round(rsi, 1) if rsi else None,
        "overbought":  rsi > 70 if rsi else False,
        "oversold":    rsi < 30 if rsi else False,
        "macd_hist":   round(macd_hist, 4) if macd_hist else None,
        "macd_cross":  macd_cross,
        "sma20_slope": sma_slope,
        "volume_spike": vol_spike,
    }


def _compute_mtf_signal(tf_4h: dict, tf_1h: dict) -> str:
    """
    Tong hop multi-timeframe signal.
    Returns: "STRONG_BUY" / "BUY" / "NEUTRAL" / "SELL" / "STRONG_SELL" / "CAUTION"
    """
    score = 0

    for tf in [tf_4h, tf_1h]:
        if not tf:
            continue
        rsi = tf.get("rsi")
        if rsi:
            if rsi < 30:   score += 1   # Oversold → bullish
            elif rsi > 70: score -= 1   # Overbought → bearish
        macd = tf.get("macd_cross")
        if macd == "bullish_cross": score += 1
        elif macd == "bearish_cross": score -= 1
        slope = tf.get("sma20_slope")
        if slope == "up":   score += 0.5
        elif slope == "down": score -= 0.5

    # Volume spike them conviction
    if tf_1h.get("volume_spike"):
        score = score * 1.3  # Amplify signal khi co volume

    if score >= 2.5:   return "STRONG_BUY"
    elif score >= 1.0: return "BUY"
    elif score <= -2.5: return "STRONG_SELL"
    elif score <= -1.0: return "SELL"
    elif tf_1h.get("overbought") or tf_4h.get("overbought"): return "CAUTION"
    else:               return "NEUTRAL"


def _format_mtf_for_prompt(mtf: dict) -> str:
    """Format MTF data thanh text cho AI prompt."""
    lines = ["PHAN TICH DA KHUNG THOI GIAN:"]
    sig = mtf.get("mtf_signal", "NEUTRAL")
    lines.append(f"Tong hop signal: {sig}")

    for label in ["4h", "1h"]:
        tf = mtf.get(label, {})
        if not tf:
            continue
        rsi = tf.get("rsi")
        cross = tf.get("macd_cross", "")
        slope = tf.get("sma20_slope", "")
        vol_spike = tf.get("volume_spike", False)

        parts = []
        if rsi:
            obs = " (OVERBOUGHT)" if tf.get("overbought") else (" (OVERSOLD)" if tf.get("oversold") else "")
            parts.append(f"RSI={rsi}{obs}")
        if cross:
            parts.append(f"MACD {cross.replace('_', ' ')}")
        if slope:
            parts.append(f"SMA20 {slope}")
        if vol_spike:
            parts.append("VOLUME SPIKE")

        if parts:
            lines.append(f"  [{label.upper()}] {' | '.join(parts)}")

    return "\n".join(lines)
