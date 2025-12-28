"""Yahoo Finance data provider implementation."""

import time
from datetime import date

import pandas as pd
import structlog
import yfinance as yf

from stock_finder.config import DataConfig
from stock_finder.data.base import DataProvider
from stock_finder.models.results import StockData

logger = structlog.get_logger()


class YFinanceProvider(DataProvider):
    """Data provider using Yahoo Finance (yfinance library)."""

    def __init__(self, config: DataConfig | None = None):
        """
        Initialize the Yahoo Finance provider.

        Args:
            config: Data configuration. If None, uses defaults.
        """
        self.config = config or DataConfig()
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self.config.rate_limit_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.config.rate_limit_delay:
                time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def get_historical(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> StockData | None:
        """
        Fetch historical OHLCV data from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            StockData with historical prices, or None if data unavailable
        """
        self._rate_limit()

        try:
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(
                start=start.isoformat(),
                end=end.isoformat(),
                auto_adjust=True,  # Adjust for splits/dividends
            )

            if df.empty:
                logger.warning("No data returned", ticker=ticker)
                return None

            # Standardize column names
            df = df.rename(
                columns={
                    "Open": "Open",
                    "High": "High",
                    "Low": "Low",
                    "Close": "Close",
                    "Volume": "Volume",
                }
            )

            # Keep only OHLCV columns
            columns_to_keep = ["Open", "High", "Low", "Close", "Volume"]
            df = df[[c for c in columns_to_keep if c in df.columns]]

            logger.debug(
                "Fetched historical data",
                ticker=ticker,
                rows=len(df),
                start=df.index.min(),
                end=df.index.max(),
            )

            return StockData(ticker=ticker, data=df)

        except Exception as e:
            logger.error("Failed to fetch data", ticker=ticker, error=str(e))
            return None

    def get_current_price(self, ticker: str) -> float | None:
        """
        Get the current/latest price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
        self._rate_limit()

        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info

            # Try different price fields
            price = info.get("regularMarketPrice") or info.get("currentPrice")

            if price is None:
                # Fallback to last close from history
                hist = yf_ticker.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]

            return float(price) if price else None

        except Exception as e:
            logger.error("Failed to get current price", ticker=ticker, error=str(e))
            return None
