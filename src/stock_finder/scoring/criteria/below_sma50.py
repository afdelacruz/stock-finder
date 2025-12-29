"""Below 50-day SMA criterion."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class BelowSMA50Criterion(Criterion):
    """
    Evaluates if the stock is trading below its 50-day simple moving average.

    Stocks in downtrends typically trade below key moving averages.
    This criterion checks if price is significantly below the 50-SMA.
    """

    def __init__(self, threshold: float = -0.10):
        """
        Initialize the below SMA50 criterion.

        Args:
            threshold: Maximum ratio vs SMA50 (e.g., -0.10 = 10% below).
                      Stock passes if (price/sma50 - 1) < threshold.
        """
        self.threshold = threshold

    @property
    def name(self) -> str:
        return "below_sma50"

    @property
    def description(self) -> str:
        return f"Stock is {abs(self.threshold)*100:.0f}%+ below 50-day SMA"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if the stock is below its 50-SMA."""
        sma50 = context.sma_data.get("sma50")

        if sma50 is None:
            return self._missing_data_result("SMA50 data not available")

        if sma50 == 0:
            return self._missing_data_result("SMA50 is zero")

        # Calculate percent from SMA: (price / sma) - 1
        # e.g., 20/35 - 1 = -0.43 (43% below)
        pct_from_sma = (context.ignition_price / sma50) - 1

        passed = bool(pct_from_sma < self.threshold)

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=round(pct_from_sma, 4),
            threshold=self.threshold,
            details=(
                f"Price ${context.ignition_price:.2f} is {pct_from_sma*100:.1f}% "
                f"{'below' if pct_from_sma < 0 else 'above'} SMA50 (${sma50:.2f}). "
                f"{'Passes' if passed else 'Fails'} {abs(self.threshold)*100:.0f}% threshold."
            ),
        )
