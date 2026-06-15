"""
Chronos-2 model for probabilistic time series forecasting.
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model_instance = None
_model_loaded = False


def load_chronos_model() -> Optional[object]:
    """
    Load Chronos-2 model from amazon/chronos-bolt-large.
    """
    global _model_instance, _model_loaded

    if _model_loaded:
        return _model_instance

    try:
        import torch
        from chronos import ChronosPipeline

        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        logger.info(f"Loading Chronos-2 on {device}")

        _model_instance = ChronosPipeline.from_pretrained(
            "amazon/chronos-bolt-large",
            device=device,
            torch_dtype=torch.float32,
        )

        _model_loaded = True
        logger.info("Chronos-2 model loaded successfully")
        return _model_instance

    except ImportError:
        logger.warning("Chronos not available, using simple forecasting")
        _model_loaded = True
        return None
    except Exception as e:
        logger.error(f"Failed to load Chronos-2: {e}")
        _model_loaded = True
        return None


class ChronosModel:
    """
    Singleton wrapper for Chronos-2 model.
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
            self._model = load_chronos_model()
            self._loaded = True
        return self._model

    def predict(
        self,
        close_prices: list[float],
        horizon: int = 7,
    ) -> list[dict]:
        """
        Generate forecast using Chronos-2.

        Args:
            close_prices: List of historical close prices
            horizon: Number of days to forecast

        Returns:
            List of predictions with price, low, high
        """
        if self.model is None:
            return self._simple_forecast(close_prices, horizon)

        try:
            return self._chronos_forecast(close_prices, horizon)
        except Exception as e:
            logger.error(f"Chronos forecast failed: {e}")
            return self._simple_forecast(close_prices, horizon)

    def _chronos_forecast(
        self,
        close_prices: list[float],
        horizon: int,
    ) -> list[dict]:
        """Generate forecast using Chronos-2."""
        import torch

        context = torch.tensor(close_prices[-512:]).unsqueeze(0)

        forecast = self.model.predict(
            context,
            prediction_length=horizon,
            num_samples=100,
        )

        forecast_array = forecast.sample().numpy()[0]

        predictions = []
        for i in range(horizon):
            sample_values = forecast_array[:, i]
            mean_price = float(np.mean(sample_values))
            low_price = float(np.percentile(sample_values, 10))
            high_price = float(np.percentile(sample_values, 90))

            predictions.append({
                "price": round(mean_price, 2),
                "low": round(low_price, 2),
                "high": round(high_price, 2),
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


chronos_model = ChronosModel()
