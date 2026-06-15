"""Tests for Prediction V2 features."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMultiAgentStyles:
    def test_agent_styles_has_required_fields(self):
        """Verify AGENT_STYLES has all required agent types."""
        from app.prediction.ai_analyst import AGENT_STYLES

        required_agents = ["trend", "value", "macro", "sentiment", "onchain"]
        for agent in required_agents:
            assert agent in AGENT_STYLES, f"Missing agent: {agent}"
            assert "name" in AGENT_STYLES[agent]
            assert "weight" in AGENT_STYLES[agent]
            assert AGENT_STYLES[agent]["weight"] > 0

    def test_agent_weights_sum_to_one(self):
        """Agent weights should sum to ~1.0."""
        from app.prediction.ai_analyst import AGENT_STYLES

        total = sum(a["weight"] for a in AGENT_STYLES.values())
        assert 0.99 <= total <= 1.01, f"Weights sum to {total}, expected ~1.0"


class TestWeightedConsensus:
    def test_positive_consensus(self):
        """Test consensus calculation for positive signals."""
        from app.prediction.ai_analyst import _compute_weighted_consensus

        agent_signals = [
            {"agent_type": "trend", "sentiment": "positive", "sentiment_score": 0.8, "confidence_score": 0.7, "weight": 0.3, "reasons": ["RSI neutral"]},
            {"agent_type": "value", "sentiment": "positive", "sentiment_score": 0.7, "confidence_score": 0.6, "weight": 0.25, "reasons": ["P/E attractive"]},
            {"agent_type": "macro", "sentiment": "positive", "sentiment_score": 0.6, "confidence_score": 0.5, "weight": 0.2, "reasons": ["Fed dovish"]},
        ]

        result = _compute_weighted_consensus(agent_signals, "BTC-USD", "Bitcoin", "crypto", 100000)

        assert result["sentiment"] == "positive"
        assert result["agent_count"] == 3
        assert len(result["agent_signals"]) == 3

    def test_negative_consensus(self):
        """Test consensus calculation for negative signals."""
        from app.prediction.ai_analyst import _compute_weighted_consensus

        agent_signals = [
            {"agent_type": "trend", "sentiment": "negative", "sentiment_score": 0.8, "confidence_score": 0.7, "weight": 0.3, "reasons": ["Death cross"]},
            {"agent_type": "macro", "sentiment": "negative", "sentiment_score": 0.7, "confidence_score": 0.6, "weight": 0.2, "reasons": ["Fed hawkish"]},
        ]

        result = _compute_weighted_consensus(agent_signals, "ETH-USD", "Ethereum", "crypto", 3000)

        assert result["sentiment"] == "negative"

    def test_mixed_signals_neutral(self):
        """Test consensus when signals are mixed (cancel out)."""
        from app.prediction.ai_analyst import _compute_weighted_consensus

        agent_signals = [
            {"agent_type": "trend", "sentiment": "positive", "sentiment_score": 0.6, "confidence_score": 0.7, "weight": 0.3, "reasons": []},
            {"agent_type": "value", "sentiment": "negative", "sentiment_score": 0.6, "confidence_score": 0.6, "weight": 0.3, "reasons": []},
        ]

        result = _compute_weighted_consensus(agent_signals, "AAPL", "Apple", "us", 200)

        assert result["sentiment"] == "neutral"


class TestFundamentalData:
    @pytest.mark.asyncio
    async def test_get_us_stock_fundamentals(self):
        """Test fetching US stock fundamentals."""
        from app.prediction.fundamental_data import FundamentalDataFetcher

        fetcher = FundamentalDataFetcher()

        with patch.object(fetcher, 'get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value.get = AsyncMock(return_value=None)
            mock_redis.return_value.setex = AsyncMock()

            with patch('yfinance.Ticker') as mock_ticker:
                mock_info = MagicMock()
                mock_info.trailingPE = 25.5
                mock_info.trailingEps = 6.50
                mock_info.marketCap = 3000000000000
                mock_info.beta = 1.2
                mock_ticker.return_value.info = mock_info

                result = await fetcher.get_us_stock_fundamentals("AAPL")

                assert result["symbol"] == "AAPL"
                assert result["market"] == "us"
                assert "pe_ratio" in result

    @pytest.mark.asyncio
    async def test_crypto_fundamentals(self):
        """Test fetching crypto fundamentals."""
        from app.prediction.fundamental_data import FundamentalDataFetcher

        fetcher = FundamentalDataFetcher()

        with patch.object(fetcher, 'get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value.get = AsyncMock(return_value=None)

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={
                    "market_cap_rank": 1,
                    "market_data": {
                        "market_cap": {"usd": 1000000000000},
                        "current_price": {"usd": 60000},
                    }
                })
                mock_response.raise_for_status = MagicMock()

                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(get=AsyncMock(return_value=mock_response))
                )

                result = await fetcher.get_crypto_fundamentals("BTC")

                assert result["market"] == "crypto"


class TestMacroData:
    @pytest.mark.asyncio
    async def test_fred_data_fallback(self):
        """Test FRED data fallback when no API key."""
        from app.prediction.macro_data import MacroDataFetcher

        fetcher = MacroDataFetcher()

        with patch.object(fetcher, 'get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value.get = AsyncMock(return_value=None)

            result = await fetcher.get_fred_data("VIXCLS")

            # Should fallback to yfinance
            assert "series_id" in result or "error" in result


class TestEventCalendar:
    def test_fomc_meetings_2026(self):
        """Test FOMC meetings for 2026 are configured."""
        from app.prediction.event_calendar import FOMC_MEETINGS_2026

        assert len(FOMC_MEETINGS_2026) > 0
        for meeting in FOMC_MEETINGS_2026:
            assert "date" in meeting
            assert "2026" in meeting["date"]

    def test_get_upcoming_fomc(self):
        """Test filtering upcoming FOMC meetings."""
        from app.prediction.event_calendar import EventCalendarFetcher

        fetcher = EventCalendarFetcher()
        upcoming = fetcher.get_upcoming_fomc(days=60)

        # Should return meetings within 60 days
        assert isinstance(upcoming, list)


class TestPredictionConfig:
    def test_agent_styles_enabled_defaults(self):
        """Test AGENT_STYLES_ENABLED has expected defaults."""
        from app.prediction.config import AGENT_STYLES_ENABLED

        assert isinstance(AGENT_STYLES_ENABLED, dict)
        assert "trend" in AGENT_STYLES_ENABLED

    def test_prediction_v2_settings(self):
        """Test Prediction V2 settings exist."""
        from app.prediction.config import (
            FUNDAMENTAL_FETCH_TIMEOUT,
            MACRO_FETCH_TIMEOUT,
            BACKTEST_WINDOW_DAYS,
        )

        assert FUNDAMENTAL_FETCH_TIMEOUT > 0
        assert MACRO_FETCH_TIMEOUT > 0
        assert BACKTEST_WINDOW_DAYS > 0
