"""Tests for prediction data fetcher."""
import pytest
from unittest.mock import patch, MagicMock


class TestDetectMarket:
    def test_detect_crypto_usdt_suffix(self):
        from app.prediction.data_fetcher import detect_market
        assert detect_market("BTCUSDT") == "crypto"
        assert detect_market("ETHUSDT") == "crypto"

    def test_detect_crypto_dash_usd(self):
        from app.prediction.data_fetcher import detect_market
        assert detect_market("BTC-USD") == "crypto"
        assert detect_market("ETH-USD") == "crypto"

    def test_detect_vn_known_symbol(self):
        from app.prediction.data_fetcher import detect_market
        assert detect_market("FPT") == "vn"
        assert detect_market("VNM") == "vn"

    def test_detect_us_default(self):
        from app.prediction.data_fetcher import detect_market
        assert detect_market("AAPL") == "us"
        assert detect_market("GOOGL") == "us"
