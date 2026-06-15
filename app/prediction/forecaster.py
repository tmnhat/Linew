"""
TimesFM forecaster for price prediction (legacy wrapper).

This module is kept for backward compatibility.
Use app.prediction.timesfm_model.TimesFMModel directly for new code.
"""
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional

import numpy as np

from app.prediction.timesfm_model import timesfm_model

logger = logging.getLogger(__name__)


async def predict_price(
    session,
    symbol: str,
    horizon: int = 7,
) -> dict:
    """
    Generate price predictions using TimesFM.

    Returns:
        {
            "symbol": str,
            "predictions": [
                {"date": "2024-01-08", "price": 50000.0, "low": 49000.0, "high": 51000.0},
                ...
            ],
            "model_used": "timesfm-2.5-200m",
        }
    """
    from app.prediction.data_fetcher import get_price_history
    from app.models.prediction import Prediction

    history = await get_price_history(session, symbol, days=365)

    if len(history) < 30:
        logger.warning(f"Not enough data for {symbol}: {len(history)} points")
        return {
            "symbol": symbol,
            "predictions": [],
            "error": f"Not enough data ({len(history)} points, need 30+)",
        }

    close_prices = [h["close"] for h in history if h.get("close")]

    if len(close_prices) < 30:
        return {
            "symbol": symbol,
            "predictions": [],
            "error": "Not enough valid close prices",
        }

    predictions = timesfm_model.predict(close_prices, horizon)
    model_name = "timesfm-2.5-200m" if timesfm_model.model else "simple-ma"

    last_date = history[-1]["date"]
    saved_predictions = []

    for i, pred in enumerate(predictions):
        pred_date = datetime.strptime(last_date, "%Y-%m-%d").date() + timedelta(days=i + 1)

        prediction = Prediction(
            symbol=symbol,
            prediction_date=pred_date,
            predicted_price=Decimal(str(pred["price"])),
            low_bound=Decimal(str(pred["low"])),
            high_bound=Decimal(str(pred["high"])),
            model_used=model_name,
            generated_at=datetime.utcnow(),
        )
        session.add(prediction)
        saved_predictions.append({
            "date": pred_date.isoformat(),
            "price": pred["price"],
            "low": pred["low"],
            "high": pred["high"],
        })

    await session.commit()

    return {
        "symbol": symbol,
        "predictions": saved_predictions,
        "model_used": model_name,
        "generated_at": datetime.utcnow().isoformat(),
    }


async def timesfm_forecast(model, close_prices: list, horizon: int) -> list[dict]:
    """Generate forecast using TimesFM (wrapper)."""
    return timesfm_model.predict(close_prices, horizon)


def simple_forecast(close_prices: list, horizon: int) -> list[dict]:
    """
    Improved fallback forecast using Holt-Winters Exponential Smoothing.
    Much better than simple moving average for financial time series.
    Falls back to linear trend if statsmodels not available.
    """
    import numpy as np

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            series = np.array(close_prices[-min(len(close_prices), 180):])

            # Holt-Winters with additive trend (no seasonality for daily prices)
            hw_model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal=None,
                damped_trend=True,
            )
            fit = hw_model.fit(optimized=True)
            forecast_values = fit.forecast(horizon)

            # Calculate uncertainty bands (grows with horizon)
            residuals = fit.resid
            std_resid = np.std(residuals)

            predictions = []
            for i, price in enumerate(forecast_values):
                uncertainty = std_resid * np.sqrt(i + 1)
                predictions.append({
                    "price": round(float(max(price, 0)), 2),
                    "low": round(float(max(price - 2 * uncertainty, 0)), 2),
                    "high": round(float(price + 2 * uncertainty), 2),
                })

            logger.info(f"Holt-Winters forecast: {len(predictions)} periods")
            return predictions

    except ImportError:
        logger.warning("statsmodels not available, using linear trend fallback")
        return _linear_trend_forecast(close_prices, horizon)
    except Exception as e:
        logger.warning(f"Holt-Winters failed: {e}, using linear trend")
        return _linear_trend_forecast(close_prices, horizon)


def _linear_trend_forecast(close_prices: list, horizon: int) -> list[dict]:
    """Linear regression trend as last resort fallback."""
    import numpy as np

    recent = np.array(close_prices[-60:])
    x = np.arange(len(recent))

    # Fit linear trend
    coeffs = np.polyfit(x, recent, 1)
    trend_slope = coeffs[0]
    last_price = recent[-1]
    std_price = np.std(recent[-30:])

    predictions = []
    for i in range(horizon):
        predicted = last_price + trend_slope * (i + 1)
        uncertainty = std_price * np.sqrt(i / 10 + 1)
        predictions.append({
            "price": round(float(max(predicted, 0)), 2),
            "low": round(float(max(predicted - 1.5 * uncertainty, 0)), 2),
            "high": round(float(predicted + 1.5 * uncertainty), 2),
        })

    return predictions
