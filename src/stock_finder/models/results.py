"""Data models for scan results."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

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


@dataclass
class NeumannScore:
    """
    Result of scoring a stock against Neumann's criteria at its ignition point.

    Attributes:
        ticker: Stock ticker symbol
        scan_result_id: ID of the source scan_result record
        score: Total score (0-8, number of criteria passed)
        criteria_results: Dict mapping criterion name to pass/fail and value
        drawdown: Drawdown from 2-year high at ignition
        days_since_high: Trading days from 2-year high to ignition
        range_position: Position in 2-year range (0=low, 1=high)
        pct_from_sma50: Percent distance from 50-SMA
        pct_from_sma200: Percent distance from 200-SMA
        vol_ratio: Volume ratio vs 50-day average
        market_cap_estimate: Estimated market cap at ignition
        sma_crossover: Whether price crossed above SMA (trendline proxy)
    """

    ticker: str
    scan_result_id: int
    score: int
    criteria_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    drawdown: float | None = None
    days_since_high: int | None = None
    range_position: float | None = None
    pct_from_sma50: float | None = None
    pct_from_sma200: float | None = None
    vol_ratio: float | None = None
    market_cap_estimate: float | None = None
    sma_crossover: bool | None = None
    # From original scan result for analysis
    gain_pct: float | None = None
    days_to_peak: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ticker": self.ticker,
            "scan_result_id": self.scan_result_id,
            "score": self.score,
            "criteria_results": self.criteria_results,
            "drawdown": self.drawdown,
            "days_since_high": self.days_since_high,
            "range_position": self.range_position,
            "pct_from_sma50": self.pct_from_sma50,
            "pct_from_sma200": self.pct_from_sma200,
            "vol_ratio": self.vol_ratio,
            "market_cap_estimate": self.market_cap_estimate,
            "sma_crossover": self.sma_crossover,
            "gain_pct": self.gain_pct,
            "days_to_peak": self.days_to_peak,
        }
