"""Integration tests for cache with data providers."""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from stock_finder.config import CacheConfig, DataConfig
from stock_finder.data.base import DataProvider
from stock_finder.data.cache import CacheManager
from stock_finder.data.cached_provider import CachedDataProvider
from stock_finder.models.results import StockData


class MockDataProvider(DataProvider):
    """Mock provider that tracks call counts."""

    def __init__(self):
        self.call_count = 0
        self.historical_calls: list[tuple[str, date, date]] = []

    def get_historical(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> StockData | None:
        self.call_count += 1
        self.historical_calls.append((ticker, start, end))

        # Generate fake data
        dates = pd.date_range(start, end, freq="D")
        df = pd.DataFrame(
            {
                "Open": [100.0] * len(dates),
                "High": [102.0] * len(dates),
                "Low": [98.0] * len(dates),
                "Close": [101.0] * len(dates),
                "Volume": [1000000] * len(dates),
            },
            index=dates,
        )
        return StockData(ticker=ticker, data=df)

    def get_current_price(self, ticker: str) -> float | None:
        return 100.0


@pytest.fixture
def cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_config(cache_dir):
    """Create cache config."""
    return CacheConfig(
        enabled=True,
        cache_dir=str(cache_dir),
        ttl_hours=24,
        max_size_gb=1.0,
    )


@pytest.fixture
def cache_manager(cache_config):
    """Create cache manager."""
    return CacheManager(cache_config)


@pytest.fixture
def mock_provider():
    """Create mock provider."""
    return MockDataProvider()


@pytest.fixture
def cached_provider(mock_provider, cache_manager):
    """Create cached provider wrapping mock."""
    return CachedDataProvider(mock_provider, cache_manager)


class TestCachedDataProvider:
    """Tests for CachedDataProvider wrapper."""

    def test_cache_miss_calls_provider(self, cached_provider, mock_provider):
        """Test that cache miss calls the underlying provider."""
        result = cached_provider.get_historical(
            "AAPL",
            date(2023, 1, 1),
            date(2023, 3, 31),
        )

        assert result is not None
        assert mock_provider.call_count == 1

    def test_cache_hit_skips_provider(self, cached_provider, mock_provider):
        """Test that cache hit returns cached data without calling provider."""
        # First call - cache miss
        result1 = cached_provider.get_historical(
            "AAPL",
            date(2023, 1, 1),
            date(2023, 3, 31),
        )

        # Second call - should be cache hit
        result2 = cached_provider.get_historical(
            "AAPL",
            date(2023, 1, 1),
            date(2023, 3, 31),
        )

        assert result1 is not None
        assert result2 is not None
        assert mock_provider.call_count == 1  # Only called once

    def test_different_tickers_separate_cache(self, cached_provider, mock_provider):
        """Test that different tickers use separate cache entries."""
        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 3, 31))
        cached_provider.get_historical("GOOG", date(2023, 1, 1), date(2023, 3, 31))

        assert mock_provider.call_count == 2

    def test_different_date_ranges_separate_cache(self, cached_provider, mock_provider):
        """Test that different date ranges use separate cache entries."""
        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 3, 31))
        cached_provider.get_historical("AAPL", date(2023, 4, 1), date(2023, 6, 30))

        assert mock_provider.call_count == 2

    def test_subset_date_range_uses_superset_cache(self, cached_provider, mock_provider):
        """Test that requesting a subset of cached range hits the cache."""
        # Cache full year
        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 12, 31))

        # Request a subset
        result = cached_provider.get_historical(
            "AAPL",
            date(2023, 3, 1),
            date(2023, 6, 30),
        )

        assert result is not None
        assert mock_provider.call_count == 1  # Only first call hits provider

    def test_current_price_not_cached(self, cached_provider, mock_provider):
        """Test that current price is not cached (real-time data)."""
        price1 = cached_provider.get_current_price("AAPL")
        price2 = cached_provider.get_current_price("AAPL")

        assert price1 == 100.0
        assert price2 == 100.0
        # Current price should always call provider

    def test_cache_stats_after_operations(self, cached_provider, cache_manager):
        """Test that cache stats reflect operations."""
        # Initial stats
        stats = cache_manager.get_stats()
        assert stats["entry_count"] == 0

        # Add some data
        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 3, 31))
        cached_provider.get_historical("GOOG", date(2023, 1, 1), date(2023, 3, 31))

        stats = cache_manager.get_stats()
        assert stats["entry_count"] == 2
        assert stats["total_size_mb"] > 0


class TestCacheDisabled:
    """Tests for cache disabled behavior."""

    def test_disabled_cache_always_calls_provider(self, cache_dir, mock_provider):
        """Test that disabled cache always calls the underlying provider."""
        config = CacheConfig(enabled=False, cache_dir=str(cache_dir))
        cache_manager = CacheManager(config)
        cached_provider = CachedDataProvider(mock_provider, cache_manager)

        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 3, 31))
        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 3, 31))

        assert mock_provider.call_count == 2


class TestCacheWithNoCache:
    """Tests for --no-cache flag behavior."""

    def test_bypass_cache_flag(self, cached_provider, mock_provider):
        """Test bypassing cache with flag."""
        # First call - populates cache
        cached_provider.get_historical("AAPL", date(2023, 1, 1), date(2023, 3, 31))

        # Second call with bypass - should hit provider
        cached_provider.get_historical(
            "AAPL",
            date(2023, 1, 1),
            date(2023, 3, 31),
            bypass_cache=True,
        )

        assert mock_provider.call_count == 2

    def test_bypass_updates_cache(self, cached_provider, mock_provider, cache_manager):
        """Test that bypass still updates the cache."""
        # Bypass cache
        cached_provider.get_historical(
            "AAPL",
            date(2023, 1, 1),
            date(2023, 3, 31),
            bypass_cache=True,
        )

        # Cache should be populated
        assert cache_manager.exists("AAPL", date(2023, 1, 1), date(2023, 3, 31))


class TestCacheIntegration:
    """Full integration tests simulating real usage patterns."""

    def test_scan_then_score_uses_cache(self, cached_provider, mock_provider):
        """Test that scoring after scanning uses cached data."""
        # Simulate scan operation
        tickers = ["AAPL", "GOOG", "MSFT"]
        for ticker in tickers:
            cached_provider.get_historical(ticker, date(2023, 1, 1), date(2023, 12, 31))

        initial_calls = mock_provider.call_count
        assert initial_calls == 3

        # Simulate scoring - same data, should hit cache
        for ticker in tickers:
            cached_provider.get_historical(ticker, date(2023, 1, 1), date(2023, 12, 31))

        # No additional calls
        assert mock_provider.call_count == initial_calls

    def test_multiple_sessions_use_cache(self, cache_config, mock_provider):
        """Test that cache persists across 'sessions' (new instances)."""
        # First "session"
        cache_manager1 = CacheManager(cache_config)
        provider1 = CachedDataProvider(mock_provider, cache_manager1)
        provider1.get_historical("AAPL", date(2023, 1, 1), date(2023, 12, 31))

        assert mock_provider.call_count == 1

        # Second "session" - new cache manager, same directory
        cache_manager2 = CacheManager(cache_config)
        provider2 = CachedDataProvider(mock_provider, cache_manager2)
        result = provider2.get_historical("AAPL", date(2023, 1, 1), date(2023, 12, 31))

        # Should hit cache, no new API call
        assert result is not None
        assert mock_provider.call_count == 1
