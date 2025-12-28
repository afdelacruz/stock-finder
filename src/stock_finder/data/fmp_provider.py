"""Financial Modeling Prep (FMP) data provider implementation."""

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
import requests
import structlog

from stock_finder.config import FMPConfig
from stock_finder.data.base import DataProvider
from stock_finder.models.results import StockData

logger = structlog.get_logger()


@dataclass
class Quote:
    """Quote data from FMP."""

    symbol: str
    price: float
    change_percent: float
    day_low: float
    day_high: float
    year_low: float
    year_high: float
    market_cap: int | None
    avg_volume: int
    volume: int
    price_avg_50: float | None
    price_avg_200: float | None
    exchange: str
    name: str


class FMPProvider(DataProvider):
    """Data provider using Financial Modeling Prep API."""

    def __init__(self, config: FMPConfig | None = None):
        """
        Initialize the FMP provider.

        Args:
            config: FMP configuration. If None, loads from environment.
        """
        self.config = config or FMPConfig.from_env()
        if not self.config.api_key:
            raise ValueError("FMP API key not found. Set FMP_API_KEY environment variable.")

    def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make a request to FMP API."""
        url = f"{self.config.base_url}/{endpoint}"
        params = params or {}
        params["apikey"] = self.config.api_key

        try:
            response = requests.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("FMP API request failed", endpoint=endpoint, error=str(e))
            raise

    def get_quote(self, ticker: str) -> Quote | None:
        """
        Get current quote for a single ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quote object or None if unavailable
        """
        try:
            data = self._request(f"quote/{ticker}")
            if not data:
                return None
            return self._parse_quote(data[0])
        except Exception as e:
            logger.error("Failed to get quote", ticker=ticker, error=str(e))
            return None

    def get_quotes_batch(self, tickers: list[str]) -> dict[str, Quote]:
        """
        Get quotes for multiple tickers in batch.

        Args:
            tickers: List of ticker symbols (max ~50 per request recommended)

        Returns:
            Dictionary mapping ticker to Quote
        """
        results: dict[str, Quote] = {}

        # Process in batches
        for i in range(0, len(tickers), self.config.batch_size):
            batch = tickers[i : i + self.config.batch_size]
            symbols = ",".join(batch)

            try:
                data = self._request(f"quote/{symbols}")
                for item in data:
                    quote = self._parse_quote(item)
                    if quote:
                        results[quote.symbol] = quote
            except Exception as e:
                logger.error("Batch quote failed", batch_start=i, error=str(e))

        logger.info("Fetched batch quotes", requested=len(tickers), received=len(results))
        return results

    def _parse_quote(self, data: dict) -> Quote | None:
        """Parse raw quote data into Quote object."""
        try:
            return Quote(
                symbol=data.get("symbol", ""),
                price=data.get("price", 0),
                change_percent=data.get("changesPercentage", 0),
                day_low=data.get("dayLow", 0),
                day_high=data.get("dayHigh", 0),
                year_low=data.get("yearLow", 0),
                year_high=data.get("yearHigh", 0),
                market_cap=data.get("marketCap"),
                avg_volume=data.get("avgVolume", 0),
                volume=data.get("volume", 0),
                price_avg_50=data.get("priceAvg50"),
                price_avg_200=data.get("priceAvg200"),
                exchange=data.get("exchange", ""),
                name=data.get("name", ""),
            )
        except Exception as e:
            logger.error("Failed to parse quote", error=str(e))
            return None

    def get_historical(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> StockData | None:
        """
        Fetch historical OHLCV data from FMP.

        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date

        Returns:
            StockData with historical prices, or None if data unavailable
        """
        try:
            data = self._request(
                f"historical-price-full/{ticker}",
                params={"from": start.isoformat(), "to": end.isoformat()},
            )

            if not data or "historical" not in data:
                logger.warning("No historical data returned", ticker=ticker)
                return None

            historical = data["historical"]
            if not historical:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(historical)

            # Parse dates and set as index
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.sort_index()

            # Rename columns to standard format
            df = df.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
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
            logger.error("Failed to fetch historical data", ticker=ticker, error=str(e))
            return None

    def get_current_price(self, ticker: str) -> float | None:
        """
        Get the current/latest price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
        quote = self.get_quote(ticker)
        return quote.price if quote else None

    def get_technical_indicator(
        self,
        ticker: str,
        indicator: str = "sma",
        period: int = 50,
    ) -> pd.DataFrame | None:
        """
        Get technical indicator data.

        Args:
            ticker: Stock ticker symbol
            indicator: Indicator type (sma, ema, rsi, etc.)
            period: Indicator period

        Returns:
            DataFrame with indicator values or None
        """
        try:
            data = self._request(
                f"technical_indicator/daily/{ticker}",
                params={"type": indicator, "period": period},
            )

            if not data:
                return None

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error(
                "Failed to fetch technical indicator",
                ticker=ticker,
                indicator=indicator,
                error=str(e),
            )
            return None

    def get_market_cap(self, ticker: str) -> int | None:
        """
        Get current market cap for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Market cap in dollars or None
        """
        quote = self.get_quote(ticker)
        return quote.market_cap if quote else None

    def get_market_caps_batch(self, tickers: list[str]) -> dict[str, int]:
        """
        Get market caps for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to market cap
        """
        quotes = self.get_quotes_batch(tickers)
        return {symbol: q.market_cap for symbol, q in quotes.items() if q.market_cap}
