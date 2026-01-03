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
from stock_finder.analysis.deriver import CriteriaDeriver, DerivedCriteria, DerivedThreshold

__all__ = [
    # Statistical analysis
    "AnalysisFramework",
    "AnalysisConfig",
    "AnalysisResult",
    "VariableStats",
    "calculate_stats",
    "calculate_lift",
    # Criteria derivation
    "CriteriaDeriver",
    "DerivedCriteria",
    "DerivedThreshold",
    # Trendline analysis
    "SwingPoint",
    "TrendlineFit",
    "TouchPoint",
    "TrendlineAnalysis",
    "TrendlineConfig",
]
