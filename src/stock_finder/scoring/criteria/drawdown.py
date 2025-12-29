"""Significant drawdown criterion."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class DrawdownCriterion(Criterion):
    """
    Evaluates if the stock has experienced a significant drawdown from its 2-year high.

    Neumann looks for stocks that have "largely declined" - this measures
    how far the ignition price is below the 2-year high.
    """

    def __init__(self, threshold: float = -0.50):
        """
        Initialize the drawdown criterion.

        Args:
            threshold: Maximum drawdown required (e.g., -0.50 = 50% decline).
                      Stock passes if drawdown <= threshold.
        """
        self.threshold = threshold

    @property
    def name(self) -> str:
        return "drawdown"

    @property
    def description(self) -> str:
        return f"Stock has declined {abs(self.threshold)*100:.0f}%+ from 2-year high"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if the stock has sufficient drawdown."""
        if not context.has_sufficient_data:
            return self._missing_data_result("Insufficient historical data")

        two_year_high = context.two_year_high
        if two_year_high is None or two_year_high == 0:
            return self._missing_data_result("Could not determine 2-year high")

        # Calculate drawdown: (current / high) - 1
        # e.g., 20/100 - 1 = -0.80 (80% drawdown)
        drawdown = (context.ignition_price / two_year_high) - 1

        passed = bool(drawdown <= self.threshold)

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=round(drawdown, 4),
            threshold=self.threshold,
            details=(
                f"Drawdown of {drawdown*100:.1f}% from 2yr high of ${two_year_high:.2f}. "
                f"{'Passes' if passed else 'Fails'} {abs(self.threshold)*100:.0f}% threshold."
            ),
        )
