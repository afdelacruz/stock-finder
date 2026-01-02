"""Data models for analysis modules."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


# =============================================================================
# Statistical Analysis Models
# =============================================================================


@dataclass
class VariableStats:
    """Statistical summary for a single variable."""

    variable_name: str
    mean: float | None = None
    median: float | None = None
    std_dev: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    p10: float | None = None
    p25: float | None = None
    p75: float | None = None
    p90: float | None = None
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "variable_name": self.variable_name,
            "mean": self.mean,
            "median": self.median,
            "std_dev": self.std_dev,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "p10": self.p10,
            "p25": self.p25,
            "p75": self.p75,
            "p90": self.p90,
            "sample_size": self.sample_size,
        }


@dataclass
class AnalysisConfig:
    """Configuration for statistical analysis."""

    start_date: str
    end_date: str
    min_gain_pct: float = 300.0
    universe: str = "all"
    variables: list[str] = field(default_factory=lambda: [
        "drawdown",
        "days_declining",
        "vol_ratio",
        "days_to_peak",
        "gain_pct",
    ])


@dataclass
class AnalysisResult:
    """Complete analysis result with stats for winners and all stocks."""

    run_id: str
    config: AnalysisConfig
    winners_count: int
    total_count: int
    winners_stats: dict[str, VariableStats] = field(default_factory=dict)
    all_stats: dict[str, VariableStats] = field(default_factory=dict)
    lift: dict[str, float] = field(default_factory=dict)

    def to_summary(self) -> dict[str, Any]:
        """Create a summary dict for display."""
        return {
            "run_id": self.run_id,
            "period": f"{self.config.start_date} to {self.config.end_date}",
            "min_gain": f"{self.config.min_gain_pct}%",
            "universe": self.config.universe,
            "winners": self.winners_count,
            "total": self.total_count,
            "lift": self.lift,
        }


# =============================================================================
# Trendline Analysis Models
# =============================================================================


@dataclass
class SwingPoint:
    """A swing low or high point in price data."""

    date: date
    price: float
    bar_index: int


@dataclass
class TrendlineFit:
    """Result of fitting a trendline through swing points."""

    slope: float  # Price change per bar
    intercept: float  # Starting price at bar 0
    r_squared: float  # Goodness of fit (0-1)
    points: list[SwingPoint] = field(default_factory=list)

    def price_at_bar(self, bar_index: int) -> float:
        """Calculate trendline price at a given bar index."""
        return self.slope * bar_index + self.intercept


@dataclass
class TouchPoint:
    """A point where price touched or came close to the trendline."""

    date: date
    price: float
    trendline_price: float
    deviation_pct: float  # How far from trendline (negative = below)
    bar_index: int


@dataclass
class TrendlineConfig:
    """Configuration for trendline analysis."""

    swing_lookback: int = 10  # Bars to look back/forward for swing detection
    min_touches: int = 2  # Minimum touches to form valid trendline
    touch_tolerance: float = 0.02  # 2% tolerance for touch detection
    min_r_squared: float = 0.5  # Minimum R² to consider "formed"
    data_buffer_days: int = 30  # Days before/after move to fetch


@dataclass
class TrendlineAnalysis:
    """Complete trendline analysis result for a stock."""

    ticker: str
    scan_result_id: int
    timeframe: str  # 'daily' or 'weekly'

    # Formation
    trendline_formed: bool
    days_to_form: int | None = None
    swing_low_count: int = 0

    # Quality
    r_squared: float | None = None
    slope_pct_per_day: float | None = None

    # Touches
    touch_count: int = 0
    avg_bounce_pct: float | None = None
    max_deviation_pct: float | None = None

    # Break
    break_date: date | None = None
    break_price: float | None = None

    # From scan result for correlation analysis
    gain_pct: float | None = None
    days_to_peak: int | None = None

    # Raw data for further analysis
    trendline_fit: TrendlineFit | None = None
    swing_lows: list[SwingPoint] = field(default_factory=list)
    touches: list[TouchPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ticker": self.ticker,
            "scan_result_id": self.scan_result_id,
            "timeframe": self.timeframe,
            "trendline_formed": self.trendline_formed,
            "days_to_form": self.days_to_form,
            "swing_low_count": self.swing_low_count,
            "r_squared": self.r_squared,
            "slope_pct_per_day": self.slope_pct_per_day,
            "touch_count": self.touch_count,
            "avg_bounce_pct": self.avg_bounce_pct,
            "max_deviation_pct": self.max_deviation_pct,
            "break_date": self.break_date.isoformat() if self.break_date else None,
            "break_price": self.break_price,
            "gain_pct": self.gain_pct,
            "days_to_peak": self.days_to_peak,
        }
