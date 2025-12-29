"""Trendline analysis algorithms."""

from stock_finder.analysis.trendline.swing_detection import (
    detect_swing_lows,
    detect_swing_highs,
    filter_ascending_lows,
)
from stock_finder.analysis.trendline.trendline_fitting import fit_trendline
from stock_finder.analysis.trendline.touch_detection import detect_touches

__all__ = [
    "detect_swing_lows",
    "detect_swing_highs",
    "filter_ascending_lows",
    "fit_trendline",
    "detect_touches",
]
