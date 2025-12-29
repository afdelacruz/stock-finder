"""Disk-based caching for historical stock data."""

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from stock_finder.config import CacheConfig

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages disk-based caching of historical stock data.

    Uses Parquet format for efficient storage and retrieval.
    Implements TTL-based expiration and LRU eviction.
    """

    # Data older than this is considered historical and never expires
    HISTORICAL_THRESHOLD_DAYS = 365

    def __init__(self, config: CacheConfig):
        """
        Initialize the cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self.cache_dir = Path(config.cache_dir)

        if config.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> str:
        """
        Generate a cache key for the given parameters.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            Cache key string (filename)
        """
        return f"{ticker}_{start.isoformat()}_{end.isoformat()}.parquet"

    def _get_cache_path(self, key: str) -> Path:
        """Get the full path for a cache key."""
        return self.cache_dir / key

    def _is_historical_data(self, end: date) -> bool:
        """
        Check if the data is considered historical (old enough to never expire).

        Args:
            end: End date of the data range

        Returns:
            True if data is historical and should never expire
        """
        threshold = date.today() - timedelta(days=self.HISTORICAL_THRESHOLD_DAYS)
        return end < threshold

    def _is_expired(self, cache_path: Path, end: date) -> bool:
        """
        Check if a cache entry has expired.

        Args:
            cache_path: Path to the cache file
            end: End date of the cached data

        Returns:
            True if the cache entry has expired
        """
        # Historical data never expires
        if self._is_historical_data(end):
            return False

        # Check TTL for recent data
        if self.config.ttl_hours <= 0:
            return True

        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        max_age = timedelta(hours=self.config.ttl_hours)

        return age > max_age

    def _find_superset_cache(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> tuple[Path, date, date] | None:
        """
        Find a cached entry that contains the requested date range.

        Args:
            ticker: Stock ticker symbol
            start: Requested start date
            end: Requested end date

        Returns:
            Tuple of (cache_path, cached_start, cached_end) or None
        """
        pattern = f"{ticker}_*.parquet"
        for cache_file in self.cache_dir.glob(pattern):
            try:
                # Parse the filename to get date range
                name = cache_file.stem  # e.g., "AAPL_2023-01-01_2023-12-31"
                parts = name.split("_")
                if len(parts) != 3:
                    continue

                cached_start = date.fromisoformat(parts[1])
                cached_end = date.fromisoformat(parts[2])

                # Check if cached range contains requested range
                if cached_start <= start and cached_end >= end:
                    return cache_file, cached_start, cached_end

            except (ValueError, IndexError):
                continue

        return None

    def get(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> pd.DataFrame | None:
        """
        Get cached data for the given ticker and date range.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            Cached DataFrame or None if not found/expired
        """
        if not self.config.enabled:
            return None

        # First, check for exact match
        key = self._generate_cache_key(ticker, start, end)
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            if self._is_expired(cache_path, end):
                logger.debug(f"Cache expired for {ticker} ({start} to {end})")
                cache_path.unlink()
                return None

            try:
                df = pd.read_parquet(cache_path)
                logger.debug(f"Cache HIT for {ticker} ({start} to {end})")
                return df
            except Exception as e:
                logger.warning(f"Failed to read cache for {ticker}: {e}")
                return None

        # Check for superset cache (larger date range that contains this one)
        superset = self._find_superset_cache(ticker, start, end)
        if superset:
            cache_path, cached_start, cached_end = superset

            if self._is_expired(cache_path, cached_end):
                logger.debug(f"Cache expired for {ticker} superset")
                cache_path.unlink()
                return None

            try:
                df = pd.read_parquet(cache_path)
                # Filter to requested date range
                mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
                filtered = df[mask]
                logger.debug(
                    f"Cache HIT (subset) for {ticker} ({start} to {end}) "
                    f"from cached ({cached_start} to {cached_end})"
                )
                return filtered
            except Exception as e:
                logger.warning(f"Failed to read cache for {ticker}: {e}")
                return None

        logger.debug(f"Cache MISS for {ticker} ({start} to {end})")
        return None

    def set(
        self,
        ticker: str,
        start: date,
        end: date,
        data: pd.DataFrame,
    ) -> None:
        """
        Cache data for the given ticker and date range.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date
            data: DataFrame to cache
        """
        if not self.config.enabled:
            return

        # Enforce size limit before adding new entry
        self._enforce_size_limit()

        key = self._generate_cache_key(ticker, start, end)
        cache_path = self._get_cache_path(key)

        try:
            data.to_parquet(cache_path, index=True)
            logger.debug(f"Cached {ticker} ({start} to {end})")
        except Exception as e:
            logger.warning(f"Failed to cache {ticker}: {e}")

    def exists(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> bool:
        """
        Check if data exists in cache (and is not expired).

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            True if valid cache entry exists
        """
        if not self.config.enabled:
            return False

        key = self._generate_cache_key(ticker, start, end)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            # Also check for superset
            return self._find_superset_cache(ticker, start, end) is not None

        if self._is_expired(cache_path, end):
            return False

        return True

    def clear(self, ticker: str | None = None) -> int:
        """
        Clear cache entries.

        Args:
            ticker: If provided, only clear entries for this ticker.
                   If None, clear all entries.

        Returns:
            Number of entries cleared
        """
        if not self.config.enabled:
            return 0

        pattern = f"{ticker}_*.parquet" if ticker else "*.parquet"
        count = 0

        for cache_file in self.cache_dir.glob(pattern):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")

        logger.info(f"Cleared {count} cache entries")
        return count

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.config.enabled or not self.cache_dir.exists():
            return {
                "enabled": self.config.enabled,
                "entry_count": 0,
                "total_size_mb": 0.0,
                "oldest_entry": None,
                "newest_entry": None,
            }

        files = list(self.cache_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files)

        oldest = None
        newest = None
        if files:
            sorted_files = sorted(files, key=lambda f: f.stat().st_mtime)
            oldest = datetime.fromtimestamp(sorted_files[0].stat().st_mtime)
            newest = datetime.fromtimestamp(sorted_files[-1].stat().st_mtime)

        return {
            "enabled": self.config.enabled,
            "entry_count": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_entry": oldest,
            "newest_entry": newest,
            "cache_dir": str(self.cache_dir),
        }

    def _enforce_size_limit(self) -> None:
        """Evict oldest entries if cache exceeds max size (LRU)."""
        if not self.config.enabled:
            return

        max_bytes = self.config.max_size_gb * 1024 * 1024 * 1024
        files = list(self.cache_dir.glob("*.parquet"))

        # Calculate current size
        current_size = sum(f.stat().st_size for f in files)

        if current_size <= max_bytes:
            return

        # Sort by modification time (oldest first)
        sorted_files = sorted(files, key=lambda f: f.stat().st_mtime)

        # Evict oldest files until under limit
        for cache_file in sorted_files:
            if current_size <= max_bytes:
                break

            file_size = cache_file.stat().st_size
            try:
                cache_file.unlink()
                current_size -= file_size
                logger.debug(f"Evicted {cache_file.name} (LRU)")
            except Exception as e:
                logger.warning(f"Failed to evict {cache_file}: {e}")
