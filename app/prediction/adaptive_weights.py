"""
Adaptive Weight System — tu dong dieu chinh agent weights dua tren performance.

Logic:
  1. Moi 7 ngay, doc accuracy_tracker records cua 30 ngay qua
  2. Tinh win-rate tung agent (direction correct / total predictions)
  3. Cap nhat weights bang softmax(win_rates) voi EMA smoothing
  4. Luu vao Redis voi TTL 7 ngay
  5. ai_analyst.py doc weights tu Redis thay vi hardcode

Khoi dong fallback: Neu chua co du data → dung default weights.
"""
import json
import logging
import math
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Default weights khi chua co du data
DEFAULT_WEIGHTS = {
    "trend":     0.25,
    "value":     0.25,
    "macro":     0.20,
    "sentiment": 0.15,
    "onchain":   0.15,
}

ADAPTIVE_WEIGHTS_KEY = "linew:adaptive_weights"
ADAPTIVE_WEIGHTS_TTL = 7 * 24 * 3600  # 7 ngay
MIN_SAMPLES_FOR_ADAPTATION = 20        # Can it nhat 20 predictions moi tinh
EMA_ALPHA = 0.3                        # Exponential smoothing: 0.3 = reactive, 0.1 = stable


async def get_agent_weights(market: str = "all") -> dict:
    """
    Lay weights hien tai cho cac agents.
    Uu tien: Redis adaptive weights → default weights.

    Args:
        market: 'crypto', 'us', hoac 'all'
    Returns:
        Dict {agent_name: weight}
    """
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        key = f"{ADAPTIVE_WEIGHTS_KEY}:{market}"
        cached = await redis.get(key)
        if cached:
            weights = json.loads(cached)
            logger.debug(f"Loaded adaptive weights for {market}: {weights}")
            return weights
    except Exception as e:
        logger.warning(f"Redis get adaptive weights failed: {e}")

    return DEFAULT_WEIGHTS.copy()


async def update_adaptive_weights() -> dict:
    """
    Tinh lai va luu adaptive weights cho tung market.
    Goi tu Celery Beat scheduler moi 7 ngay.

    Returns:
        Dict voi weights moi cho moi market.
    """
    results = {}
    for market in ["crypto", "us", "all"]:
        try:
            weights = await _compute_weights_for_market(market)
            await _save_weights(market, weights)
            results[market] = weights
            logger.info(f"Updated adaptive weights [{market}]: {weights}")
        except Exception as e:
            logger.error(f"Failed to compute weights for {market}: {e}")
            results[market] = DEFAULT_WEIGHTS.copy()

    return results


async def _compute_weights_for_market(market: str) -> dict:
    """
    Tinh win-rate tung agent dua tren MarketResearch records.
    """
    from sqlalchemy import text

    cutoff = date.today() - timedelta(days=30)

    # Query: lay agent predictions va actual price outcomes
    # Dung market_research.key_factors de extract agent signals
    # key_factors format: ["TrendAgent: BUY", "ValueAgent: HOLD", ...]
    win_rates = {}

    try:
        from app.core.database import get_db_context
        async with get_db_context() as session:
            # Join market_research voi prediction_final de co actual outcome
            query = text("""
                SELECT
                    mr.key_factors,
                    mr.sentiment AS predicted_sentiment,
                    mr.analysis_date,
                    pf.actual_price,
                    pf.current_price,
                    pf.predicted_price,
                    mr.symbol,
                    ts.market
                FROM market_research mr
                LEFT JOIN prediction_final pf
                    ON mr.symbol = pf.symbol
                    AND pf.prediction_date = mr.analysis_date + INTERVAL '7 days'
                    AND pf.horizon_days = 7
                LEFT JOIN tracked_symbols ts ON mr.symbol = ts.symbol
                WHERE mr.analysis_date >= :cutoff
                    AND pf.actual_price IS NOT NULL
                    AND (:market = 'all' OR ts.market = :market OR :market IS NULL)
                ORDER BY mr.analysis_date DESC
                LIMIT 500
            """)
            result = await session.execute(query, {"cutoff": cutoff, "market": market if market != "all" else None})
            rows = result.fetchall()

        if len(rows) < MIN_SAMPLES_FOR_ADAPTATION:
            logger.info(f"Not enough samples for {market}: {len(rows)} < {MIN_SAMPLES_FOR_ADAPTATION}")
            return DEFAULT_WEIGHTS.copy()

        # Dem win/total cho tung agent
        agent_stats = {
            "trend": {"wins": 0, "total": 0},
            "value": {"wins": 0, "total": 0},
            "macro": {"wins": 0, "total": 0},
            "sentiment": {"wins": 0, "total": 0},
            "onchain": {"wins": 0, "total": 0},
        }

        AGENT_NAME_MAP = {
            "TrendAgent": "trend",
            "ValueAgent": "value",
            "MacroAgent": "macro",
            "SentimentAgent": "sentiment",
            "OnChainAgent": "onchain",
        }

        for row in rows:
            key_factors = row.key_factors or []
            actual_price = float(row.actual_price) if row.actual_price else None
            current_price = float(row.current_price) if row.current_price else None

            if not actual_price or not current_price:
                continue

            # Actual direction: gia thuc te tang hay giam
            actual_direction = actual_price > current_price  # True = tang, False = giam

            # Parse tung agent signal tu key_factors
            # Format: "TrendAgent: BUY" hoac "TrendAgent: BUY (conf=0.75)"
            for factor in key_factors:
                for agent_name, agent_key in AGENT_NAME_MAP.items():
                    if agent_name in factor:
                        if "BUY" in factor:
                            predicted_direction = True
                        elif "SELL" in factor:
                            predicted_direction = False
                        elif "HOLD" in factor:
                            # HOLD → skip (khong tinh win/lose)
                            continue
                        else:
                            continue

                        agent_stats[agent_key]["total"] += 1
                        if predicted_direction == actual_direction:
                            agent_stats[agent_key]["wins"] += 1

        # Tinh win rates
        raw_rates = {}
        for agent, stats in agent_stats.items():
            if stats["total"] >= 5:
                raw_rates[agent] = stats["wins"] / stats["total"]
            else:
                raw_rates[agent] = DEFAULT_WEIGHTS[agent]  # Fallback

        # Softmax de tong = 1.0
        weights = _softmax_normalize(raw_rates)

        # EMA smoothing voi previous weights
        prev_weights = await get_agent_weights(market)
        smoothed = {}
        for agent in weights:
            smoothed[agent] = EMA_ALPHA * weights[agent] + (1 - EMA_ALPHA) * prev_weights.get(agent, DEFAULT_WEIGHTS[agent])

        # Re-normalize sau smoothing
        total = sum(smoothed.values())
        final_weights = {k: round(v / total, 4) for k, v in smoothed.items()}

        return final_weights

    except Exception as e:
        logger.error(f"Weight computation failed for {market}: {e}")
        return DEFAULT_WEIGHTS.copy()


def _softmax_normalize(rates: dict) -> dict:
    """Convert win-rates to weights using softmax (ensures sum=1, amplifies differences)."""
    # Temperature scaling: T=2 = moderate smoothing, T=1 = sharp
    T = 2.0
    exp_vals = {k: math.exp(v / T) for k, v in rates.items()}
    total = sum(exp_vals.values())
    return {k: v / total for k, v in exp_vals.items()}


async def _save_weights(market: str, weights: dict):
    """Luu weights vao Redis."""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        key = f"{ADAPTIVE_WEIGHTS_KEY}:{market}"
        await redis.setex(key, ADAPTIVE_WEIGHTS_TTL, json.dumps(weights))
    except Exception as e:
        logger.warning(f"Failed to save weights to Redis: {e}")


def get_default_weights() -> dict:
    """Return default weights (fallback)."""
    return DEFAULT_WEIGHTS.copy()
