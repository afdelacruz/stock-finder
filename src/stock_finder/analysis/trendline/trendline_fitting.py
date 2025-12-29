"""Trendline fitting using linear regression."""

from scipy import stats

from stock_finder.analysis.models import SwingPoint, TrendlineFit


def fit_trendline(swing_lows: list[SwingPoint]) -> TrendlineFit | None:
    """
    Fit a trendline through swing lows using linear regression.

    Uses scipy.stats.linregress to fit a line y = mx + b where:
    - x = bar index
    - y = price

    Args:
        swing_lows: List of swing low points to fit

    Returns:
        TrendlineFit with slope, intercept, and R² value,
        or None if fewer than 2 points provided
    """
    if len(swing_lows) < 2:
        return None

    x = [s.bar_index for s in swing_lows]
    y = [s.price for s in swing_lows]

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return TrendlineFit(
        slope=float(slope),
        intercept=float(intercept),
        r_squared=float(r_value**2),
        points=swing_lows,
    )
