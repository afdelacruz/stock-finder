"""Statistical calculation utilities for analysis framework."""

from __future__ import annotations

import math
from typing import Sequence

from stock_finder.analysis.models import VariableStats


def calculate_stats(values: Sequence[float], variable_name: str) -> VariableStats:
    """
    Calculate comprehensive statistics for a list of values.

    Args:
        values: Sequence of numeric values
        variable_name: Name of the variable being analyzed

    Returns:
        VariableStats with all computed statistics
    """
    if not values:
        return VariableStats(variable_name=variable_name, sample_size=0)

    # Filter out None values and convert to list
    clean_values = [v for v in values if v is not None and not math.isnan(v)]

    if not clean_values:
        return VariableStats(variable_name=variable_name, sample_size=0)

    n = len(clean_values)
    sorted_vals = sorted(clean_values)

    # Central tendency
    mean = sum(clean_values) / n
    median = percentile(sorted_vals, 50)

    # Spread
    if n > 1:
        variance = sum((x - mean) ** 2 for x in clean_values) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    return VariableStats(
        variable_name=variable_name,
        mean=round(mean, 4),
        median=round(median, 4),
        std_dev=round(std_dev, 4),
        min_val=round(min(clean_values), 4),
        max_val=round(max(clean_values), 4),
        p10=round(percentile(sorted_vals, 10), 4),
        p25=round(percentile(sorted_vals, 25), 4),
        p75=round(percentile(sorted_vals, 75), 4),
        p90=round(percentile(sorted_vals, 90), 4),
        sample_size=n,
    )


def percentile(sorted_values: list[float], p: float) -> float:
    """
    Calculate percentile using linear interpolation.

    Args:
        sorted_values: Pre-sorted list of values
        p: Percentile to calculate (0-100)

    Returns:
        The value at the given percentile
    """
    if not sorted_values:
        return 0.0

    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]

    # Use linear interpolation
    k = (n - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return sorted_values[int(k)]

    return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)


def calculate_lift(
    winners_mean: float | None,
    all_mean: float | None,
    variable_name: str,
) -> float | None:
    """
    Calculate lift (predictive power) for a variable.

    For most variables: lift = winners_mean / all_mean (higher is better)
    For negative metrics (drawdown, pct_from_sma): lift = all_mean / winners_mean

    Args:
        winners_mean: Mean value for winners
        all_mean: Mean value for all stocks
        variable_name: Name of the variable

    Returns:
        Lift value (1.0 = no difference, >1 = winners differ positively)
    """
    if winners_mean is None or all_mean is None:
        return None

    if all_mean == 0 or winners_mean == 0:
        return None

    # Variables where lower values are better for winners
    negative_metrics = {"drawdown", "pct_from_sma50", "pct_from_sma200"}

    if variable_name in negative_metrics:
        # For drawdown: winners have deeper drawdown, so winners_mean is more negative
        # Lift = all_mean / winners_mean (both negative, so result is positive if winners more extreme)
        return round(abs(winners_mean / all_mean), 2)
    else:
        # For positive metrics: higher is better
        return round(winners_mean / all_mean, 2)
