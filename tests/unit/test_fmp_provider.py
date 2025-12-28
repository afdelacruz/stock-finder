"""Tests for FMP provider."""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from stock_finder.data.fmp_provider import FMPProvider, Quote
from stock_finder.config import FMPConfig


class TestFMPProvider:
    """Tests for FMPProvider class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock FMP config."""
        return FMPConfig(api_key="test_key", batch_size=50)

    @pytest.fixture
    def provider(self, mock_config):
        """Create a provider with mock config."""
        return FMPProvider(config=mock_config)

    def test_init_without_api_key_raises(self):
        """Test that init raises without API key."""
        config = FMPConfig(api_key=None)
        with pytest.raises(ValueError, match="FMP API key not found"):
            FMPProvider(config=config)

    def test_init_from_env(self):
        """Test loading API key from environment."""
        with patch.dict(os.environ, {"FMP_API_KEY": "env_test_key"}):
            config = FMPConfig.from_env()
            assert config.api_key == "env_test_key"

    def test_parse_quote(self, provider):
        """Test parsing quote data."""
        raw_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "changesPercentage": 1.5,
            "dayLow": 148.0,
            "dayHigh": 152.0,
            "yearLow": 120.0,
            "yearHigh": 180.0,
            "marketCap": 2500000000000,
            "avgVolume": 50000000,
            "volume": 45000000,
            "priceAvg50": 145.0,
            "priceAvg200": 140.0,
            "exchange": "NASDAQ",
            "name": "Apple Inc.",
        }

        quote = provider._parse_quote(raw_data)

        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price == 150.0
        assert quote.market_cap == 2500000000000
        assert quote.price_avg_50 == 145.0

    @patch("requests.get")
    def test_get_quote(self, mock_get, provider):
        """Test getting a single quote."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "symbol": "AAPL",
                "price": 150.0,
                "changesPercentage": 1.5,
                "dayLow": 148.0,
                "dayHigh": 152.0,
                "yearLow": 120.0,
                "yearHigh": 180.0,
                "marketCap": 2500000000000,
                "avgVolume": 50000000,
                "volume": 45000000,
                "priceAvg50": 145.0,
                "priceAvg200": 140.0,
                "exchange": "NASDAQ",
                "name": "Apple Inc.",
            }
        ]
        mock_get.return_value = mock_response

        quote = provider.get_quote("AAPL")

        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price == 150.0
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_historical(self, mock_get, provider):
        """Test getting historical data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "historical": [
                {"date": "2024-01-03", "open": 148.0, "high": 150.0, "low": 147.0, "close": 149.0, "volume": 1000000},
                {"date": "2024-01-02", "open": 147.0, "high": 149.0, "low": 146.0, "close": 148.0, "volume": 900000},
            ],
        }
        mock_get.return_value = mock_response

        result = provider.get_historical("AAPL", date(2024, 1, 1), date(2024, 1, 5))

        assert result is not None
        assert result.ticker == "AAPL"
        assert len(result.data) == 2
        assert "Close" in result.data.columns
        assert "Volume" in result.data.columns

    @patch("requests.get")
    def test_get_quotes_batch(self, mock_get, provider):
        """Test batch quote fetching."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"symbol": "AAPL", "price": 150.0, "changesPercentage": 1.5, "dayLow": 148.0, "dayHigh": 152.0,
             "yearLow": 120.0, "yearHigh": 180.0, "marketCap": 2500000000000, "avgVolume": 50000000,
             "volume": 45000000, "priceAvg50": 145.0, "priceAvg200": 140.0, "exchange": "NASDAQ", "name": "Apple"},
            {"symbol": "NVDA", "price": 500.0, "changesPercentage": 2.0, "dayLow": 495.0, "dayHigh": 510.0,
             "yearLow": 300.0, "yearHigh": 550.0, "marketCap": 1200000000000, "avgVolume": 40000000,
             "volume": 35000000, "priceAvg50": 480.0, "priceAvg200": 400.0, "exchange": "NASDAQ", "name": "NVIDIA"},
        ]
        mock_get.return_value = mock_response

        quotes = provider.get_quotes_batch(["AAPL", "NVDA"])

        assert len(quotes) == 2
        assert "AAPL" in quotes
        assert "NVDA" in quotes
        assert quotes["AAPL"].price == 150.0
        assert quotes["NVDA"].price == 500.0


@pytest.mark.integration
class TestFMPProviderIntegration:
    """Integration tests that hit real FMP API (requires FMP_API_KEY env var)."""

    @pytest.fixture
    def provider(self):
        """Create provider from environment."""
        api_key = os.environ.get("FMP_API_KEY")
        if not api_key:
            pytest.skip("FMP_API_KEY not set")
        return FMPProvider()

    def test_real_quote(self, provider):
        """Test getting a real quote."""
        quote = provider.get_quote("AAPL")
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price > 0
        assert quote.market_cap > 0

    def test_real_batch_quotes(self, provider):
        """Test batch quotes with real API."""
        quotes = provider.get_quotes_batch(["AAPL", "NVDA", "TSLA"])
        assert len(quotes) >= 3
        for symbol in ["AAPL", "NVDA", "TSLA"]:
            assert symbol in quotes

    def test_real_historical(self, provider):
        """Test historical data with real API."""
        result = provider.get_historical("AAPL", date(2024, 1, 1), date(2024, 3, 1))
        assert result is not None
        assert len(result.data) > 30  # Should have ~40 trading days
