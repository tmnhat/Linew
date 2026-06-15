"""
Prediction System configuration.

Note: VN stocks have been removed from this system (V3 upgrade).
Focus: US stocks + Crypto only.
"""
from typing import List, Dict

# Default symbols - US stocks and Crypto only (VN stocks removed in V3)
DEFAULT_SYMBOLS: List[Dict[str, str]] = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "type": "crypto"},
    {"symbol": "ETH-USD", "name": "Ethereum", "type": "crypto"},
    {"symbol": "AAPL", "name": "Apple", "type": "stock"},
    {"symbol": "GOOGL", "name": "Google", "type": "stock"},
    {"symbol": "MSFT", "name": "Microsoft", "type": "stock"},
    {"symbol": "NVDA", "name": "NVIDIA", "type": "stock"},
    {"symbol": "TSLA", "name": "Tesla", "type": "stock"},
    {"symbol": "AMZN", "name": "Amazon", "type": "stock"},
    {"symbol": "SPY", "name": "S&P 500 ETF", "type": "stock"},
    {"symbol": "QQQ", "name": "Nasdaq 100 ETF", "type": "stock"},
]

PREDICTION_HORIZONS: List[int] = [1, 3, 7, 30]

HISTORY_PERIOD: str = "2y"

FEAR_GREED_API: str = "https://api.alternative.me/fng/"

TIMESFM_CONFIG = {
    "checkpoint": -1,
    "horizon_len": 30,
    "context_len": 512,
}

CHRONOS_CONFIG = {
    "model_name": "amazon/chronos-bolt-large",
    "device": "auto",
}

ENSEMBLE_WEIGHTS = {
    "timesfm": 0.5,
    "chronos": 0.5,
}

AI_ANALYST_MODEL: str = "gpt-4o-mini"  # AI model for market analysis (fallback)
AI_TEMPERATURE: float = 0.7
AI_MAX_TOKENS: int = 2048

PRICE_ALERT_THRESHOLD_PCT: float = 5.0

ACCURACY_TRACKING_DAYS: int = 30

# ═══════════════════════════════════════════════════════════════════════
# PREDICTION V2 - Multi-Agent Configuration
# ═══════════════════════════════════════════════════════════════════════

# Enable/disable specific agents (set to False to disable)
AGENT_STYLES_ENABLED = {
    "trend": True,    # Technical analysis
    "value": True,    # Fundamental analysis
    "macro": True,    # Macroeconomic analysis
    "sentiment": True,  # Market sentiment
    "onchain": True,  # On-chain data (crypto)
}

# Data layer timeouts (seconds)
FUNDAMENTAL_FETCH_TIMEOUT = 30
MACRO_FETCH_TIMEOUT = 30
ONCHAIN_FETCH_TIMEOUT = 30
EVENT_FETCH_TIMEOUT = 30

# Fallback model when primary fails
FALLBACK_MODEL = "holt-winters"

# Backtesting parameters
BACKTEST_WINDOW_DAYS = 30
BACKTEST_MIN_ACCURACY = 0.55  # Alert neu accuracy < 55%
