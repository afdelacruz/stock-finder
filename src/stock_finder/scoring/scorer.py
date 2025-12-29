"""NeumannScorer - orchestrates scoring stocks against Neumann criteria."""

from datetime import date, timedelta
from typing import Any, Callable

import structlog

from stock_finder.data.base import DataProvider
from stock_finder.data.database import Database
from stock_finder.models.results import NeumannScore
from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext
from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion
from stock_finder.scoring.criteria.below_sma200 import BelowSMA200Criterion
from stock_finder.scoring.criteria.drawdown import DrawdownCriterion
from stock_finder.scoring.criteria.extended_decline import ExtendedDeclineCriterion
from stock_finder.scoring.criteria.market_cap import MarketCapCriterion
from stock_finder.scoring.criteria.near_lows import NearLowsCriterion
from stock_finder.scoring.criteria.trendline_break import TrendlineBreakCriterion
from stock_finder.scoring.criteria.volume_exhaustion import VolumeExhaustionCriterion

logger = structlog.get_logger()


class NeumannScorer:
    """
    Orchestrates scoring stocks against Jeffrey Neumann's criteria.

    The scorer takes scan results (stocks that achieved 300%+ gains) and
    evaluates each stock at its ignition point (low_date) against 8 quantifiable
    criteria derived from Neumann's approach in "Unknown Market Wizards".
    """

    def __init__(
        self,
        provider: DataProvider | None = None,
        criteria: list[Criterion] | None = None,
        db: Database | None = None,
    ):
        """
        Initialize the scorer.

        Args:
            provider: Data provider for fetching historical data.
                     If None, scoring will fail for stocks needing data.
            criteria: List of criteria to evaluate. If None, uses default 8 criteria.
            db: Database for saving scores. If None, scores are not persisted.
        """
        self.provider = provider
        self.criteria = criteria if criteria is not None else self._default_criteria()
        self.db = db

    def _default_criteria(self) -> list[Criterion]:
        """Return the standard 8 Neumann criteria with default thresholds."""
        return [
            DrawdownCriterion(threshold=-0.50),
            ExtendedDeclineCriterion(min_days=90),
            NearLowsCriterion(max_position=0.20),
            BelowSMA50Criterion(threshold=-0.10),
            BelowSMA200Criterion(threshold=-0.10),
            VolumeExhaustionCriterion(max_ratio=1.0),
            MarketCapCriterion(min_cap=200_000_000, max_cap=2_000_000_000),
            TrendlineBreakCriterion(),
        ]

    def score_stock(self, scan_result: dict[str, Any]) -> NeumannScore:
        """
        Score a single stock at its ignition point.

        Args:
            scan_result: Dict with keys: id, ticker, low_date, low_price,
                        high_date, high_price, gain_pct, days_to_peak

        Returns:
            NeumannScore with results for all criteria
        """
        ticker = scan_result["ticker"]
        scan_result_id = scan_result.get("id", 0)

        # Parse dates if they're strings
        low_date = self._parse_date(scan_result["low_date"])
        high_date = self._parse_date(scan_result["high_date"])
        low_price = float(scan_result.get("low_price", 0))
        high_price = float(scan_result.get("high_price", 0))
        gain_pct = float(scan_result.get("gain_pct", 0))
        days_to_peak = int(scan_result.get("days_to_peak", 0))

        # Build scoring context
        context = self._build_context(
            ticker=ticker,
            ignition_date=low_date,
            ignition_price=low_price,
            high_date=high_date,
            high_price=high_price,
            gain_pct=gain_pct,
        )

        # Evaluate all criteria
        results: dict[str, dict[str, Any]] = {}
        total_score = 0

        for criterion in self.criteria:
            result = criterion.evaluate(context)
            results[criterion.name] = result.to_dict()
            if result.passed:
                total_score += 1

        # Extract individual metrics for storage
        return NeumannScore(
            ticker=ticker,
            scan_result_id=scan_result_id,
            score=total_score,
            criteria_results=results,
            drawdown=self._get_value(results, "drawdown"),
            days_since_high=self._get_value_int(results, "extended_decline"),
            range_position=self._get_value(results, "near_lows"),
            pct_from_sma50=self._get_value(results, "below_sma50"),
            pct_from_sma200=self._get_value(results, "below_sma200"),
            vol_ratio=self._get_value(results, "volume_exhaustion"),
            market_cap_estimate=self._get_value(results, "market_cap"),
            sma_crossover=self._get_passed(results, "trendline_break"),
            gain_pct=gain_pct,
            days_to_peak=days_to_peak,
        )

    def score_all(
        self,
        scan_run_id: int,
        save: bool = False,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> list[NeumannScore]:
        """
        Score all stocks from a scan run.

        Args:
            scan_run_id: ID of the scan run to score
            save: Whether to save results to database
            on_progress: Callback for progress updates (current, total, ticker)

        Returns:
            List of NeumannScore objects
        """
        if self.db is None:
            raise ValueError("Database required to score scan run")

        # Get all results from the scan run
        scan_results = self.db.get_results(scan_run_id=scan_run_id)

        logger.info(
            "Scoring scan run",
            scan_run_id=scan_run_id,
            total_stocks=len(scan_results),
        )

        scores = []
        for i, result in enumerate(scan_results):
            if on_progress:
                on_progress(i + 1, len(scan_results), result["ticker"])

            try:
                score = self.score_stock(result)
                scores.append(score)

                if save:
                    self.db.add_neumann_score(score)

            except Exception as e:
                logger.error(
                    "Failed to score stock",
                    ticker=result["ticker"],
                    error=str(e),
                )

        logger.info(
            "Scoring complete",
            scored=len(scores),
            avg_score=sum(s.score for s in scores) / len(scores) if scores else 0,
        )

        return scores

    def _build_context(
        self,
        ticker: str,
        ignition_date: date,
        ignition_price: float,
        high_date: date,
        high_price: float,
        gain_pct: float,
    ) -> ScoringContext:
        """Build a ScoringContext with historical data and SMA values."""
        import pandas as pd

        # Default empty context if no provider
        historical_data = pd.DataFrame()
        shares_outstanding = None
        sma_data = {}

        if self.provider is not None:
            # Fetch 2 years of historical data before ignition
            start_date = ignition_date - timedelta(days=730)  # ~2 years
            end_date = ignition_date

            stock_data = self.provider.get_historical(ticker, start_date, end_date)
            if stock_data is not None:
                historical_data = stock_data.data

                # Calculate SMAs from historical data (more accurate than current quote)
                if len(historical_data) >= 50:
                    sma50 = historical_data["Close"].tail(50).mean()
                    sma_data["sma50"] = sma50
                if len(historical_data) >= 200:
                    sma200 = historical_data["Close"].tail(200).mean()
                    sma_data["sma200"] = sma200

            # Try to get shares outstanding from provider for market cap
            try:
                if hasattr(self.provider, "get_quote"):
                    quote = self.provider.get_quote(ticker)
                    if quote and quote.market_cap and quote.price:
                        # Estimate shares from current market cap / current price
                        shares_outstanding = quote.market_cap / quote.price
            except Exception as e:
                logger.debug("Could not get quote data", ticker=ticker, error=str(e))

        # Build context
        return ScoringContext(
            ticker=ticker,
            ignition_date=ignition_date,
            ignition_price=ignition_price,
            historical_data=historical_data,
            gain_pct=gain_pct,
            high_date=high_date,
            high_price=high_price,
            shares_outstanding=shares_outstanding,
            sma_data={k: v for k, v in sma_data.items() if v is not None},
        )

    def _parse_date(self, d: str | date) -> date:
        """Parse a date from string or return as-is if already a date."""
        if isinstance(d, date):
            return d
        return date.fromisoformat(str(d))

    def _get_value(self, results: dict, key: str) -> float | None:
        """Get a float value from criterion results."""
        if key not in results:
            return None
        value = results[key].get("value")
        if value is None:
            return None
        return float(value)

    def _get_value_int(self, results: dict, key: str) -> int | None:
        """Get an int value from criterion results."""
        value = self._get_value(results, key)
        if value is None:
            return None
        return int(value)

    def _get_passed(self, results: dict, key: str) -> bool | None:
        """Get a passed status from criterion results."""
        if key not in results:
            return None
        return results[key].get("passed")
