"""Data models for scan results."""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class StockData:
    """Historical price data for a stock."""

    ticker: str
    data: pd.DataFrame  # OHLCV data with DatetimeIndex

    @property
    def start_date(self) -> date:
        """First date in the data."""
        return self.data.index.min().date()

    @property
    def end_date(self) -> date:
        """Last date in the data."""
        return self.data.index.max().date()

    @property
    def trading_days(self) -> int:
        """Number of trading days in the data."""
        return len(self.data)


@dataclass
class ScanResult:
    """Result of scanning a single stock for gain criteria."""

    ticker: str
    gain_pct: float
    low_date: date
    high_date: date
    low_price: float
    high_price: float
    current_price: float
    days_to_peak: int  # Trading days from low to high

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ticker": self.ticker,
            "gain_pct": round(self.gain_pct, 2),
            "low_date": self.low_date.isoformat(),
            "high_date": self.high_date.isoformat(),
            "low_price": round(self.low_price, 2),
            "high_price": round(self.high_price, 2),
            "current_price": round(self.current_price, 2),
            "days_to_peak": self.days_to_peak,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScanResult":
        """Create from dictionary."""
        return cls(
            ticker=data["ticker"],
            gain_pct=data["gain_pct"],
            low_date=date.fromisoformat(data["low_date"]),
            high_date=date.fromisoformat(data["high_date"]),
            low_price=data["low_price"],
            high_price=data["high_price"],
            current_price=data["current_price"],
            days_to_peak=data["days_to_peak"],
        )
