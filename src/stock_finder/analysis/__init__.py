"""Analysis module for statistical and price structure analysis."""

from stock_finder.analysis.models import (
    # Statistical analysis
    AnalysisConfig,
    AnalysisResult,
    VariableStats,
    # Trendline analysis
    SwingPoint,
    TrendlineFit,
    TouchPoint,
    TrendlineAnalysis,
    TrendlineConfig,
)
from stock_finder.analysis.framework import AnalysisFramework
from stock_finder.analysis.statistics import calculate_stats, calculate_lift

__all__ = [
    # Statistical analysis
    "AnalysisFramework",
    "AnalysisConfig",
    "AnalysisResult",
    "VariableStats",
    "calculate_stats",
    "calculate_lift",
    # Trendline analysis
    "SwingPoint",
    "TrendlineFit",
    "TouchPoint",
    "TrendlineAnalysis",
    "TrendlineConfig",
]
