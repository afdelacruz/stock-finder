"""Abstract base class for data providers."""

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from stock_finder.models.results import StockData


class DataProvider(ABC):
    """Abstract base class for stock data providers."""

    @abstractmethod
    def get_historical(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> StockData | None:
        """
        Fetch historical OHLCV data for a ticker.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            StockData with historical prices, or None if data unavailable
        """
        pass

    @abstractmethod
    def get_current_price(self, ticker: str) -> float | None:
        """
        Get the current/latest price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
        pass

    def get_historical_df(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> pd.DataFrame | None:
        """
        Convenience method to get just the DataFrame.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            DataFrame with OHLCV data, or None if unavailable
        """
        stock_data = self.get_historical(ticker, start, end)
        if stock_data is None:
            return None
        return stock_data.data
