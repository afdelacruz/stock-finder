"""Integration tests for Yahoo Finance provider."""

from datetime import date, timedelta

import pytest

from stock_finder.config import DataConfig
from stock_finder.data.yfinance_provider import YFinanceProvider


@pytest.mark.integration
class TestYFinanceProvider:
    """Integration tests for YFinanceProvider (requires network)."""

    @pytest.fixture
    def provider(self):
        """Create a provider with minimal rate limiting."""
        config = DataConfig(rate_limit_delay=0.2)
        return YFinanceProvider(config)

    def test_get_historical_aapl(self, provider):
        """Should fetch AAPL historical data."""
        end = date.today()
        start = end - timedelta(days=30)

        result = provider.get_historical("AAPL", start, end)

        assert result is not None
        assert result.ticker == "AAPL"
        assert not result.data.empty
        assert "Close" in result.data.columns

    def test_get_historical_invalid_ticker(self, provider):
        """Should return None for invalid ticker."""
        end = date.today()
        start = end - timedelta(days=30)

        result = provider.get_historical("INVALIDTICKER123456", start, end)

        # yfinance may return empty data or None for invalid tickers
        assert result is None or result.data.empty

    def test_get_current_price(self, provider):
        """Should get current price for known stock."""
        price = provider.get_current_price("MSFT")

        assert price is not None
        assert price > 0

    def test_data_has_expected_columns(self, provider):
        """Historical data should have OHLCV columns."""
        end = date.today()
        start = end - timedelta(days=30)

        result = provider.get_historical("GOOGL", start, end)

        assert result is not None
        df = result.data
        assert "Open" in df.columns
        assert "High" in df.columns
        assert "Low" in df.columns
        assert "Close" in df.columns
        assert "Volume" in df.columns
