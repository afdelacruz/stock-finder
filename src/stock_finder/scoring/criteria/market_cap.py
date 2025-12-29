"""Market cap sweet spot criterion."""

from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


class MarketCapCriterion(Criterion):
    """
    Evaluates if the stock is in the market cap sweet spot.

    Neumann's sweet spot is $200M - $500M, though he'll go up to $2B.
    Small enough to have room to run, large enough to be liquid.
    """

    def __init__(
        self,
        min_cap: float = 200_000_000,
        max_cap: float = 2_000_000_000,
    ):
        """
        Initialize the market cap criterion.

        Args:
            min_cap: Minimum market cap in dollars.
            max_cap: Maximum market cap in dollars.
        """
        self.min_cap = min_cap
        self.max_cap = max_cap

    @property
    def name(self) -> str:
        return "market_cap"

    @property
    def description(self) -> str:
        return f"Market cap between ${self._format_cap(self.min_cap)} - ${self._format_cap(self.max_cap)}"

    def _format_cap(self, cap: float) -> str:
        """Format market cap for display."""
        if cap >= 1_000_000_000:
            return f"{cap/1_000_000_000:.1f}B"
        if cap >= 1_000_000:
            return f"{cap/1_000_000:.0f}M"
        return f"{cap:,.0f}"

    def evaluate(self, context: ScoringContext) -> CriterionResult:
        """Evaluate if market cap is in the sweet spot."""
        market_cap = context.estimated_market_cap

        if market_cap is None:
            return self._missing_data_result(
                "Could not estimate market cap (shares outstanding not available)"
            )

        passed = bool(self.min_cap <= market_cap <= self.max_cap)

        if market_cap < self.min_cap:
            status = f"below ${self._format_cap(self.min_cap)} minimum"
        elif market_cap > self.max_cap:
            status = f"above ${self._format_cap(self.max_cap)} maximum"
        else:
            status = "in sweet spot"

        return CriterionResult(
            name=self.name,
            passed=passed,
            value=market_cap,
            threshold=None,  # Range, not single threshold
            details=(
                f"Estimated market cap ${self._format_cap(market_cap)} is {status}. "
                f"Target range: ${self._format_cap(self.min_cap)} - ${self._format_cap(self.max_cap)}."
            ),
        )
