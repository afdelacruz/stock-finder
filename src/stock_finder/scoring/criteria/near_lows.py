"""Near lows criterion - position in 2-year range."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class NearLowsCriterion(Criterion):
    """
    Evaluates if the stock is near its 2-year lows.

    Neumann looks for stocks "sideways near lows" - this measures where
    the ignition price sits in the 2-year high-low range.
    """

    def __init__(self, max_position: float = 0.20):
        """
        Initialize the near lows criterion.

        Args:
            max_position: Maximum position in range (0.0 = at low, 1.0 = at high).
                         Stock passes if position <= max_position.
        """
        self.max_position = max_position

    @property
    def name(self) -> str:
        return "near_lows"

    @property
    def description(self) -> str:
        return f"Stock is in bottom {self.max_position*100:.0f}% of 2-year range"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if the stock is near its lows."""
        if not context.has_sufficient_data:
            return self._missing_data_result("Insufficient historical data")

        range_position = context.range_position
        if range_position is None:
            return self._missing_data_result("Could not determine range position")

        passed = bool(range_position <= self.max_position)

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=round(range_position, 4),
            threshold=self.max_position,
            details=(
                f"At {range_position*100:.1f}% of 2-year range (0%=low, 100%=high). "
                f"{'Passes' if passed else 'Fails'} {self.max_position*100:.0f}% threshold."
            ),
        )
