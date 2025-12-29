"""Unit tests for CacheManager."""

import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from stock_finder.config import CacheConfig
from stock_finder.data.cache import CacheManager


@pytest.fixture
def cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_config(cache_dir):
    """Create cache config for testing."""
    return CacheConfig(
        enabled=True,
        cache_dir=str(cache_dir),
        ttl_hours=24,
        max_size_gb=1.0,
    )


@pytest.fixture
def cache_manager(cache_config):
    """Create a CacheManager instance for testing."""
    return CacheManager(cache_config)


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(100)],
            "High": [102.0 + i for i in range(100)],
            "Low": [98.0 + i for i in range(100)],
            "Close": [101.0 + i for i in range(100)],
            "Volume": [1000000] * 100,
        },
        index=dates,
    )


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.cache_dir == "data/cache"
        assert config.ttl_hours == 24
        assert config.max_size_gb == 5.0

    def test_custom_values(self, cache_dir):
        """Test custom configuration values."""
        config = CacheConfig(
            enabled=False,
            cache_dir=str(cache_dir),
            ttl_hours=48,
            max_size_gb=10.0,
        )
        assert config.enabled is False
        assert config.cache_dir == str(cache_dir)
        assert config.ttl_hours == 48
        assert config.max_size_gb == 10.0


class TestCacheManager:
    """Tests for CacheManager."""

    def test_init_creates_cache_dir(self, cache_config):
        """Test that CacheManager creates the cache directory."""
        cache_dir = Path(cache_config.cache_dir)
        # Remove dir if it exists
        if cache_dir.exists():
            cache_dir.rmdir()

        manager = CacheManager(cache_config)
        assert cache_dir.exists()

    def test_generate_cache_key(self, cache_manager):
        """Test cache key generation."""
        key = cache_manager._generate_cache_key(
            ticker="AAPL",
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
        )
        assert key == "AAPL_2023-01-01_2023-12-31.parquet"

    def test_set_and_get(self, cache_manager, sample_df):
        """Test setting and getting data from cache."""
        ticker = "AAPL"
        start = date(2023, 1, 1)
        end = date(2023, 4, 10)

        # Set data
        cache_manager.set(ticker, start, end, sample_df)

        # Get data
        cached_df = cache_manager.get(ticker, start, end)

        assert cached_df is not None
        # Compare values (parquet may not preserve freq attribute)
        pd.testing.assert_frame_equal(
            cached_df.reset_index(drop=True),
            sample_df.reset_index(drop=True),
        )
        # Verify index values match
        assert list(cached_df.index) == list(sample_df.index)

    def test_get_missing_returns_none(self, cache_manager):
        """Test that getting missing data returns None."""
        result = cache_manager.get(
            ticker="MISSING",
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
        )
        assert result is None

    def test_exists(self, cache_manager, sample_df):
        """Test checking if cache entry exists."""
        ticker = "AAPL"
        start = date(2023, 1, 1)
        end = date(2023, 4, 10)

        assert not cache_manager.exists(ticker, start, end)

        cache_manager.set(ticker, start, end, sample_df)

        assert cache_manager.exists(ticker, start, end)

    def test_clear_all(self, cache_manager, sample_df):
        """Test clearing all cache entries."""
        # Add multiple entries
        cache_manager.set("AAPL", date(2023, 1, 1), date(2023, 4, 10), sample_df)
        cache_manager.set("GOOG", date(2023, 1, 1), date(2023, 4, 10), sample_df)

        assert cache_manager.exists("AAPL", date(2023, 1, 1), date(2023, 4, 10))
        assert cache_manager.exists("GOOG", date(2023, 1, 1), date(2023, 4, 10))

        cache_manager.clear()

        assert not cache_manager.exists("AAPL", date(2023, 1, 1), date(2023, 4, 10))
        assert not cache_manager.exists("GOOG", date(2023, 1, 1), date(2023, 4, 10))

    def test_clear_by_ticker(self, cache_manager, sample_df):
        """Test clearing cache entries for a specific ticker."""
        cache_manager.set("AAPL", date(2023, 1, 1), date(2023, 4, 10), sample_df)
        cache_manager.set("AAPL", date(2023, 5, 1), date(2023, 8, 10), sample_df)
        cache_manager.set("GOOG", date(2023, 1, 1), date(2023, 4, 10), sample_df)

        cache_manager.clear(ticker="AAPL")

        assert not cache_manager.exists("AAPL", date(2023, 1, 1), date(2023, 4, 10))
        assert not cache_manager.exists("AAPL", date(2023, 5, 1), date(2023, 8, 10))
        assert cache_manager.exists("GOOG", date(2023, 1, 1), date(2023, 4, 10))

    def test_get_stats(self, cache_manager, sample_df):
        """Test getting cache statistics."""
        # Initially empty
        stats = cache_manager.get_stats()
        assert stats["entry_count"] == 0
        assert stats["total_size_mb"] == 0.0

        # Add entries
        cache_manager.set("AAPL", date(2023, 1, 1), date(2023, 4, 10), sample_df)
        cache_manager.set("GOOG", date(2023, 1, 1), date(2023, 4, 10), sample_df)

        stats = cache_manager.get_stats()
        assert stats["entry_count"] == 2
        assert stats["total_size_mb"] > 0

    def test_disabled_cache_returns_none(self, cache_dir, sample_df):
        """Test that disabled cache always returns None."""
        config = CacheConfig(enabled=False, cache_dir=str(cache_dir))
        manager = CacheManager(config)

        ticker = "AAPL"
        start = date(2023, 1, 1)
        end = date(2023, 4, 10)

        # Set should be a no-op
        manager.set(ticker, start, end, sample_df)

        # Get should return None
        assert manager.get(ticker, start, end) is None

        # Exists should return False
        assert not manager.exists(ticker, start, end)


class TestCacheTTL:
    """Tests for cache TTL (time-to-live) behavior."""

    def test_expired_entry_returns_none(self, cache_dir):
        """Test that expired cache entries return None."""
        from datetime import timedelta

        config = CacheConfig(
            enabled=True,
            cache_dir=str(cache_dir),
            ttl_hours=0,  # Immediate expiration
        )
        manager = CacheManager(config)

        # Use recent dates (within the last year, so not historical)
        today = date.today()
        start = today - timedelta(days=30)
        end = today - timedelta(days=1)

        # Create a simple DataFrame for the date range
        dates = pd.date_range(start, end, freq="D")
        recent_df = pd.DataFrame(
            {
                "Open": [100.0] * len(dates),
                "High": [102.0] * len(dates),
                "Low": [98.0] * len(dates),
                "Close": [101.0] * len(dates),
                "Volume": [1000000] * len(dates),
            },
            index=dates,
        )

        manager.set("AAPL", start, end, recent_df)

        # Should return None because TTL is 0 and data is recent (not historical)
        assert manager.get("AAPL", start, end) is None

    def test_historical_data_never_expires(self, cache_dir, sample_df):
        """Test that old historical data never expires."""
        config = CacheConfig(
            enabled=True,
            cache_dir=str(cache_dir),
            ttl_hours=0,  # Would expire immediately
        )
        manager = CacheManager(config)

        # Data from 2 years ago (considered historical)
        old_start = date(2021, 1, 1)
        old_end = date(2021, 12, 31)

        manager.set("AAPL", old_start, old_end, sample_df)

        # Historical data should never expire
        result = manager.get("AAPL", old_start, old_end)
        assert result is not None


class TestCacheLRU:
    """Tests for LRU cache eviction."""

    def test_eviction_when_cache_full(self, cache_dir, sample_df):
        """Test that oldest entries are evicted when cache exceeds max size."""
        # Each parquet file for sample_df is ~5KB, so set max to ~25KB
        config = CacheConfig(
            enabled=True,
            cache_dir=str(cache_dir),
            ttl_hours=24,
            max_size_gb=0.000025,  # ~25KB, should only fit ~5 entries
        )
        manager = CacheManager(config)

        # Add many entries to exceed max size
        for i in range(10):
            ticker = f"STOCK{i}"
            manager.set(ticker, date(2023, 1, 1), date(2023, 4, 10), sample_df)

        # After eviction, total size should be under the limit
        stats = manager.get_stats()
        max_size_mb = config.max_size_gb * 1024
        # Either entry count is reduced OR total size is within limits
        assert stats["entry_count"] < 10 or stats["total_size_mb"] <= max_size_mb


class TestCachePartialHit:
    """Tests for partial cache hits."""

    def test_partial_date_range_no_hit(self, cache_manager, sample_df):
        """Test that partial date range overlap doesn't return cache hit."""
        # Cache data for Jan-April
        cache_manager.set("AAPL", date(2023, 1, 1), date(2023, 4, 10), sample_df)

        # Request Jan-June (partial overlap) - should not hit
        result = cache_manager.get("AAPL", date(2023, 1, 1), date(2023, 6, 30))
        assert result is None

    def test_subset_range_hits(self, cache_manager, sample_df):
        """Test that requesting a subset of cached range returns hit."""
        # Cache full year
        dates = pd.date_range("2023-01-01", periods=365, freq="D")
        full_year_df = pd.DataFrame(
            {
                "Open": [100.0] * 365,
                "High": [102.0] * 365,
                "Low": [98.0] * 365,
                "Close": [101.0] * 365,
                "Volume": [1000000] * 365,
            },
            index=dates,
        )
        cache_manager.set("AAPL", date(2023, 1, 1), date(2023, 12, 31), full_year_df)

        # Request a subset (should hit and return filtered data)
        result = cache_manager.get("AAPL", date(2023, 3, 1), date(2023, 6, 30))

        # Should get filtered subset
        assert result is not None
        assert result.index[0].date() >= date(2023, 3, 1)
        assert result.index[-1].date() <= date(2023, 6, 30)
