"""
Market Regime Detector — phan loai trang thai thi truong.

Regimes:
  - TRENDING_UP:   ADX > 25, gia tren SMA50. TrendAgent quan trong nhat.
  - TRENDING_DOWN: ADX > 25, gia duoi SMA50. MacroAgent + SentimentAgent quan trong.
  - SIDEWAYS:      ADX < 20. ValueAgent quan trong nhat, tranh false breakout.
  - VOLATILE:      ATR% > 3%. Tat ca threshold tang (yeu cau conviction cao hon).

Cong thuc ADX (Average Directional Index):
  - Dua tren Wilder's smoothing cua +DM/-DM
  - ADX > 25 = trending, < 20 = ranging/sideways
"""
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class MarketRegime:
    TRENDING_UP   = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    SIDEWAYS      = "SIDEWAYS"
    VOLATILE      = "VOLATILE"


def calculate_adx(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> Optional[float]:
    """
    Tinh Average Directional Index (ADX) — Wilder's method.
    ADX > 25: trending market
    ADX < 20: ranging/sideways
    """
    if len(highs) < period * 2 + 1:
        return None

    try:
        highs  = np.array(highs, dtype=float)
        lows   = np.array(lows,  dtype=float)
        closes = np.array(closes, dtype=float)

        n = len(closes)
        plus_dm  = np.zeros(n)
        minus_dm = np.zeros(n)
        tr       = np.zeros(n)

        for i in range(1, n):
            h_diff = highs[i]  - highs[i-1]
            l_diff = lows[i-1] - lows[i]

            plus_dm[i]  = h_diff if (h_diff > l_diff and h_diff > 0) else 0.0
            minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0.0

            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i]  - closes[i-1]),
                abs(lows[i]   - closes[i-1]),
            )

        # Wilder's smoothing
        def wilder_smooth(arr, p):
            s = np.zeros(len(arr))
            s[p] = np.sum(arr[1:p+1])
            for i in range(p+1, len(arr)):
                s[i] = s[i-1] - s[i-1]/p + arr[i]
            return s

        atr_smooth  = wilder_smooth(tr,       period)
        pdm_smooth  = wilder_smooth(plus_dm,  period)
        mdm_smooth  = wilder_smooth(minus_dm, period)

        # +DI, -DI
        pdi = np.where(atr_smooth > 0, 100 * pdm_smooth / atr_smooth, 0)
        mdi = np.where(atr_smooth > 0, 100 * mdm_smooth / atr_smooth, 0)

        # DX and ADX
        dx_denom = pdi + mdi
        dx = np.where(dx_denom > 0, 100 * np.abs(pdi - mdi) / dx_denom, 0)

        adx = np.zeros(n)
        adx[period*2] = np.mean(dx[period:period*2+1])
        for i in range(period*2+1, n):
            adx[i] = (adx[i-1] * (period-1) + dx[i]) / period

        return float(adx[-1])

    except Exception as e:
        logger.warning(f"ADX calculation failed: {e}")
        return None


def detect_regime(
    indicators: dict,
    highs: list[float] = None,
    lows: list[float]  = None,
    closes: list[float] = None,
) -> dict:
    """
    Phat hien market regime tu indicators hien tai.

    Args:
        indicators: Dict chua RSI, MACD, ATR, SMA50, SMA200, v.v.
        highs/lows/closes: Raw OHLC data de tinh ADX (optional)

    Returns:
        {
          "regime": "TRENDING_UP" | "TRENDING_DOWN" | "SIDEWAYS" | "VOLATILE",
          "adx": float,
          "atr_pct": float,
          "description": str,
          "weight_adjustments": dict,  # Dieu chinh weights cho tung agent
          "signal_threshold": float,   # BUY/SELL threshold cho regime nay
        }
    """
    result = {
        "regime": MarketRegime.SIDEWAYS,
        "adx": None,
        "atr_pct": None,
        "description": "Thi truong dang di ngang, cho tin hieu ro hon",
        "weight_adjustments": {},
        "signal_threshold": 0.35,
    }

    # Tinh ATR% (ATR / current_price)
    atr = indicators.get("atr_14")
    current_price = indicators.get("current_price")
    sma50 = indicators.get("sma_50")

    if atr and current_price and current_price > 0:
        atr_pct = (atr / current_price) * 100
        result["atr_pct"] = round(atr_pct, 2)

        # VOLATILE: ATR > 3% cua gia
        if atr_pct > 3.0:
            result["regime"] = MarketRegime.VOLATILE
            result["description"] = f"Thi truong bien dong cao (ATR={atr_pct:.1f}%) — can confidence cao hon"
            result["signal_threshold"] = 0.50  # Can conviction cao hon trong volatile
            result["weight_adjustments"] = {
                "macro":     +0.05,   # MacroAgent quan trong hon trong volatile
                "sentiment": +0.03,
                "trend":     -0.05,   # Trend signal it tin cay trong volatile
                "value":     -0.03,
            }
            return result

    # Tinh ADX neu co raw data
    adx = None
    if highs and lows and closes and len(closes) >= 30:
        adx = calculate_adx(highs, lows, closes)
        result["adx"] = round(adx, 1) if adx else None

    # Fallback: estimate ADX tu MACD histogram variance
    if adx is None:
        macd_hist = indicators.get("macd_histogram")
        rsi = indicators.get("rsi_14")
        if macd_hist is not None and rsi is not None:
            # Heuristic: strong MACD + RSI far from 50 → likely trending
            rsi_deviation = abs(rsi - 50)
            if rsi_deviation > 20 and abs(macd_hist) > 0:
                adx = 28.0  # Estimate: trending
            else:
                adx = 18.0  # Estimate: sideways

    # Classify regime bang ADX
    if adx is not None:
        if adx >= 25:
            # TRENDING — xac dinh huong bang SMA50
            price_above_sma50 = (current_price > sma50) if (current_price and sma50) else None

            if price_above_sma50 is True:
                result["regime"] = MarketRegime.TRENDING_UP
                result["description"] = f"Xu huong TANG manh (ADX={adx:.0f}) — momentum signal dang tin cay"
                result["signal_threshold"] = 0.25   # De trigger BUY hon trong uptrend
                result["weight_adjustments"] = {
                    "trend":     +0.10,  # TrendAgent lead
                    "macro":     +0.03,
                    "value":     -0.08,  # Value it quan trong trong uptrend
                    "sentiment": -0.03,
                    "onchain":   -0.02,
                }
            elif price_above_sma50 is False:
                result["regime"] = MarketRegime.TRENDING_DOWN
                result["description"] = f"Xu huong GIAM (ADX={adx:.0f}) — can than trong voi tin hieu BUY"
                result["signal_threshold"] = 0.45   # Can conviction cao hon de vao BUY trong downtrend
                result["weight_adjustments"] = {
                    "macro":     +0.08,  # MacroAgent: lieu macro co ho tro reversal?
                    "sentiment": +0.05,  # SentimentAgent: fear extreme?
                    "trend":     -0.05,
                    "value":     -0.05,
                    "onchain":   -0.03,
                }
            else:
                result["regime"] = MarketRegime.TRENDING_UP
                result["description"] = f"Trending (ADX={adx:.0f})"
                result["signal_threshold"] = 0.30

        else:  # ADX < 25 → SIDEWAYS
            result["regime"] = MarketRegime.SIDEWAYS
            result["description"] = f"Thi truong di ngang (ADX={adx:.0f}) — tranh fake breakout"
            result["signal_threshold"] = 0.40   # Can conviction cao hon de tranh noise
            result["weight_adjustments"] = {
                "value":     +0.08,  # ValueAgent lead: mua khi re, ban khi dat
                "macro":     +0.05,
                "trend":     -0.08,  # TrendAgent it tin cay trong sideways
                "sentiment": -0.03,
                "onchain":   -0.02,
            }

    return result


def apply_regime_to_weights(base_weights: dict, regime_info: dict) -> dict:
    """
    Ap dung regime weight adjustments len base weights.
    Dam bao tong luon = 1.0 va moi weight >= 0.05.
    """
    adjustments = regime_info.get("weight_adjustments", {})
    if not adjustments:
        return base_weights

    adjusted = dict(base_weights)
    for agent, delta in adjustments.items():
        if agent in adjusted:
            adjusted[agent] = max(0.05, adjusted[agent] + delta)

    # Re-normalize
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: round(v / total, 4) for k, v in adjusted.items()}

    return adjusted
