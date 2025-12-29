"""Cached data provider wrapper."""

import logging
from datetime import date

from stock_finder.data.base import DataProvider
from stock_finder.data.cache import CacheManager
from stock_finder.models.results import StockData

logger = logging.getLogger(__name__)


class CachedDataProvider(DataProvider):
    """
    A wrapper that adds disk caching to any DataProvider.

    Caches historical data to disk using Parquet format for efficient
    storage and retrieval. Subsequent requests for the same data
    return cached results instead of making API calls.
    """

    def __init__(self, provider: DataProvider, cache_manager: CacheManager):
        """
        Initialize the cached provider.

        Args:
            provider: The underlying data provider to wrap
            cache_manager: Cache manager for disk caching
        """
        self.provider = provider
        self.cache = cache_manager

    def get_historical(
        self,
        ticker: str,
        start: date,
        end: date,
        bypass_cache: bool = False,
    ) -> StockData | None:
        """
        Fetch historical OHLCV data, using cache when available.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date
            bypass_cache: If True, skip cache lookup (but still update cache)

        Returns:
            StockData with historical prices, or None if data unavailable
        """
        # Check cache first (unless bypassed)
        if not bypass_cache:
            cached_df = self.cache.get(ticker, start, end)
            if cached_df is not None:
                logger.debug(f"Cache HIT for {ticker} ({start} to {end})")
                return StockData(ticker=ticker, data=cached_df)

        # Cache miss - fetch from provider
        logger.debug(f"Cache MISS for {ticker} ({start} to {end})")
        result = self.provider.get_historical(ticker, start, end)

        # Cache the result
        if result is not None:
            self.cache.set(ticker, start, end, result.data)

        return result

    def get_current_price(self, ticker: str) -> float | None:
        """
        Get the current/latest price for a ticker.

        Note: Current prices are NOT cached as they change frequently.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
        # Current prices are not cached - they're real-time data
        return self.provider.get_current_price(ticker)

    def get_historical_df(self, ticker: str, start: date, end: date):
        """Get historical data as DataFrame (convenience method)."""
        result = self.get_historical(ticker, start, end)
        return result.data if result else None
