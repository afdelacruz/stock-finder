"""Trendline break criterion using SMA crossover as proxy."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class TrendlineBreakCriterion(Criterion):
    """
    Evaluates if the stock is breaking above its downtrend.

    Neumann enters on "breakouts from 1-5 year downtrend lines."
    As a quantifiable proxy, we check if price is crossing above
    the 50-day SMA - an early sign of trend reversal.

    This implementation can be swapped for more sophisticated
    trendline detection algorithms.
    """

    def __init__(self, sma_key: str = "sma50"):
        """
        Initialize the trendline break criterion.

        Args:
            sma_key: Which SMA to use for the crossover check.
        """
        self.sma_key = sma_key

    @property
    def name(self) -> str:
        return "trendline_break"

    @property
    def description(self) -> str:
        return "Price is crossing above descending resistance (SMA proxy)"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if price is breaking above the trend."""
        sma_value = context.sma_data.get(self.sma_key)

        if sma_value is None:
            return self._missing_data_result(f"{self.sma_key.upper()} data not available")

        if sma_value == 0:
            return self._missing_data_result(f"{self.sma_key.upper()} is zero")

        # Check if price is above the SMA (breaking above resistance)
        # For a true crossover, we'd also check that previous day was below
        # But at ignition, being above the SMA is the key signal
        is_above = bool(context.ignition_price > sma_value)

        # Calculate how far above/below
        pct_from_sma = (context.ignition_price / sma_value) - 1

        return CriterionResult(
            name=self.name,
            passed=is_above,
            value=round(pct_from_sma, 4),
            threshold=0.0,  # Must be above (positive)
            details=(
                f"Price ${context.ignition_price:.2f} is "
                f"{'above' if is_above else 'below'} {self.sma_key.upper()} "
                f"(${sma_value:.2f}) by {abs(pct_from_sma)*100:.1f}%. "
                f"{'Passes' if is_above else 'Fails'} - price must be above SMA."
            ),
        )
