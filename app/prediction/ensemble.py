"""
Ensemble prediction combining TimesFM, Chronos, and AI analysis.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Tuple

import numpy as np

from app.prediction.config import ENSEMBLE_WEIGHTS

logger = logging.getLogger(__name__)


def compute_ensemble(
    timesfm_predictions: list[dict],
    chronos_predictions: list[dict],
    weights: Tuple[float, float] = None,
) -> list[dict]:
    """
    Combine TimesFM and Chronos predictions using weighted average.

    Args:
        timesfm_predictions: List of TimesFM predictions with price, low, high
        chronos_predictions: List of Chronos predictions with price, low, high
        weights: Tuple of (timesfm_weight, chronos_weight), defaults to config

    Returns:
        List of ensemble predictions
    """
    if weights is None:
        weights = (ENSEMBLE_WEIGHTS["timesfm"], ENSEMBLE_WEIGHTS["chronos"])

    w_timesfm, w_chronos = weights

    horizon = min(len(timesfm_predictions), len(chronos_predictions))

    ensemble = []
    for i in range(horizon):
        tf_pred = timesfm_predictions[i]
        ch_pred = chronos_predictions[i]

        ensemble_pred = {
            "price": (tf_pred["price"] * w_timesfm + ch_pred["price"] * w_chronos),
            "low": (tf_pred["low"] * w_timesfm + ch_pred["low"] * w_chronos),
            "high": (tf_pred["high"] * w_timesfm + ch_pred["high"] * w_chronos),
        }

        ensemble_pred["price"] = round(ensemble_pred["price"], 2)
        ensemble_pred["low"] = round(ensemble_pred["low"], 2)
        ensemble_pred["high"] = round(ensemble_pred["high"], 2)

        ensemble.append(ensemble_pred)

    return ensemble


def compute_final_prediction(
    ensemble_predictions: list[dict],
    ai_analysis: Optional[dict],
    current_price: float,
    horizon: int,
) -> dict:
    """
    Compute final prediction by applying AI sentiment adjustment.

    Args:
        ensemble_predictions: List of ensemble predictions
        ai_analysis: AI market analysis with sentiment
        current_price: Current price of the asset
        horizon: Prediction horizon in days

    Returns:
        Final prediction dictionary
    """
    horizon_index = min(horizon - 1, len(ensemble_predictions) - 1)
    base_prediction = ensemble_predictions[horizon_index]

    predicted_price = base_prediction["price"]
    predicted_low = base_prediction["low"]
    predicted_high = base_prediction["high"]
    ai_adjustment_pct = 0.0
    ai_sentiment = None
    ai_sentiment_score = None

    if ai_analysis:
        sentiment = ai_analysis.get("sentiment", "neutral")
        sentiment_score = ai_analysis.get("sentiment_score", 0.5)
        ai_confidence = ai_analysis.get("confidence_score", 0.5)

        # Dynamic weight based on AI confidence (0.02-0.12 range)
        dynamic_weight = 0.02 + (ai_confidence * 0.10)

        sentiment_multiplier = {
            "positive": 1.0 + (sentiment_score - 0.5) * dynamic_weight,
            "bullish": 1.0 + (sentiment_score - 0.5) * dynamic_weight,
            "negative": 1.0 - (sentiment_score - 0.5) * dynamic_weight,
            "bearish": 1.0 - (sentiment_score - 0.5) * dynamic_weight,
            "neutral": 1.0,
        }

        adjustment = sentiment_multiplier.get(sentiment, 1.0)
        predicted_price = predicted_price * adjustment
        predicted_high = predicted_high * adjustment
        predicted_low = predicted_low * adjustment

        ai_adjustment_pct = (adjustment - 1.0) * 100
        ai_sentiment = sentiment
        ai_sentiment_score = sentiment_score

        predicted_price = round(predicted_price, 2)
        predicted_high = round(predicted_high, 2)
        predicted_low = round(predicted_low, 2)

    change_pct = ((predicted_price - current_price) / current_price) * 100

    confidence = _compute_confidence(
        base_prediction["low"],
        base_prediction["high"],
        predicted_price,
        ai_analysis,
    )

    return {
        "predicted_price": predicted_price,
        "predicted_low": predicted_low,
        "predicted_high": predicted_high,
        "change_pct": round(change_pct, 4),
        "confidence_score": confidence,
        "ai_sentiment": ai_sentiment,
        "ai_sentiment_score": ai_sentiment_score,
        "ai_adjustment_pct": round(ai_adjustment_pct, 4),
    }


def _compute_confidence(
    low: float,
    high: float,
    predicted: float,
    ai_analysis: Optional[dict],
) -> float:
    """
    Compute confidence score based on prediction range and AI analysis.

    Args:
        low: Lower bound of prediction
        high: Upper bound of prediction
        predicted: Predicted price
        ai_analysis: AI analysis data

    Returns:
        Confidence score between 0 and 1
    """
    price_range_pct = ((high - low) / predicted) * 100 if predicted > 0 else 100

    base_confidence = max(0.0, 1.0 - (price_range_pct / 100))

    if ai_analysis and ai_analysis.get("confidence_score"):
        ai_confidence = float(ai_analysis.get("confidence_score", 0.5))
        confidence = base_confidence * 0.6 + ai_confidence * 0.4
    else:
        confidence = base_confidence

    return round(confidence, 4)


async def save_prediction_final(
    session,
    symbol: str,
    horizon: int,
    current_price: float,
    final_prediction: dict,
    timesfm_predictions: list[dict],
    chronos_predictions: list[dict],
    technical_signals: dict,
) -> bool:
    """
    Save final prediction to database.

    Args:
        session: Database session
        symbol: Trading symbol
        horizon: Prediction horizon in days
        current_price: Current price
        final_prediction: Final prediction data
        timesfm_predictions: TimesFM raw predictions
        chronos_predictions: Chronos raw predictions
        technical_signals: Technical trading signals

    Returns:
        True if saved successfully
    """
    from app.models.prediction_models import PredictionFinal
    from sqlalchemy.dialects.postgresql import insert

    try:
        prediction_date = date.today() + timedelta(days=horizon)

        tf_pred = timesfm_predictions[horizon - 1] if horizon <= len(timesfm_predictions) else None
        ch_pred = chronos_predictions[horizon - 1] if horizon <= len(chronos_predictions) else None

        stmt = insert(PredictionFinal).values(
            symbol=symbol,
            prediction_date=prediction_date,
            horizon_days=horizon,
            current_price=Decimal(str(current_price)),
            predicted_price=Decimal(str(final_prediction["predicted_price"])),
            predicted_low=Decimal(str(final_prediction["predicted_low"])),
            predicted_high=Decimal(str(final_prediction["predicted_high"])),
            change_pct=Decimal(str(final_prediction.get("change_pct", 0))),
            confidence_score=Decimal(str(final_prediction.get("confidence_score", 0.5))),
            timesfm_prediction=Decimal(str(tf_pred["price"])) if tf_pred else None,
            chronos_prediction=Decimal(str(ch_pred["price"])) if ch_pred else None,
            ensemble_weight_timesfm=Decimal(str(ENSEMBLE_WEIGHTS["timesfm"])),
            ensemble_weight_chronos=Decimal(str(ENSEMBLE_WEIGHTS["chronos"])),
            ai_sentiment=final_prediction.get("ai_sentiment"),
            ai_sentiment_score=Decimal(str(final_prediction["ai_sentiment_score"])) if final_prediction.get("ai_sentiment_score") else None,
            ai_adjustment_pct=Decimal(str(final_prediction.get("ai_adjustment_pct", 0))),
            technical_signals=technical_signals,
            model_used="ensemble-timesfm-chronos-ai",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "prediction_date", "horizon_days"],
            set_={
                "predicted_price": stmt.excluded.predicted_price,
                "predicted_low": stmt.excluded.predicted_low,
                "predicted_high": stmt.excluded.predicted_high,
                "change_pct": stmt.excluded.change_pct,
                "confidence_score": stmt.excluded.confidence_score,
                "timesfm_prediction": stmt.excluded.timesfm_prediction,
                "chronos_prediction": stmt.excluded.chronos_prediction,
                "ai_sentiment": stmt.excluded.ai_sentiment,
                "ai_sentiment_score": stmt.excluded.ai_sentiment_score,
                "ai_adjustment_pct": stmt.excluded.ai_adjustment_pct,
                "technical_signals": stmt.excluded.technical_signals,
            }
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Saved final prediction for {symbol} (horizon={horizon})")
        return True

    except Exception as e:
        logger.error(f"Failed to save final prediction for {symbol}: {e}")
        return False
