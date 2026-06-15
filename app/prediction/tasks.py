"""
Prediction Celery tasks.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


async def task_fetch_all_prices() -> dict:
    """
    Fetch prices for all tracked symbols.
    Scheduled: 7:00 AM daily.
    """
    from app.core.database import get_db_context
    from app.models.setting import Setting
    from app.prediction.data_fetcher import fetch_history, fetch_current_price
    from app.prediction.config import DEFAULT_SYMBOLS, HISTORY_PERIOD
    from sqlalchemy import select

    results = {"fetched": 0, "failed": 0, "symbols": []}

    async with get_db_context() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == "prediction")
        )
        setting = result.scalar_one_or_none()
        symbols = DEFAULT_SYMBOLS.copy()

        if setting and setting.value.get("symbols"):
            symbols = setting.value["symbols"]

        for symbol_info in symbols:
            symbol = symbol_info["symbol"]
            try:
                records = await fetch_history(session, symbol, period=HISTORY_PERIOD)
                if records:
                    results["fetched"] += 1
                    results["symbols"].append(symbol)
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results["failed"] += 1

    logger.info(f"Fetched prices: {results}")
    return results


async def task_run_model_inference() -> dict:
    """
    Run TimesFM and Chronos model inference for all symbols.
    Scheduled: 7:30 AM daily.
    """
    from app.core.database import get_db_context
    from app.models.setting import Setting
    from app.prediction.data_fetcher import get_price_history
    from app.prediction.timesfm_model import timesfm_model
    from app.prediction.chronos_model import chronos_model
    from app.prediction.ensemble import compute_ensemble
    from app.prediction.config import DEFAULT_SYMBOLS, PREDICTION_HORIZONS
    from sqlalchemy import select

    results = {"predicted": 0, "failed": 0, "symbols": []}

    async with get_db_context() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == "prediction")
        )
        setting = result.scalar_one_or_none()
        symbols = DEFAULT_SYMBOLS.copy()

        if setting and setting.value.get("symbols"):
            symbols = setting.value["symbols"]

        for symbol_info in symbols:
            symbol = symbol_info["symbol"]
            try:
                history = await get_price_history(session, symbol, days=730)

                if len(history) < 60:
                    logger.warning(f"Not enough data for {symbol}: {len(history)} points")
                    continue

                close_prices = [h["close"] for h in history if h.get("close")]
                if len(close_prices) < 60:
                    continue

                timesfm_preds = timesfm_model.predict(close_prices, horizon=max(PREDICTION_HORIZONS))
                chronos_preds = chronos_model.predict(close_prices, horizon=max(PREDICTION_HORIZONS))

                ensemble_preds = compute_ensemble(timesfm_preds, chronos_preds)

                session["_model_cache"] = session.get("_model_cache", {})
                session["_model_cache"][symbol] = {
                    "timesfm": timesfm_preds,
                    "chronos": chronos_preds,
                    "ensemble": ensemble_preds,
                }

                results["predicted"] += 1
                results["symbols"].append(symbol)
                logger.info(f"Model inference complete for {symbol}")

            except Exception as e:
                logger.error(f"Model inference failed for {symbol}: {e}")
                results["failed"] += 1

    logger.info(f"Model inference results: {results}")
    return results


async def task_run_ai_analysis() -> dict:
    """
    Run AI analysis for all tracked symbols.
    Scheduled: 8:00 AM daily.
    """
    from app.core.database import get_db_context
    from app.models.setting import Setting
    from app.prediction.data_fetcher import get_price_history, fetch_current_price, fetch_fear_greed
    from app.prediction.indicators import calculate_all_indicators, save_indicators
    from app.prediction.ai_analyst import analyze_symbol
    from app.prediction.config import DEFAULT_SYMBOLS
    from sqlalchemy import select

    results = {"analyzed": 0, "failed": 0, "symbols": []}

    async with get_db_context() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == "prediction")
        )
        setting = result.scalar_one_or_none()
        symbols = DEFAULT_SYMBOLS.copy()

        if setting and setting.value.get("symbols"):
            symbols = setting.value["symbols"]

        fear_greed = await fetch_fear_greed()

        for symbol_info in symbols:
            symbol = symbol_info["symbol"]
            try:
                history = await get_price_history(session, symbol, days=365)
                if len(history) < 30:
                    continue

                current_data = await fetch_current_price(symbol)
                if not current_data:
                    continue

                current_price = current_data["price"]
                price_change_pct = current_data.get("change_pct", 0)

                highs = [h["high"] for h in history if h.get("high")]
                lows = [h["low"] for h in history if h.get("low")]
                closes = [h["close"] for h in history if h.get("close")]
                volumes = [h["volume"] for h in history if h.get("volume")]

                indicators = calculate_all_indicators(highs, lows, closes, volumes)
                await save_indicators(session, symbol, indicators)

                analysis = await analyze_symbol(
                    symbol=symbol,
                    current_price=current_price,
                    price_change_pct=price_change_pct,
                    indicators=indicators,
                    fear_greed=fear_greed,
                )

                if analysis:
                    results["analyzed"] += 1
                    results["symbols"].append(symbol)

            except Exception as e:
                logger.error(f"AI analysis failed for {symbol}: {e}")
                results["failed"] += 1

    logger.info(f"AI analysis results: {results}")
    return results


async def task_run_ai_analysis_single(symbol: str) -> dict:
    """
    Run AI analysis for a single symbol.
    Used for re-analysis triggered by alerts.
    """
    from app.core.database import get_db_context
    from app.prediction.data_fetcher import get_price_history, fetch_current_price, fetch_fear_greed
    from app.prediction.indicators import calculate_all_indicators, save_indicators
    from app.prediction.ai_analyst import analyze_symbol

    try:
        async with get_db_context() as session:
            history = await get_price_history(session, symbol, days=365)
            if len(history) < 30:
                return {"error": "Not enough data"}

            current_data = await fetch_current_price(symbol)
            if not current_data:
                return {"error": "Failed to fetch current price"}

            current_price = current_data["price"]
            price_change_pct = current_data.get("change_pct", 0)

            highs = [h["high"] for h in history if h.get("high")]
            lows = [h["low"] for h in history if h.get("low")]
            closes = [h["close"] for h in history if h.get("close")]
            volumes = [h["volume"] for h in history if h.get("volume")]

            indicators = calculate_all_indicators(highs, lows, closes, volumes)
            await save_indicators(session, symbol, indicators)

            fear_greed = await fetch_fear_greed()

            analysis = await analyze_symbol(
                symbol=symbol,
                current_price=current_price,
                price_change_pct=price_change_pct,
                indicators=indicators,
                fear_greed=fear_greed,
            )

            return {"symbol": symbol, "analysis": analysis}

    except Exception as e:
        logger.error(f"Single AI analysis failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


async def task_update_accuracy() -> dict:
    """
    Update accuracy metrics for past predictions.
    Scheduled: 9:00 AM daily.
    """
    from app.prediction.accuracy_tracker import update_accuracy_daily

    try:
        results = await update_accuracy_daily()
        logger.info(f"Accuracy update completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Accuracy update task failed: {e}")
        return {"error": str(e)}


async def task_check_alerts() -> dict:
    """
    Check for price alerts.
    Scheduled: Every 2 hours.
    """
    from app.prediction.alert_monitor import check_price_alerts

    try:
        results = await check_price_alerts()
        logger.info(f"Alert check completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Alert check task failed: {e}")
        return {"error": str(e)}


async def task_run_full_prediction(symbol: Optional[str] = None) -> dict:
    """
    Run complete prediction pipeline for symbols.
    Can be triggered manually or scheduled.

    Args:
        symbol: Optional specific symbol to predict. If None, predicts all tracked symbols.
    """
    from app.core.database import get_db_context
    from app.models.setting import Setting
    from app.prediction.data_fetcher import get_price_history, fetch_current_price, fetch_fear_greed
    from app.prediction.indicators import calculate_all_indicators, save_indicators, get_technical_signals
    from app.prediction.timesfm_model import timesfm_model
    from app.prediction.chronos_model import chronos_model
    from app.prediction.ensemble import compute_ensemble, compute_final_prediction, save_prediction_final
    from app.prediction.ai_analyst import analyze_symbol, get_latest_analysis
    from app.prediction.config import DEFAULT_SYMBOLS, PREDICTION_HORIZONS
    from sqlalchemy import select

    results = {"symbols": [], "errors": []}

    async with get_db_context() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == "prediction")
        )
        setting = result.scalar_one_or_none()
        symbols = DEFAULT_SYMBOLS.copy()

        if setting and setting.value.get("symbols"):
            symbols = setting.value["symbols"]

        if symbol:
            symbols = [s for s in symbols if s["symbol"] == symbol]
            if not symbols:
                symbols = [{"symbol": symbol, "name": symbol, "type": "unknown"}]

        fear_greed = await fetch_fear_greed()

        for symbol_info in symbols:
            sym = symbol_info["symbol"]
            try:
                logger.info(f"Running full prediction for {sym}")

                history = await get_price_history(session, sym, days=730)
                if len(history) < 60:
                    results["errors"].append(f"{sym}: Not enough data")
                    continue

                current_data = await fetch_current_price(sym)
                if not current_data:
                    results["errors"].append(f"{sym}: Failed to fetch current price")
                    continue

                current_price = current_data["price"]
                price_change_pct = current_data.get("change_pct", 0)

                highs = [h["high"] for h in history if h.get("high")]
                lows = [h["low"] for h in history if h.get("low")]
                closes = [h["close"] for h in history if h.get("close")]
                volumes = [h["volume"] for h in history if h.get("volume")]

                indicators = calculate_all_indicators(highs, lows, closes, volumes)
                await save_indicators(session, sym, indicators)
                technical_signals = get_technical_signals(indicators)

                analysis = await analyze_symbol(
                    symbol=sym,
                    current_price=current_price,
                    price_change_pct=price_change_pct,
                    indicators=indicators,
                    fear_greed=fear_greed,
                )

                timesfm_preds = timesfm_model.predict(closes, horizon=max(PREDICTION_HORIZONS))
                chronos_preds = chronos_model.predict(closes, horizon=max(PREDICTION_HORIZONS))
                ensemble_preds = compute_ensemble(timesfm_preds, chronos_preds)

                for horizon in PREDICTION_HORIZONS:
                    final_pred = compute_final_prediction(
                        ensemble_preds, analysis, current_price, horizon
                    )

                    await save_prediction_final(
                        session=session,
                        symbol=sym,
                        horizon=horizon,
                        current_price=current_price,
                        final_prediction=final_pred,
                        timesfm_predictions=timesfm_preds,
                        chronos_predictions=chronos_preds,
                        technical_signals=technical_signals,
                    )

                results["symbols"].append(sym)
                logger.info(f"Full prediction complete for {sym}")

            except Exception as e:
                logger.error(f"Full prediction failed for {sym}: {e}")
                results["errors"].append(f"{sym}: {str(e)}")

    return results


async def task_fetch_prices() -> dict:
    """Legacy task - redirects to task_fetch_all_prices."""
    return await task_fetch_all_prices()


async def task_run_predictions() -> dict:
    """Legacy task - redirects to task_run_model_inference."""
    return await task_run_model_inference()


async def task_fetch_single_symbol(symbol: str) -> dict:
    """Fetch prices for a single symbol."""
    from app.core.database import get_db_context
    from app.prediction.data_fetcher import fetch_history
    from app.prediction.config import HISTORY_PERIOD

    async with get_db_context() as session:
        records = await fetch_history(session, symbol, period=HISTORY_PERIOD)
        return {"symbol": symbol, "records": len(records)}


async def task_predict_single_symbol(symbol: str, horizon: int = 7) -> dict:
    """Run prediction for a single symbol."""
    result = await task_run_full_prediction(symbol=symbol)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION V3 TASKS
# ═══════════════════════════════════════════════════════════════════════════════

def task_update_adaptive_weights() -> dict:
    """
    Cap nhat adaptive agent weights dua tren 30 ngay performance.
    Chay moi thu 2, 2:00 AM.
    """
    from app.prediction.adaptive_weights import update_adaptive_weights
    from app.worker.celery_app import run_async
    try:
        result = run_async(update_adaptive_weights())
        logger.info(f"Adaptive weights updated: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to update adaptive weights: {e}")
        return {"error": str(e)}


def task_weekly_backtest() -> dict:
    """
    Walk-forward backtest hang tuan cho toan bo symbols.
    Chay moi thu 2, 3:00 AM.
    """
    from app.prediction.accuracy_tracker import run_walk_forward_backtest
    from app.worker.celery_app import run_async
    try:
        result = run_async(run_walk_forward_backtest())
        if result.get("status") == "ALERT":
            logger.warning(f"BACKTEST ALERT: {result.get('alerts')}")
        return result
    except Exception as e:
        logger.error(f"Failed to run weekly backtest: {e}")
        return {"error": str(e)}


def task_calibrate_confidence() -> dict:
    """
    Calibrate confidence scores (Platt scaling) moi 2 tuan.
    Chay moi thu 2, 4:00 AM, moi 2 tuan.
    """
    from app.prediction.accuracy_tracker import calibrate_confidence_scores
    from app.worker.celery_app import run_async
    try:
        result = run_async(calibrate_confidence_scores())
        logger.info(f"Confidence calibration completed: {result}")
        return {"success": result}
    except Exception as e:
        logger.error(f"Failed to calibrate confidence: {e}")
        return {"error": str(e)}
