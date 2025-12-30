"""Scoring modes and criteria weights based on empirical analysis."""

from enum import Enum


class ScoringMode(str, Enum):
    """Available scoring modes for Neumann criteria."""

    FULL = "full"
    """All 8 criteria, equal weight (1 point each). Max score: 8."""

    CORE = "core"
    """Only high-predictive criteria (drawdown, extended_decline). Max score: 2."""

    WEIGHTED = "weighted"
    """All criteria with weights based on predictive lift. Max score: 10."""


# Weights based on empirical analysis of 3,177 stocks
# Lift = avg_gain_when_passed / avg_gain_when_failed
CRITERIA_WEIGHTS = {
    # High predictive value (lift > 1.5x)
    "drawdown": 3,           # 1.86x lift - BEST predictor
    "extended_decline": 2,   # 1.61x lift - strong

    # Moderate predictive value (lift 1.2-1.5x)
    "near_lows": 1,          # 1.29x lift
    "volume_exhaustion": 1,  # 1.27x lift

    # Low predictive value (lift < 1.2x)
    "below_sma50": 1,        # 1.12x lift - weak
    "below_sma200": 0,       # 1.06x lift - nearly useless, excluded
    "market_cap": 1,         # N/A - data quality issues, keep for completeness
    "trendline_break": 1,    # Not analyzed, keep default weight
}

# Core criteria - only the high-value predictors
CORE_CRITERIA = {"drawdown", "extended_decline"}

# Maximum possible scores by mode
MAX_SCORES = {
    ScoringMode.FULL: 8,
    ScoringMode.CORE: 2,
    ScoringMode.WEIGHTED: sum(CRITERIA_WEIGHTS.values()),  # 10
}


def get_weight(criterion_name: str, mode: ScoringMode) -> int:
    """
    Get the weight for a criterion based on scoring mode.

    Args:
        criterion_name: Name of the criterion
        mode: Scoring mode to use

    Returns:
        Weight for the criterion (0 means excluded)
    """
    if mode == ScoringMode.FULL:
        return 1
    elif mode == ScoringMode.CORE:
        return 1 if criterion_name in CORE_CRITERIA else 0
    elif mode == ScoringMode.WEIGHTED:
        return CRITERIA_WEIGHTS.get(criterion_name, 1)
    return 1


def get_max_score(mode: ScoringMode) -> int:
    """Get the maximum possible score for a scoring mode."""
    return MAX_SCORES[mode]
