"""
Technical indicators calculator.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index (RSI).
    """
    if len(prices) < period + 1:
        return None

    try:
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    except Exception as e:
        logger.warning(f"RSI calculation failed: {e}")
        return None


def calculate_macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Calculate MACD, Signal line, and Histogram.
    Returns: (macd_line, signal_line, histogram)
    """
    if len(prices) < slow + signal:
        return None, None, None

    try:
        prices_series = pd.Series(prices)
        ema_fast = prices_series.ewm(span=fast, adjust=False).mean()
        ema_slow = prices_series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return (
            float(macd_line.iloc[-1]),
            float(signal_line.iloc[-1]),
            float(histogram.iloc[-1]),
        )
    except Exception as e:
        logger.warning(f"MACD calculation failed: {e}")
        return None, None, None


def calculate_bollinger_bands(
    prices: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Calculate Bollinger Bands.
    Returns: (upper_band, middle_band, lower_band)
    """
    if len(prices) < period:
        return None, None, None

    try:
        recent_prices = prices[-period:]
        middle_band = np.mean(recent_prices)
        std_dev = np.std(recent_prices)

        upper_band = middle_band + (num_std * std_dev)
        lower_band = middle_band - (num_std * std_dev)

        return float(upper_band), float(middle_band), float(lower_band)
    except Exception as e:
        logger.warning(f"Bollinger Bands calculation failed: {e}")
        return None, None, None


def calculate_atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> Optional[float]:
    """
    Calculate Average True Range (ATR).
    """
    if len(closes) < period + 1:
        return None

    try:
        high_low = np.array(highs) - np.array(lows)
        high_close = np.abs(np.array(highs[1:]) - np.array(closes[:-1]))
        low_close = np.abs(np.array(lows[1:]) - np.array(closes[:-1]))

        true_ranges = np.maximum(high_low[1:], np.maximum(high_close, low_close))

        atr = np.mean(true_ranges[-period:])
        return float(atr)
    except Exception as e:
        logger.warning(f"ATR calculation failed: {e}")
        return None


def calculate_sma(prices: list[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return None
    try:
        return float(np.mean(prices[-period:]))
    except Exception as e:
        logger.warning(f"SMA calculation failed: {e}")
        return None


def calculate_ema(prices: list[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return None
    try:
        prices_series = pd.Series(prices)
        ema = prices_series.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])
    except Exception as e:
        logger.warning(f"EMA calculation failed: {e}")
        return None


def calculate_all_indicators(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[int],
) -> dict:
    """
    Calculate all technical indicators for the given data.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of close prices
        volumes: List of volumes

    Returns:
        Dictionary with all calculated indicators
    """
    indicators = {
        "rsi_14": calculate_rsi(closes, 14),
        "macd_line": None,
        "macd_signal": None,
        "macd_histogram": None,
        "bb_upper": None,
        "bb_middle": None,
        "bb_lower": None,
        "sma_20": calculate_sma(closes, 20),
        "sma_50": calculate_sma(closes, 50),
        "sma_200": calculate_sma(closes, 200),
        "ema_12": calculate_ema(closes, 12),
        "ema_26": calculate_ema(closes, 26),
        "atr_14": calculate_atr(highs, lows, closes, 14),
        "volume": volumes[-1] if volumes else None,
        "volume_sma_20": calculate_sma([float(v) for v in volumes], 20) if len(volumes) >= 20 else None,
    }

    macd_result = calculate_macd(closes)
    indicators["macd_line"] = macd_result[0]
    indicators["macd_signal"] = macd_result[1]
    indicators["macd_histogram"] = macd_result[2]

    bb_result = calculate_bollinger_bands(closes)
    indicators["bb_upper"] = bb_result[0]
    indicators["bb_middle"] = bb_result[1]
    indicators["bb_lower"] = bb_result[2]

    return indicators


async def save_indicators(
    session,
    symbol: str,
    indicators: dict,
) -> bool:
    """
    Save technical indicators to database.
    """
    from app.models.prediction_models import TechnicalIndicator
    from sqlalchemy.dialects.postgresql import insert
    from datetime import date

    try:
        today = date.today()

        stmt = insert(TechnicalIndicator).values(
            symbol=symbol,
            date=today,
            rsi_14=Decimal(str(indicators["rsi_14"])) if indicators.get("rsi_14") else None,
            macd_line=Decimal(str(indicators["macd_line"])) if indicators.get("macd_line") else None,
            macd_signal=Decimal(str(indicators["macd_signal"])) if indicators.get("macd_signal") else None,
            macd_histogram=Decimal(str(indicators["macd_histogram"])) if indicators.get("macd_histogram") else None,
            bb_upper=Decimal(str(indicators["bb_upper"])) if indicators.get("bb_upper") else None,
            bb_middle=Decimal(str(indicators["bb_middle"])) if indicators.get("bb_middle") else None,
            bb_lower=Decimal(str(indicators["bb_lower"])) if indicators.get("bb_lower") else None,
            sma_20=Decimal(str(indicators["sma_20"])) if indicators.get("sma_20") else None,
            sma_50=Decimal(str(indicators["sma_50"])) if indicators.get("sma_50") else None,
            sma_200=Decimal(str(indicators["sma_200"])) if indicators.get("sma_200") else None,
            ema_12=Decimal(str(indicators["ema_12"])) if indicators.get("ema_12") else None,
            ema_26=Decimal(str(indicators["ema_26"])) if indicators.get("ema_26") else None,
            atr_14=Decimal(str(indicators["atr_14"])) if indicators.get("atr_14") else None,
            volume=indicators.get("volume"),
            volume_sma_20=Decimal(str(indicators["volume_sma_20"])) if indicators.get("volume_sma_20") else None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "rsi_14": stmt.excluded.rsi_14,
                "macd_line": stmt.excluded.macd_line,
                "macd_signal": stmt.excluded.macd_signal,
                "macd_histogram": stmt.excluded.macd_histogram,
                "bb_upper": stmt.excluded.bb_upper,
                "bb_middle": stmt.excluded.bb_middle,
                "bb_lower": stmt.excluded.bb_lower,
                "sma_20": stmt.excluded.sma_20,
                "sma_50": stmt.excluded.sma_50,
                "sma_200": stmt.excluded.sma_200,
                "ema_12": stmt.excluded.ema_12,
                "ema_26": stmt.excluded.ema_26,
                "atr_14": stmt.excluded.atr_14,
                "volume": stmt.excluded.volume,
                "volume_sma_20": stmt.excluded.volume_sma_20,
            }
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Saved indicators for {symbol}")
        return True
    except Exception as e:
        logger.error(f"Failed to save indicators for {symbol}: {e}")
        return False


def get_technical_signals(indicators: dict) -> dict:
    """
    Generate trading signals based on technical indicators.
    """
    signals = {
        "rsi_signal": "neutral",
        "macd_signal": "neutral",
        "bb_signal": "neutral",
        "trend_signal": "neutral",
        "overall_signal": "neutral",
    }

    if indicators.get("rsi_14"):
        rsi = indicators["rsi_14"]
        if rsi < 30:
            signals["rsi_signal"] = "oversold"
        elif rsi > 70:
            signals["rsi_signal"] = "overbought"

    if indicators.get("macd_histogram") and indicators.get("macd_signal"):
        if indicators["macd_histogram"] > indicators["macd_signal"]:
            signals["macd_signal"] = "bullish"
        elif indicators["macd_histogram"] < indicators["macd_signal"]:
            signals["macd_signal"] = "bearish"

    if indicators.get("bb_upper") and indicators.get("bb_lower"):
        price = indicators.get("sma_20")
        if price:
            bb_upper = indicators["bb_upper"]
            bb_lower = indicators["bb_lower"]
            if price <= bb_lower:
                signals["bb_signal"] = "oversold"
            elif price >= bb_upper:
                signals["bb_signal"] = "overbought"

    if indicators.get("sma_20") and indicators.get("sma_50"):
        if indicators["sma_20"] > indicators["sma_50"]:
            signals["trend_signal"] = "bullish"
        elif indicators["sma_20"] < indicators["sma_50"]:
            signals["trend_signal"] = "bearish"

    bullish_count = sum([
        signals["rsi_signal"] == "oversold",
        signals["macd_signal"] == "bullish",
        signals["trend_signal"] == "bullish",
    ])
    bearish_count = sum([
        signals["rsi_signal"] == "overbought",
        signals["macd_signal"] == "bearish",
        signals["trend_signal"] == "bearish",
    ])

    if bullish_count >= 2:
        signals["overall_signal"] = "bullish"
    elif bearish_count >= 2:
        signals["overall_signal"] = "bearish"

    return signals
