"""
Price alert monitor for tracking significant price deviations.
"""
import logging
from typing import Optional

from app.prediction.config import PRICE_ALERT_THRESHOLD_PCT

logger = logging.getLogger(__name__)


async def check_price_alerts() -> dict:
    """
    Check for significant price deviations from predictions.
    Triggers re-analysis when deviation exceeds threshold.

    Returns:
        Dictionary with alert results
    """
    from app.core.database import get_db_context
    from app.models.prediction_models import PredictionFinal
    from app.prediction.data_fetcher import fetch_current_price
    from sqlalchemy import select, desc

    results = {
        "checked": 0,
        "alerts_triggered": 0,
        "symbols": [],
    }

    try:
        async with get_db_context() as session:
            # Get the latest prediction for each symbol only
            # Using DISTINCT ON to get the latest record per symbol
            from sqlalchemy import distinct
            result = await session.execute(
                select(PredictionFinal)
                .distinct(PredictionFinal.symbol)
                .order_by(PredictionFinal.symbol, desc(PredictionFinal.generated_at))
                .limit(100)  # Safety limit
            )
            latest_predictions = result.scalars().all()

            for pred in latest_predictions:
                symbol = pred.symbol

                if not pred.current_price:
                    continue

                try:
                    current_data = await fetch_current_price(symbol)
                    if not current_data or "price" not in current_data:
                        continue

                    current_price = current_data["price"]
                    results["checked"] += 1

                    deviation_pct = abs(
                        (current_price - float(pred.current_price)) / float(pred.current_price) * 100
                    )

                    if deviation_pct > PRICE_ALERT_THRESHOLD_PCT:
                        logger.warning(
                            f"Price alert: {symbol} deviated {deviation_pct:.2f}% "
                            f"from prediction (threshold: {PRICE_ALERT_THRESHOLD_PCT}%)"
                        )

                        await _trigger_reanalysis(symbol, current_price, deviation_pct)
                        results["alerts_triggered"] += 1
                        results["symbols"].append(symbol)

                except Exception as e:
                    logger.error(f"Failed to check alert for {symbol}: {e}")

    except Exception as e:
        logger.error(f"Alert check failed: {e}")

    logger.info(f"Alert check completed: {results}")
    return results


async def _trigger_reanalysis(symbol: str, current_price: float, deviation_pct: float) -> None:
    """
    Trigger re-analysis for a symbol with significant price deviation.
    """
    from app.prediction.tasks import task_run_ai_analysis_single

    logger.info(f"Triggering re-analysis for {symbol} due to {deviation_pct:.2f}% deviation")

    try:
        await task_run_ai_analysis_single(symbol)
    except Exception as e:
        logger.error(f"Failed to trigger re-analysis for {symbol}: {e}")


async def get_active_alerts() -> list[dict]:
    """
    Get currently active price alerts.

    Returns:
        List of active alert dictionaries
    """
    from app.core.redis import redis_client
    import json

    try:
        if not redis_client:
            return []

        keys = await redis_client.keys("alert:*")
        alerts = []

        for key in keys:
            data = await redis_client.get(key)
            if data:
                try:
                    alerts.append(json.loads(data))
                except json.JSONDecodeError:
                    continue

        return alerts

    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        return []


async def create_alert(
    symbol: str,
    alert_type: str,
    threshold_pct: float = PRICE_ALERT_THRESHOLD_PCT,
) -> bool:
    """
    Create a new price alert.

    Args:
        symbol: Trading symbol
        alert_type: Type of alert (e.g., 'deviation', 'target', 'stop_loss')
        threshold_pct: Threshold percentage for the alert

    Returns:
        True if alert was created successfully
    """
    from app.core.redis import redis_client
    import json
    from datetime import datetime

    try:
        if not redis_client:
            logger.warning("Redis not available, alert not created")
            return False

        alert_id = f"{symbol}:{alert_type}:{datetime.utcnow().timestamp()}"
        alert_data = {
            "id": alert_id,
            "symbol": symbol,
            "type": alert_type,
            "threshold_pct": threshold_pct,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
        }

        await redis_client.setex(
            f"alert:{alert_id}",
            86400 * 7,
            json.dumps(alert_data),
        )

        logger.info(f"Created alert for {symbol}: {alert_type}")
        return True

    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        return False


async def dismiss_alert(alert_id: str) -> bool:
    """
    Dismiss an active alert.

    Args:
        alert_id: ID of the alert to dismiss

    Returns:
        True if alert was dismissed successfully
    """
    from app.core.redis import redis_client

    try:
        if not redis_client:
            return False

        await redis_client.delete(f"alert:{alert_id}")
        logger.info(f"Dismissed alert: {alert_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to dismiss alert: {e}")
        return False
