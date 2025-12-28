"""Shared test fixtures."""

from datetime import date

import pandas as pd
import pytest

from stock_finder.config import DataConfig, ScanConfig
from stock_finder.data.base import DataProvider
from stock_finder.models.results import ScanResult, StockData


class MockDataProvider(DataProvider):
    """Mock data provider for testing."""

    def __init__(self, data: dict[str, pd.DataFrame] | None = None):
        """
        Initialize with optional predefined data.

        Args:
            data: Dict mapping ticker -> DataFrame with price data
        """
        self.data = data or {}
        self.call_count = 0

    def get_historical(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> StockData | None:
        self.call_count += 1

        if ticker not in self.data:
            return None

        df = self.data[ticker]
        # Filter by date range
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
        filtered = df[mask]

        if filtered.empty:
            return None

        return StockData(ticker=ticker, data=filtered)

    def get_current_price(self, ticker: str) -> float | None:
        if ticker not in self.data:
            return None
        return self.data[ticker]["Close"].iloc[-1]


@pytest.fixture
def mock_provider() -> MockDataProvider:
    """Create a mock data provider with test data."""
    # Create test data for a few tickers
    # Use recent dates to fall within the 3-year lookback period
    dates = pd.date_range("2023-01-01", periods=500, freq="D")

    # GAINER: Stock that goes from 10 to 70 (600% gain)
    gainer_prices = [10] * 100 + list(range(10, 70, 1)) + [70] * 340
    gainer_df = pd.DataFrame(
        {
            "Open": gainer_prices,
            "High": [p * 1.02 for p in gainer_prices],
            "Low": [p * 0.98 for p in gainer_prices],
            "Close": gainer_prices,
            "Volume": [1000000] * 500,
        },
        index=dates,
    )

    # LOSER: Stock that declines from 100 to 50 (no gain)
    loser_prices = list(range(100, 50, -1)) + [50] * 450
    loser_df = pd.DataFrame(
        {
            "Open": loser_prices,
            "High": [p * 1.02 for p in loser_prices],
            "Low": [p * 0.98 for p in loser_prices],
            "Close": loser_prices,
            "Volume": [500000] * 500,
        },
        index=dates,
    )

    # FLAT: Stock that stays flat around 50
    flat_prices = [50 + (i % 5 - 2) for i in range(500)]
    flat_df = pd.DataFrame(
        {
            "Open": flat_prices,
            "High": [p * 1.01 for p in flat_prices],
            "Low": [p * 0.99 for p in flat_prices],
            "Close": flat_prices,
            "Volume": [200000] * 500,
        },
        index=dates,
    )

    return MockDataProvider({
        "GAINER": gainer_df,
        "LOSER": loser_df,
        "FLAT": flat_df,
    })


@pytest.fixture
def scan_config() -> ScanConfig:
    """Create a scan config for testing."""
    return ScanConfig(min_gain_pct=500, lookback_years=3)


@pytest.fixture
def data_config() -> DataConfig:
    """Create a data config for testing."""
    return DataConfig(cache_enabled=False, rate_limit_delay=0)


@pytest.fixture
def sample_scan_result() -> ScanResult:
    """Create a sample scan result for testing."""
    return ScanResult(
        ticker="TEST",
        gain_pct=600.0,
        low_date=date(2022, 1, 15),
        high_date=date(2022, 6, 15),
        low_price=10.0,
        high_price=70.0,
        current_price=65.0,
        days_to_peak=100,
    )
