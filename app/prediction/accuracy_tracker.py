"""
Accuracy tracker for prediction model evaluation.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, desc

logger = logging.getLogger(__name__)


async def update_accuracy_daily() -> dict:
    """
    Update actual prices for predictions from the previous day.
    Calculate accuracy error percentage.

    Returns:
        Statistics about the update operation
    """
    from app.core.database import get_db_context
    from app.models.prediction_models import PredictionFinal
    from app.prediction.data_fetcher import fetch_current_price

    results = {"updated": 0, "errors": 0, "symbols": []}

    try:
        async with get_db_context() as session:
            yesterday = date.today() - timedelta(days=1)

            result = await session.execute(
                select(PredictionFinal)
                .where(PredictionFinal.prediction_date == yesterday)
                .where(PredictionFinal.actual_price.is_(None))
            )
            predictions = result.scalars().all()

            symbols = set(p.symbol for p in predictions)

            for symbol in symbols:
                try:
                    current_data = await fetch_current_price(symbol)
                    if not current_data or "price" not in current_data:
                        continue

                    actual_price = Decimal(str(current_data["price"]))

                    symbol_predictions = [p for p in predictions if p.symbol == symbol]
                    for pred in symbol_predictions:
                        pred.actual_price = actual_price

                        if pred.predicted_price and pred.predicted_price > 0:
                            error_pct = (
                                (actual_price - pred.predicted_price) / pred.predicted_price * 100
                            )
                            pred.accuracy_error_pct = Decimal(str(error_pct))

                    await session.commit()
                    results["updated"] += len(symbol_predictions)
                    results["symbols"].append(symbol)
                    logger.info(f"Updated accuracy for {symbol}: actual={actual_price}")

                except Exception as e:
                    logger.error(f"Failed to update accuracy for {symbol}: {e}")
                    results["errors"] += 1

    except Exception as e:
        logger.error(f"Accuracy update failed: {e}")

    logger.info(f"Accuracy update completed: {results}")
    return results


async def get_accuracy_stats(
    symbol: str,
    days: int = 30,
    horizon: Optional[int] = None,
) -> dict:
    """
    Get accuracy statistics for a symbol.

    Args:
        symbol: Trading symbol
        days: Number of days to analyze
        horizon: Optional specific horizon to filter

    Returns:
        Dictionary with accuracy statistics
    """
    from app.core.database import get_db_context
    from app.models.prediction_models import PredictionFinal

    stats = {
        "symbol": symbol,
        "period_days": days,
        "horizon": horizon,
        "total_predictions": 0,
        "predictions_with_actual": 0,
        "avg_error_pct": None,
        "median_error_pct": None,
        "max_error_pct": None,
        "min_error_pct": None,
        "direction_accuracy": None,
        "within_bounds_pct": None,
    }

    try:
        async with get_db_context() as session:
            cutoff = date.today() - timedelta(days=days)

            query = select(PredictionFinal).where(
                PredictionFinal.symbol == symbol,
                PredictionFinal.generated_at >= cutoff,
                PredictionFinal.actual_price.isnot(None),
            )

            if horizon:
                query = query.where(PredictionFinal.horizon_days == horizon)

            query = query.order_by(desc(PredictionFinal.prediction_date)).limit(1000)

            result = await session.execute(query)
            predictions = result.scalars().all()

            stats["total_predictions"] = len(predictions)
            stats["predictions_with_actual"] = len(predictions)

            if not predictions:
                return stats

            errors = []
            correct_directions = 0
            within_bounds_count = 0

            for pred in predictions:
                if pred.accuracy_error_pct is not None:
                    error = float(pred.accuracy_error_pct)
                    errors.append(error)

                    if pred.predicted_price and pred.current_price:
                        predicted_direction = pred.predicted_price > pred.current_price
                        actual_direction = pred.actual_price > pred.current_price
                        if predicted_direction == actual_direction:
                            correct_directions += 1

                    if pred.predicted_low and pred.predicted_high:
                        if pred.predicted_low <= pred.actual_price <= pred.predicted_high:
                            within_bounds_count += 1

            if errors:
                import numpy as np

                stats["avg_error_pct"] = round(np.mean(errors), 2)
                stats["median_error_pct"] = round(np.median(errors), 2)
                stats["max_error_pct"] = round(max(errors), 2)
                stats["min_error_pct"] = round(min(errors), 2)

            if predictions:
                stats["direction_accuracy"] = round(correct_directions / len(predictions) * 100, 1)
                stats["within_bounds_pct"] = round(within_bounds_count / len(predictions) * 100, 1)

    except Exception as e:
        logger.error(f"Failed to get accuracy stats for {symbol}: {e}")

    return stats


async def get_recent_predictions(
    symbol: str,
    limit: int = 10,
) -> list[dict]:
    """
    Get recent predictions for a symbol with their accuracy.

    Args:
        symbol: Trading symbol
        limit: Maximum number of predictions to return

    Returns:
        List of prediction dictionaries
    """
    from app.core.database import get_db_context
    from app.models.prediction_models import PredictionFinal

    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(PredictionFinal)
                .where(PredictionFinal.symbol == symbol)
                .order_by(desc(PredictionFinal.generated_at))
                .limit(100)
            )
            predictions = result.scalars().all()
            return [p.to_dict() for p in predictions]

    except Exception as e:
        logger.error(f"Failed to get recent predictions for {symbol}: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION V3 — WALK-FORWARD BACKTEST & CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════


async def run_walk_forward_backtest(
    symbol: str = None,
    window_days: int = 30,
) -> dict:
    """
    Walk-forward backtest: danh gia accuracy cua predictions trong 30 ngay qua.
    Chay moi tuan tu Celery Beat.

    Returns:
        {
          "symbol": str,
          "window_days": int,
          "direction_accuracy": float,   # % BUY/SELL direction dung
          "within_bounds_pct": float,    # % actual price nam trong [low, high]
          "avg_error_pct": float,        # MAPE
          "status": "GOOD" | "WARNING" | "ALERT",
          "alert_message": str,
        }
    """
    from app.prediction.config import BACKTEST_MIN_ACCURACY

    if symbol:
        stats = await get_accuracy_stats(symbol, days=window_days)
        direction_acc = (stats.get("direction_accuracy") or 0) / 100

        status = "GOOD"
        alert_msg = ""
        if direction_acc < BACKTEST_MIN_ACCURACY:
            status = "ALERT"
            alert_msg = (f"Accuracy THAP cho {symbol}: {direction_acc:.0%} "
                         f"< threshold {BACKTEST_MIN_ACCURACY:.0%}")
            logger.warning(alert_msg)
        elif direction_acc < BACKTEST_MIN_ACCURACY + 0.05:
            status = "WARNING"
            alert_msg = f"Accuracy hoi thap cho {symbol}: {direction_acc:.0%}"

        return {
            "symbol": symbol,
            "window_days": window_days,
            "direction_accuracy": direction_acc,
            "within_bounds_pct": stats.get("within_bounds_pct"),
            "avg_error_pct": stats.get("avg_error_pct"),
            "status": status,
            "alert_message": alert_msg,
        }
    else:
        # Chay cho top symbols
        from app.prediction.config import DEFAULT_SYMBOLS
        results = []
        for sym_info in DEFAULT_SYMBOLS[:20]:
            try:
                r = await run_walk_forward_backtest(sym_info["symbol"], window_days)
                results.append(r)
            except Exception as e:
                logger.warning(f"Backtest failed for {sym_info['symbol']}: {e}")

        alerts = [r for r in results if r["status"] == "ALERT"]
        warnings = [r for r in results if r["status"] == "WARNING"]

        avg_acc = sum(r.get("direction_accuracy", 0) for r in results) / len(results) if results else 0

        return {
            "total_symbols": len(results),
            "avg_direction_accuracy": round(avg_acc, 3),
            "alerts": alerts,
            "warnings": warnings,
            "status": "ALERT" if alerts else ("WARNING" if warnings else "GOOD"),
        }


async def calibrate_confidence_scores() -> bool:
    """
    Platt scaling calibration: dieu chinh confidence scores de
    confidence X% = dung X% lan trong thuc te.

    Luu calibration parameters vao Redis.
    Chay moi 2 tuan tu Celery Beat.
    """
    import json
    from app.core.database import get_db_context
    from app.models.prediction_models import PredictionFinal
    from sqlalchemy import select

    cutoff = date.today() - timedelta(days=60)

    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(
                    PredictionFinal.confidence_score,
                    PredictionFinal.predicted_price,
                    PredictionFinal.current_price,
                    PredictionFinal.actual_price,
                )
                .where(PredictionFinal.generated_at >= cutoff)
                .where(PredictionFinal.actual_price.isnot(None))
                .where(PredictionFinal.confidence_score.isnot(None))
                .limit(1000)
            )
            rows = result.fetchall()

        if len(rows) < 50:
            logger.info(f"Not enough data for calibration: {len(rows)} samples")
            return False

        # Build arrays
        raw_confidences = []
        outcomes = []

        for row in rows:
            if not all([row.confidence_score, row.predicted_price, row.current_price, row.actual_price]):
                continue

            conf = float(row.confidence_score)
            pred_dir  = float(row.predicted_price) > float(row.current_price)
            actual_dir = float(row.actual_price)   > float(row.current_price)
            correct = int(pred_dir == actual_dir)

            raw_confidences.append(conf)
            outcomes.append(correct)

        if len(raw_confidences) < 30:
            return False

        # Simple isotonic calibration: bin-based
        import numpy as np
        confidences = np.array(raw_confidences)
        outcomes_arr = np.array(outcomes)

        # Bin confidences vao 10 buckets
        bins = np.linspace(0, 1, 11)
        calibration_map = {}
        for i in range(len(bins)-1):
            mask = (confidences >= bins[i]) & (confidences < bins[i+1])
            if mask.sum() >= 5:
                actual_accuracy = outcomes_arr[mask].mean()
                bin_center = (bins[i] + bins[i+1]) / 2
                calibration_map[f"{bin_center:.1f}"] = round(float(actual_accuracy), 3)

        # Luu calibration vao Redis
        from app.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(
            "linew:calibration:confidence",
            14 * 24 * 3600,  # 2 tuan
            json.dumps(calibration_map)
        )

        logger.info(f"Calibration map updated: {calibration_map}")
        return True

    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        return False


async def get_calibrated_confidence(raw_confidence: float) -> float:
    """
    Lay calibrated confidence tu Redis map.
    Neu chua co calibration → return raw confidence.
    """
    try:
        import json
        from app.core.redis import get_redis
        redis = await get_redis()
        cached = await redis.get("linew:calibration:confidence")
        if not cached:
            return raw_confidence

        cal_map = json.loads(cached)
        if not cal_map:
            return raw_confidence

        # Find nearest bin
        bins = [float(k) for k in cal_map.keys()]
        nearest = min(bins, key=lambda x: abs(x - raw_confidence))
        return cal_map[str(nearest)]

    except Exception:
        return raw_confidence
