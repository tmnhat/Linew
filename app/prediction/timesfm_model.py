"""
TimesFM 2.5 model for price forecasting.
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model_instance = None
_model_loaded = False


def load_timesfm_model() -> Optional[object]:
    """
    Load TimesFM 2.5 model.
    Uses MPS for Apple Silicon, falls back to CPU.
    """
    global _model_instance, _model_loaded

    if _model_loaded:
        return _model_instance

    try:
        import torch
        from timesfm import TimesFm

        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        logger.info(f"Loading TimesFM 2.5 on {device}")

        _model_instance = TimesFm(
            checkpoint=-1,
            horizon_len=30,
            context_len=512,
            backend=device,
        )

        _model_loaded = True
        logger.info("TimesFM model loaded successfully")
        return _model_instance

    except ImportError:
        logger.warning("TimesFM not available, using simple forecasting")
        _model_loaded = True
        return None
    except Exception as e:
        logger.error(f"Failed to load TimesFM: {e}")
        _model_loaded = True
        return None


class TimesFMModel:
    """
    Singleton wrapper for TimesFM model.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
            cls._instance._loaded = False
        return cls._instance

    @property
    def model(self):
        if not self._loaded:
            self._model = load_timesfm_model()
            self._loaded = True
        return self._model

    def predict(
        self,
        close_prices: list[float],
        horizon: int = 7,
    ) -> list[dict]:
        """
        Generate forecast using TimesFM.

        Args:
            close_prices: List of historical close prices
            horizon: Number of days to forecast

        Returns:
            List of predictions with price, low, high
        """
        if self.model is None:
            return self._simple_forecast(close_prices, horizon)

        try:
            return self._timesfm_forecast(close_prices, horizon)
        except Exception as e:
            logger.error(f"TimesFM forecast failed: {e}")
            return self._simple_forecast(close_prices, horizon)

    def _timesfm_forecast(
        self,
        close_prices: list[float],
        horizon: int,
    ) -> list[dict]:
        """Generate forecast using TimesFM."""
        import torch

        input_data = np.array(close_prices[-512:], dtype=np.float32)

        context = torch.tensor(input_data).unsqueeze(0).unsqueeze(-1)

        with torch.no_grad():
            output = self.model(context.permute(0, 2, 1), horizon)

        point_forecast = output.point_forecast[0, 0, :].numpy()
        quantile_10 = output.quantile_forecast[0, 0, 0, :].numpy()
        quantile_90 = output.quantile_forecast[0, 0, 2, :].numpy()

        predictions = []
        for i in range(min(horizon, len(point_forecast))):
            predictions.append({
                "price": float(point_forecast[i]),
                "low": float(quantile_10[i]),
                "high": float(quantile_90[i]),
            })

        return predictions

    def _simple_forecast(
        self,
        close_prices: list[float],
        horizon: int,
    ) -> list[dict]:
        """Simple moving average forecast as fallback."""
        recent = close_prices[-30:]
        mean_price = np.mean(recent)
        std_price = np.std(recent)

        predictions = []
        for i in range(horizon):
            uncertainty = (i + 1) * 0.01 * std_price
            predictions.append({
                "price": round(mean_price, 2),
                "low": round(mean_price - uncertainty, 2),
                "high": round(mean_price + uncertainty, 2),
            })

        return predictions


timesfm_model = TimesFMModel()
