"""Extended decline criterion - days since 2-year high."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class ExtendedDeclineCriterion(Criterion):
    """
    Evaluates if the stock has been declining for an extended period.

    Neumann looks for stocks that have been in a downtrend for a significant
    time - this measures trading days from the 2-year high to ignition.
    """

    def __init__(self, min_days: int = 90):
        """
        Initialize the extended decline criterion.

        Args:
            min_days: Minimum trading days since 2-year high required.
        """
        self.min_days = min_days

    @property
    def name(self) -> str:
        return "extended_decline"

    @property
    def description(self) -> str:
        return f"Stock has been declining for {self.min_days}+ trading days"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if the decline has been long enough."""
        if not context.has_sufficient_data:
            return self._missing_data_result("Insufficient historical data")

        days_since_high = context.days_since_high
        if days_since_high is None:
            return self._missing_data_result("Could not determine days since high")

        passed = bool(days_since_high >= self.min_days)

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=float(days_since_high),
            threshold=float(self.min_days),
            details=(
                f"{days_since_high} trading days since 2-year high. "
                f"{'Passes' if passed else 'Fails'} {self.min_days} day minimum."
            ),
        )
