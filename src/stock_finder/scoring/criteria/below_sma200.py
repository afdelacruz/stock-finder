"""Below 200-day SMA criterion."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class BelowSMA200Criterion(Criterion):
    """
    Evaluates if the stock is trading below its 200-day simple moving average.

    The 200-SMA is a key long-term trend indicator. Stocks in major
    downtrends typically trade significantly below this average.
    """

    def __init__(self, threshold: float = -0.10):
        """
        Initialize the below SMA200 criterion.

        Args:
            threshold: Maximum ratio vs SMA200 (e.g., -0.10 = 10% below).
                      Stock passes if (price/sma200 - 1) < threshold.
        """
        self.threshold = threshold

    @property
    def name(self) -> str:
        return "below_sma200"

    @property
    def description(self) -> str:
        return f"Stock is {abs(self.threshold)*100:.0f}%+ below 200-day SMA"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if the stock is below its 200-SMA."""
        sma200 = context.sma_data.get("sma200")

        if sma200 is None:
            return self._missing_data_result("SMA200 data not available")

        if sma200 == 0:
            return self._missing_data_result("SMA200 is zero")

        # Calculate percent from SMA: (price / sma) - 1
        pct_from_sma = (context.ignition_price / sma200) - 1

        passed = bool(pct_from_sma < self.threshold)

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=round(pct_from_sma, 4),
            threshold=self.threshold,
            details=(
                f"Price ${context.ignition_price:.2f} is {pct_from_sma*100:.1f}% "
                f"{'below' if pct_from_sma < 0 else 'above'} SMA200 (${sma200:.2f}). "
                f"{'Passes' if passed else 'Fails'} {abs(self.threshold)*100:.0f}% threshold."
            ),
        )
