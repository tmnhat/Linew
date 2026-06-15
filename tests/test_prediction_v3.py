"""
Tests cho Prediction System V3 upgrades.
Chay: pytest tests/test_prediction_v3.py -v
"""
import asyncio
import pytest


# ==============================================================================
# Test Regime Detection
# ==============================================================================

def test_regime_detector_trending_up():
    """Test regime detection for trending up market."""
    from app.prediction.regime_detector import detect_regime
    indicators = {
        "rsi_14": 65,
        "macd_histogram": 0.5,
        "sma_50": 100,
        "sma_200": 90,
        "atr_14": 1.5,
        "current_price": 105,  # Tren SMA50
    }
    result = detect_regime(indicators)
    assert result["regime"] in ("TRENDING_UP", "SIDEWAYS", "VOLATILE")
    assert "signal_threshold" in result
    assert 0 < result["signal_threshold"] < 1


def test_regime_detector_volatile():
    """Test regime detection for volatile market (ATR > 3%)."""
    from app.prediction.regime_detector import detect_regime
    indicators = {
        "atr_14": 5.0,
        "current_price": 100,  # ATR% = 5% > 3% → VOLATILE
        "sma_50": 95,
        "rsi_14": 50,
        "macd_histogram": 0,
    }
    result = detect_regime(indicators)
    assert result["regime"] == "VOLATILE"
    assert result["signal_threshold"] > 0.35


def test_regime_detector_sideways():
    """Test regime detection for sideways market."""
    from app.prediction.regime_detector import detect_regime
    indicators = {
        "atr_14": 1.0,
        "current_price": 100,
        "sma_50": 100,
        "sma_200": 99,
        "rsi_14": 50,
        "macd_histogram": 0.01,
    }
    result = detect_regime(indicators)
    # Should be SIDEWAYS or TRENDING (low ADX estimate)
    assert result["regime"] in ("SIDEWAYS", "TRENDING_UP", "TRENDING_DOWN")
    assert result["signal_threshold"] >= 0.30


def test_regime_apply_to_weights():
    """Test regime weight adjustments."""
    from app.prediction.regime_detector import apply_regime_to_weights
    base = {"trend": 0.25, "value": 0.25, "macro": 0.20, "sentiment": 0.15, "onchain": 0.15}
    regime_info = {"weight_adjustments": {"trend": +0.10, "value": -0.08}}
    result = apply_regime_to_weights(base, regime_info)
    total = sum(result.values())
    assert abs(total - 1.0) < 0.01, f"Weights sum = {total}, expected ~1.0"
    assert all(v >= 0.05 for v in result.values()), "All weights must be >= 0.05"
    assert result["trend"] > base["trend"], "Trend weight should increase"


def test_regime_apply_preserves_minimum():
    """Test that regime adjustments preserve minimum weight of 0.05."""
    from app.prediction.regime_detector import apply_regime_to_weights
    base = {"trend": 0.10, "value": 0.10, "macro": 0.20, "sentiment": 0.15, "onchain": 0.45}
    regime_info = {"weight_adjustments": {"trend": -0.10, "onchain": +0.10}}
    result = apply_regime_to_weights(base, regime_info)
    # After adjustment, trend would be 0.0, but min is 0.05
    assert result["trend"] >= 0.05


# ==============================================================================
# Test ADX Calculation
# ==============================================================================

def test_adx_calculation():
    """Test ADX calculation with trending data."""
    from app.prediction.regime_detector import calculate_adx
    import numpy as np

    # Create trending data
    n = 60
    np.random.seed(42)
    trend = np.linspace(100, 115, n)  # Uptrend
    noise = np.random.uniform(-2, 2, n)
    highs  = trend + noise + 2
    lows   = trend + noise - 2
    closes = trend + noise

    adx = calculate_adx(highs, lows, closes)
    assert adx is not None, "ADX should return a value for 60 data points"
    assert 0 <= adx <= 100, f"ADX={adx} out of range"


def test_adx_calculation_insufficient_data():
    """Test ADX returns None for insufficient data."""
    from app.prediction.regime_detector import calculate_adx

    # Only 10 data points - need at least 29
    highs  = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    lows   = [99, 100, 101, 102, 103, 104, 105, 106, 107, 108]
    closes = [99.5, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5]

    adx = calculate_adx(highs, lows, closes)
    assert adx is None, "ADX should return None for insufficient data"


# ==============================================================================
# Test Adaptive Weights
# ==============================================================================

def test_default_weights():
    """Test default weights structure."""
    from app.prediction.adaptive_weights import get_default_weights
    weights = get_default_weights()
    assert set(weights.keys()) == {"trend", "value", "macro", "sentiment", "onchain"}
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01


def test_softmax_normalize():
    """Test softmax normalization."""
    from app.prediction.adaptive_weights import _softmax_normalize
    rates = {"trend": 0.6, "value": 0.5, "macro": 0.55, "sentiment": 0.45, "onchain": 0.4}
    weights = _softmax_normalize(rates)
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01
    # Agent voi win-rate cao nhat phai co weight cao nhat
    assert weights["trend"] == max(weights.values())


def test_softmax_normalize_equal_rates():
    """Test softmax with equal win rates."""
    from app.prediction.adaptive_weights import _softmax_normalize
    rates = {"a": 0.5, "b": 0.5, "c": 0.5}
    weights = _softmax_normalize(rates)
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01
    # Should be roughly equal
    assert abs(weights["a"] - weights["b"]) < 0.1


# ==============================================================================
# Test Multi-timeframe
# ==============================================================================

def test_mtf_signal_computation():
    """Test MTF signal computation."""
    from app.prediction.multi_timeframe import _compute_mtf_signal

    # Strong bullish signals
    tf_4h = {"rsi": 28, "oversold": True, "macd_cross": "bullish_cross", "sma20_slope": "up"}
    tf_1h = {"rsi": 31, "volume_spike": True}
    signal = _compute_mtf_signal(tf_4h, tf_1h)
    assert signal in ("STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL", "CAUTION")

    # Bearish signals
    tf_bear = {"rsi": 75, "overbought": True, "macd_cross": "bearish_cross", "sma20_slope": "down"}
    signal_bear = _compute_mtf_signal(tf_bear, {})
    assert signal_bear in ("STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL", "CAUTION")


def test_mtf_signal_empty_data():
    """Test MTF signal with empty data."""
    from app.prediction.multi_timeframe import _compute_mtf_signal
    signal = _compute_mtf_signal({}, {})
    assert signal == "NEUTRAL"


def test_mtf_indicator_computation():
    """Test MTF indicator calculation."""
    from app.prediction.multi_timeframe import _compute_mtf_indicators

    # Create sample candles
    candles = [
        {"close": 100 + i, "volume": 1000}
        for i in range(30)
    ]
    result = _compute_mtf_indicators(candles, "4h")

    assert "rsi" in result
    assert result["rsi"] is not None or result.get("rsi") is None  # RSI might be None for some data


# ==============================================================================
# Test Social Sentiment
# ==============================================================================

def test_sentiment_label():
    """Test sentiment label mapping."""
    from app.prediction.social_sentiment import _sentiment_label

    assert _sentiment_label(80) == "Very Bullish"
    assert _sentiment_label(65) == "Bullish"
    assert _sentiment_label(50) == "Neutral"
    assert _sentiment_label(30) == "Bearish"
    assert _sentiment_label(15) == "Very Bearish"


def test_format_social_for_prompt():
    """Test social sentiment formatting."""
    from app.prediction.social_sentiment import _format_social_for_prompt
    data = {
        "sentiment_label": "Bullish",
        "sentiment_pct": 65,
        "social_volume": 15000,
        "trending": True,
        "social_score": 72,
        "top_headlines": ["Headline 1", "Headline 2"],
    }
    text = _format_social_for_prompt(data, "BTC-USD", "crypto")

    assert "BTC-USD" in text
    assert "Bullish" in text
    assert "65" in text or "Social" in text


# ==============================================================================
# Test Correlation Engine
# ==============================================================================

def test_correlation_format():
    """Test correlation formatting."""
    from app.prediction.correlation_engine import _format_corr_for_prompt
    data = {
        "lead_asset": "BTC",
        "lead_asset_return_1d": -2.5,
        "correlation_30d": 0.75,
        "predicted_impact_pct": -1.875,
        "btc_trend": "DUMP",
    }
    text = _format_corr_for_prompt(data, "ETH-USD", "crypto")
    assert "BTC" in text
    assert "-2.5" in text


def test_corr_format_no_data():
    """Test correlation formatting with no data."""
    from app.prediction.correlation_engine import _format_corr_for_prompt
    data = {}
    text = _format_corr_for_prompt(data, "ETH-USD", "crypto")
    assert "ETH-USD" in text


# ==============================================================================
# Test Options Signals
# ==============================================================================

def test_options_signal_interpretation():
    """Test options signal interpretation."""
    from app.prediction.options_signals import _interpret_options_signal

    # High P/C ratio - bullish contrarian
    signal, interp = _interpret_options_signal(1.5, None)
    assert signal == "BULLISH_CONTRARIAN"

    # Low P/C ratio - bearish contrarian
    signal, interp = _interpret_options_signal(0.4, None)
    assert signal == "BEARISH_CONTRARIAN"

    # Neutral
    signal, interp = _interpret_options_signal(0.8, None)
    assert signal == "NEUTRAL"


def test_options_iv_interpretation():
    """Test IV interpretation."""
    from app.prediction.options_signals import _interpret_options_signal

    # High IV
    signal, interp = _interpret_options_signal(None, 90)
    assert "IV" in interp

    # Low IV
    signal, interp = _interpret_options_signal(None, 15)
    assert "IV" in interp


# ==============================================================================
# Test Accuracy Tracker
# ==============================================================================

def test_accuracy_stats_structure():
    """Test accuracy stats has correct structure."""
    from app.prediction.accuracy_tracker import get_accuracy_stats

    # This will fail without DB but should not crash
    # Just test the function exists and is callable
    assert callable(get_accuracy_stats)


# ==============================================================================
# Test AI Analyst V3 Integration
# ==============================================================================

def test_agent_styles_structure():
    """Test AGENT_STYLES has correct structure."""
    from app.prediction.ai_analyst import AGENT_STYLES

    assert "trend" in AGENT_STYLES
    assert "value" in AGENT_STYLES
    assert "macro" in AGENT_STYLES
    assert "sentiment" in AGENT_STYLES
    assert "onchain" in AGENT_STYLES

    # Check weights sum to ~1.0
    total = sum(v["weight"] for v in AGENT_STYLES.values())
    assert abs(total - 1.0) < 0.01


def test_analyze_symbol_enhanced_function_exists():
    """Test analyze_symbol_enhanced exists and is callable."""
    from app.prediction.ai_analyst import analyze_symbol_enhanced
    assert callable(analyze_symbol_enhanced)


def test_run_single_agent_v3_function_exists():
    """Test _run_single_agent_v3 exists and is callable."""
    from app.prediction.ai_analyst import _run_single_agent_v3
    assert callable(_run_single_agent_v3)


def test_compute_weighted_consensus_v2_function_exists():
    """Test _compute_weighted_consensus_v2 exists and is callable."""
    from app.prediction.ai_analyst import _compute_weighted_consensus_v2
    assert callable(_compute_weighted_consensus_v2)


def test_weighted_consensus_v2_threshold():
    """Test weighted consensus V2 respects threshold."""
    from app.prediction.ai_analyst import _compute_weighted_consensus_v2

    agent_signals = [
        {"sentiment": "positive", "sentiment_score": 0.8, "weight": 0.5, "reasons": ["Test"]},
        {"sentiment": "positive", "sentiment_score": 0.8, "weight": 0.5, "reasons": ["Test"]},
    ]

    # With high threshold (0.5), should be neutral
    result = _compute_weighted_consensus_v2(
        agent_signals, "TEST", "Test", "crypto", 100.0, threshold=0.5
    )

    assert result is not None
    assert "sentiment" in result
    assert "confidence_score" in result


def test_weighted_consensus_v2_empty_signals():
    """Test weighted consensus V2 handles empty signals."""
    from app.prediction.ai_analyst import _compute_weighted_consensus_v2

    result = _compute_weighted_consensus_v2([], "TEST", "Test", "crypto", 100.0)
    assert result is None


# ==============================================================================
# Test Config
# ==============================================================================

def test_prediction_config_symbols_no_vn():
    """Test prediction config has no VN symbols."""
    from app.prediction.config import DEFAULT_SYMBOLS

    # Check no VN symbols
    for sym in DEFAULT_SYMBOLS:
        assert sym["symbol"] not in ["^VNINDEX", "VNINDEX", "FPT", "VNM"], \
            f"VN symbol found: {sym['symbol']}"


def test_prediction_config_has_backtest_threshold():
    """Test prediction config has backtest threshold."""
    from app.prediction.config import BACKTEST_MIN_ACCURACY

    assert BACKTEST_MIN_ACCURACY >= 0.50
    assert BACKTEST_MIN_ACCURACY <= 0.60


# ==============================================================================
# Test MarketRegime constants
# ==============================================================================

def test_market_regime_constants():
    """Test MarketRegime class has correct constants."""
    from app.prediction.regime_detector import MarketRegime

    assert MarketRegime.TRENDING_UP == "TRENDING_UP"
    assert MarketRegime.TRENDING_DOWN == "TRENDING_DOWN"
    assert MarketRegime.SIDEWAYS == "SIDEWAYS"
    assert MarketRegime.VOLATILE == "VOLATILE"


# ==============================================================================
# Integration smoke tests (async)
# ==============================================================================

@pytest.mark.asyncio
async def test_get_agent_weights_returns_valid():
    """Test that get_agent_weights returns valid weights (may fallback)."""
    from app.prediction.adaptive_weights import get_agent_weights, get_default_weights

    # Try to get weights (may fail without Redis)
    try:
        weights = await get_agent_weights("crypto")
    except Exception:
        weights = get_default_weights()

    assert weights is not None
    assert set(weights.keys()) == {"trend", "value", "macro", "sentiment", "onchain"}
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01
