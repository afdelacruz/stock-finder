"""Base classes for Neumann scoring criteria."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class ScoringContext:
    """
    Context containing all data needed to evaluate criteria at ignition point.

    Attributes:
        ticker: Stock ticker symbol
        ignition_date: The low_date (ignition point) from scan results
        ignition_price: The low_price at ignition
        historical_data: OHLCV DataFrame for 2 years before ignition
        gain_pct: The eventual gain from the scan results
        high_date: Date of the peak after ignition
        high_price: Price at the peak
        shares_outstanding: Number of shares (for market cap calculation)
        sma_data: Dict of SMA values at ignition (e.g., {"sma50": 15.0, "sma200": 18.0})
    """

    ticker: str
    ignition_date: date
    ignition_price: float
    historical_data: pd.DataFrame
    gain_pct: float
    high_date: date
    high_price: float
    shares_outstanding: float | None = None
    sma_data: dict[str, float] = field(default_factory=dict)

    @property
    def has_sufficient_data(self) -> bool:
        """Check if we have enough historical data for analysis."""
        if self.historical_data is None or self.historical_data.empty:
            return False
        return len(self.historical_data) >= 50  # At least 50 days

    @property
    def two_year_high(self) -> float | None:
        """Get the 2-year high price before ignition."""
        if not self.has_sufficient_data:
            return None
        return self.historical_data["High"].max()

    @property
    def two_year_low(self) -> float | None:
        """Get the 2-year low price before ignition."""
        if not self.has_sufficient_data:
            return None
        return self.historical_data["Low"].min()

    @property
    def two_year_high_date(self) -> date | None:
        """Get the date of the 2-year high."""
        if not self.has_sufficient_data:
            return None
        return self.historical_data["High"].idxmax().date()

    @property
    def days_since_high(self) -> int | None:
        """Calculate trading days from 2-year high to ignition."""
        if not self.has_sufficient_data:
            return None
        high_date = self.two_year_high_date
        if high_date is None:
            return None
        # Count trading days between high and ignition
        mask = (self.historical_data.index >= pd.Timestamp(high_date)) & (
            self.historical_data.index <= pd.Timestamp(self.ignition_date)
        )
        return mask.sum()

    @property
    def range_position(self) -> float | None:
        """
        Calculate where ignition price sits in the 2-year range.

        Returns:
            0.0 = at the low, 1.0 = at the high
        """
        high = self.two_year_high
        low = self.two_year_low
        if high is None or low is None or high == low:
            return None
        return (self.ignition_price - low) / (high - low)

    @property
    def estimated_market_cap(self) -> float | None:
        """Estimate market cap at ignition using shares_outstanding * ignition_price."""
        if self.shares_outstanding is None:
            return None
        return self.shares_outstanding * self.ignition_price

    def get_volume_at_ignition(self) -> float | None:
        """Get the volume on ignition date."""
        if not self.has_sufficient_data:
            return None
        try:
            return self.historical_data.loc[
                pd.Timestamp(self.ignition_date), "Volume"
            ]
        except KeyError:
            # Try to find closest date
            idx = self.historical_data.index.get_indexer(
                [pd.Timestamp(self.ignition_date)], method="nearest"
            )[0]
            if idx >= 0:
                return self.historical_data.iloc[idx]["Volume"]
            return None

    def get_avg_volume(self, days: int = 50) -> float | None:
        """Get average volume over the last N days before ignition."""
        if not self.has_sufficient_data:
            return None
        # Get last N days of volume
        volumes = self.historical_data["Volume"].tail(days)
        if len(volumes) == 0:
            return None
        return volumes.mean()


@dataclass
class CriterionResult:
    """
    Result from evaluating a single criterion.

    Attributes:
        name: Unique identifier for the criterion
        passed: Whether the criterion was met
        value: The actual calculated value
        threshold: The threshold used for comparison
        details: Human-readable explanation of the result
    """

    name: str
    passed: bool
    value: float | None
    threshold: float | None
    details: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "threshold": self.threshold,
            "details": self.details,
        }


class Criterion(ABC):
    """
    Abstract base class for Neumann scoring criteria.

    Each criterion evaluates one aspect of the stock at its ignition point
    and returns a pass/fail result with details.

    Implementations should be stateless and configurable via constructor.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this criterion."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this criterion measures."""
        pass

    @abstractmethod
    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """
        Evaluate this criterion against the stock data.

        Args:
            context: Contains ticker, ignition_date, historical_data, etc.

        Returns:
            CriterionResult with pass/fail and details
        """
        pass

    def _missing_data_result(self, reason: str) -> CriterionResult:
        """Helper to create a result when data is missing."""
        return CriterionResult(
            name=self.name,
            passed=False,
            value=None,
            threshold=None,
            details=f"Unable to evaluate: {reason}",
        )
