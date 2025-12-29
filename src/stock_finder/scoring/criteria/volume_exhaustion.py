"""Volume exhaustion criterion."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class VolumeExhaustionCriterion(Criterion):
    """
    Evaluates if selling pressure has exhausted (low volume at lows).

    Neumann looks for a "sudden upmove or volume spike after quiet period."
    Low volume at the ignition point suggests sellers have exhausted
    and the stock is ready for a reversal.
    """

    def __init__(self, max_ratio: float = 1.0, avg_days: int = 50):
        """
        Initialize the volume exhaustion criterion.

        Args:
            max_ratio: Maximum volume ratio vs average (e.g., 1.0 = at or below average).
            avg_days: Number of days for average volume calculation.
        """
        self.max_ratio = max_ratio
        self.avg_days = avg_days

    @property
    def name(self) -> str:
        return "volume_exhaustion"

    @property
    def description(self) -> str:
        return f"Volume is at or below {self.avg_days}-day average (exhaustion)"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if volume shows exhaustion."""
        if not context.has_sufficient_data:
            return self._missing_data_result("Insufficient historical data")

        current_volume = context.get_volume_at_ignition()
        avg_volume = context.get_avg_volume(self.avg_days)

        if current_volume is None:
            return self._missing_data_result("Could not get volume at ignition")

        if avg_volume is None or avg_volume == 0:
            return self._missing_data_result("Could not calculate average volume")

        # Calculate volume ratio
        vol_ratio = current_volume / avg_volume

        passed = bool(vol_ratio <= self.max_ratio)

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=round(vol_ratio, 4),
            threshold=self.max_ratio,
            details=(
                f"Volume {current_volume:,.0f} is {vol_ratio:.2f}x the {self.avg_days}-day "
                f"average ({avg_volume:,.0f}). "
                f"{'Passes' if passed else 'Fails'} <= {self.max_ratio:.1f}x threshold."
            ),
        )
