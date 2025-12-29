"""Unit tests for Neumann scoring criteria (TDD)."""

from datetime import date

import pandas as pd
import pytest

from stock_finder.scoring.criteria.base import CriterionResult, ScoringContext


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_historical_data() -> pd.DataFrame:
    """
    Create sample historical data simulating a stock that declined significantly.

    Pattern: Started at 100, peaked at 120, declined to 20 (ignition point)
    - 2-year high: 120
    - 2-year low: 18 (slight dip before ignition)
    - Ignition price: 20
    """
    dates = pd.date_range("2020-01-01", periods=500, freq="D")

    # Build price pattern: rise, peak, decline
    prices = []
    volumes = []

    for i in range(500):
        if i < 50:
            # Initial rise to peak
            price = 100 + (i / 50) * 20  # 100 -> 120
            volume = 1_000_000
        elif i < 100:
            # Plateau near peak
            price = 120 - (i - 50) * 0.2  # 120 -> 110
            volume = 800_000
        elif i < 400:
            # Long decline
            price = 110 - ((i - 100) / 300) * 90  # 110 -> 20
            volume = 500_000 - (i - 100) * 1000  # Declining volume
        else:
            # Near ignition (low volume, near lows)
            price = 20 + (i - 400) * 0.02  # ~20
            volume = 200_000  # Exhausted volume

        prices.append(price)
        volumes.append(max(volume, 100_000))

    return pd.DataFrame(
        {
            "Open": prices,
            "High": [p * 1.02 for p in prices],
            "Low": [p * 0.98 for p in prices],
            "Close": prices,
            "Volume": volumes,
        },
        index=dates,
    )


@pytest.fixture
def scoring_context(sample_historical_data) -> ScoringContext:
    """Create a standard scoring context for testing."""
    return ScoringContext(
        ticker="TEST",
        ignition_date=date(2021, 5, 15),  # Near end of data
        ignition_price=20.0,
        historical_data=sample_historical_data,
        gain_pct=500.0,
        high_date=date(2022, 1, 15),
        high_price=120.0,
        shares_outstanding=10_000_000,  # 10M shares
        sma_data={"sma50": 35.0, "sma200": 55.0},  # Price below both SMAs
    )


@pytest.fixture
def context_near_highs(sample_historical_data) -> ScoringContext:
    """Context where stock is near highs (should fail most criteria)."""
    return ScoringContext(
        ticker="STRONG",
        ignition_date=date(2020, 2, 20),
        ignition_price=115.0,  # Near the peak
        historical_data=sample_historical_data,
        gain_pct=100.0,
        high_date=date(2020, 6, 1),
        high_price=130.0,
        shares_outstanding=10_000_000,
        sma_data={"sma50": 110.0, "sma200": 100.0},  # Price above SMAs
    )


@pytest.fixture
def context_missing_data() -> ScoringContext:
    """Context with insufficient data."""
    return ScoringContext(
        ticker="NODATA",
        ignition_date=date(2022, 1, 1),
        ignition_price=50.0,
        historical_data=pd.DataFrame(),  # Empty
        gain_pct=300.0,
        high_date=date(2022, 6, 1),
        high_price=200.0,
    )


# =============================================================================
# Test ScoringContext Properties
# =============================================================================


class TestScoringContext:
    """Tests for ScoringContext computed properties."""

    def test_has_sufficient_data_with_data(self, scoring_context):
        """Should return True when data has 50+ rows."""
        assert scoring_context.has_sufficient_data is True

    def test_has_sufficient_data_empty(self, context_missing_data):
        """Should return False for empty DataFrame."""
        assert context_missing_data.has_sufficient_data is False

    def test_two_year_high(self, scoring_context):
        """Should find the maximum high price."""
        high = scoring_context.two_year_high
        assert high is not None
        assert high > 100  # Should find the peak

    def test_two_year_low(self, scoring_context):
        """Should find the minimum low price."""
        low = scoring_context.two_year_low
        assert low is not None
        assert low < 30  # Should find near the bottom

    def test_range_position_near_lows(self, scoring_context):
        """Stock at $20 with high of ~120, low of ~18 should be near 0."""
        position = scoring_context.range_position
        assert position is not None
        assert position < 0.1  # Near the bottom of range

    def test_range_position_near_highs(self, context_near_highs):
        """Stock at $115 near high of $120 should be near 1.0."""
        position = context_near_highs.range_position
        assert position is not None
        assert position > 0.8  # Near the top of range

    def test_estimated_market_cap(self, scoring_context):
        """Market cap should be shares * price."""
        cap = scoring_context.estimated_market_cap
        assert cap == 20.0 * 10_000_000  # $200M

    def test_estimated_market_cap_no_shares(self, context_missing_data):
        """Should return None if shares_outstanding not set."""
        assert context_missing_data.estimated_market_cap is None


# =============================================================================
# Tests for DrawdownCriterion
# =============================================================================


class TestDrawdownCriterion:
    """Tests for significant drawdown criterion."""

    def test_passes_when_drawdown_exceeds_threshold(self, scoring_context):
        """Stock at $20 from peak of $120+ should pass 50% drawdown test."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        criterion = DrawdownCriterion(threshold=-0.50)
        result = criterion.evaluate(scoring_context)

        assert result.passed is True
        assert result.value is not None
        assert result.value <= -0.50  # Drawdown should be >= 50%
        assert "drawdown" in result.details.lower()

    def test_fails_when_drawdown_below_threshold(self, context_near_highs):
        """Stock near highs should fail drawdown test."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        criterion = DrawdownCriterion(threshold=-0.50)
        result = criterion.evaluate(context_near_highs)

        assert result.passed is False
        assert result.value is not None
        assert result.value > -0.50  # Drawdown less than 50%

    def test_handles_missing_data(self, context_missing_data):
        """Should return failed result with explanation when data missing."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        criterion = DrawdownCriterion()
        result = criterion.evaluate(context_missing_data)

        assert result.passed is False
        assert result.value is None
        assert "unable" in result.details.lower()

    def test_configurable_threshold(self, scoring_context):
        """Should respect custom threshold."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        # Very strict threshold
        strict = DrawdownCriterion(threshold=-0.90)
        result = strict.evaluate(scoring_context)

        # 20/120 = 0.167, so drawdown is -83%, fails -90% threshold
        assert result.passed is False

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        criterion = DrawdownCriterion()
        assert criterion.name == "drawdown"

    def test_has_description(self):
        """Criterion should have a description."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        criterion = DrawdownCriterion()
        assert len(criterion.description) > 10


# =============================================================================
# Tests for ExtendedDeclineCriterion
# =============================================================================


class TestExtendedDeclineCriterion:
    """Tests for extended decline (days since high) criterion."""

    def test_passes_when_decline_long_enough(self, scoring_context):
        """Stock that peaked 300+ days ago should pass 90-day test."""
        from stock_finder.scoring.criteria.extended_decline import (
            ExtendedDeclineCriterion,
        )

        criterion = ExtendedDeclineCriterion(min_days=90)
        result = criterion.evaluate(scoring_context)

        assert result.passed is True
        assert result.value is not None
        assert result.value >= 90

    def test_fails_when_decline_too_short(self, context_near_highs):
        """Stock recently at highs should fail."""
        from stock_finder.scoring.criteria.extended_decline import (
            ExtendedDeclineCriterion,
        )

        criterion = ExtendedDeclineCriterion(min_days=90)
        result = criterion.evaluate(context_near_highs)

        assert result.passed is False

    def test_handles_missing_data(self, context_missing_data):
        """Should handle missing data gracefully."""
        from stock_finder.scoring.criteria.extended_decline import (
            ExtendedDeclineCriterion,
        )

        criterion = ExtendedDeclineCriterion()
        result = criterion.evaluate(context_missing_data)

        assert result.passed is False
        assert result.value is None

    def test_configurable_min_days(self, scoring_context):
        """Should respect custom min_days threshold."""
        from stock_finder.scoring.criteria.extended_decline import (
            ExtendedDeclineCriterion,
        )

        # Very long requirement
        strict = ExtendedDeclineCriterion(min_days=1000)
        result = strict.evaluate(scoring_context)

        # Only 500 days of data, can't have 1000 day decline
        assert result.passed is False

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.extended_decline import (
            ExtendedDeclineCriterion,
        )

        criterion = ExtendedDeclineCriterion()
        assert criterion.name == "extended_decline"


# =============================================================================
# Tests for NearLowsCriterion
# =============================================================================


class TestNearLowsCriterion:
    """Tests for near lows (position in range) criterion."""

    def test_passes_when_near_lows(self, scoring_context):
        """Stock in bottom 20% of range should pass."""
        from stock_finder.scoring.criteria.near_lows import NearLowsCriterion

        criterion = NearLowsCriterion(max_position=0.20)
        result = criterion.evaluate(scoring_context)

        assert result.passed is True
        assert result.value is not None
        assert result.value <= 0.20

    def test_fails_when_near_highs(self, context_near_highs):
        """Stock near highs should fail."""
        from stock_finder.scoring.criteria.near_lows import NearLowsCriterion

        criterion = NearLowsCriterion(max_position=0.20)
        result = criterion.evaluate(context_near_highs)

        assert result.passed is False
        assert result.value is not None
        assert result.value > 0.20

    def test_handles_missing_data(self, context_missing_data):
        """Should handle missing data gracefully."""
        from stock_finder.scoring.criteria.near_lows import NearLowsCriterion

        criterion = NearLowsCriterion()
        result = criterion.evaluate(context_missing_data)

        assert result.passed is False
        assert result.value is None

    def test_configurable_max_position(self, scoring_context):
        """Should respect custom max_position threshold."""
        from stock_finder.scoring.criteria.near_lows import NearLowsCriterion

        # Very strict - must be in bottom 5%
        strict = NearLowsCriterion(max_position=0.05)
        result = strict.evaluate(scoring_context)

        # Depends on exact data, but tests configurability
        assert result.threshold == 0.05

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.near_lows import NearLowsCriterion

        criterion = NearLowsCriterion()
        assert criterion.name == "near_lows"


# =============================================================================
# Tests for BelowSMA50Criterion
# =============================================================================


class TestBelowSMA50Criterion:
    """Tests for below 50-day SMA criterion."""

    def test_passes_when_below_sma(self, scoring_context):
        """Stock at $20 with SMA50 of $35 should pass."""
        from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion

        criterion = BelowSMA50Criterion(threshold=-0.10)
        result = criterion.evaluate(scoring_context)

        assert result.passed is True
        assert result.value is not None
        # 20/35 - 1 = -0.43, so definitely < -0.10
        assert result.value < -0.10

    def test_fails_when_above_sma(self, context_near_highs):
        """Stock above SMA should fail."""
        from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion

        criterion = BelowSMA50Criterion(threshold=-0.10)
        result = criterion.evaluate(context_near_highs)

        assert result.passed is False

    def test_handles_missing_sma_data(self, scoring_context):
        """Should handle missing SMA data gracefully."""
        from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion

        # Remove SMA data
        scoring_context.sma_data = {}

        criterion = BelowSMA50Criterion()
        result = criterion.evaluate(scoring_context)

        assert result.passed is False
        assert "sma" in result.details.lower() or "missing" in result.details.lower()

    def test_configurable_threshold(self, scoring_context):
        """Should respect custom threshold."""
        from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion

        # Must be 50% below SMA
        strict = BelowSMA50Criterion(threshold=-0.50)
        result = strict.evaluate(scoring_context)

        # 20/35 - 1 = -0.43, fails -0.50 threshold
        assert result.passed is False

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion

        criterion = BelowSMA50Criterion()
        assert criterion.name == "below_sma50"


# =============================================================================
# Tests for BelowSMA200Criterion
# =============================================================================


class TestBelowSMA200Criterion:
    """Tests for below 200-day SMA criterion."""

    def test_passes_when_below_sma(self, scoring_context):
        """Stock at $20 with SMA200 of $55 should pass."""
        from stock_finder.scoring.criteria.below_sma200 import BelowSMA200Criterion

        criterion = BelowSMA200Criterion(threshold=-0.10)
        result = criterion.evaluate(scoring_context)

        assert result.passed is True
        assert result.value is not None
        # 20/55 - 1 = -0.64, so definitely < -0.10
        assert result.value < -0.10

    def test_fails_when_above_sma(self, context_near_highs):
        """Stock above SMA should fail."""
        from stock_finder.scoring.criteria.below_sma200 import BelowSMA200Criterion

        criterion = BelowSMA200Criterion(threshold=-0.10)
        result = criterion.evaluate(context_near_highs)

        assert result.passed is False

    def test_handles_missing_sma_data(self, scoring_context):
        """Should handle missing SMA data gracefully."""
        from stock_finder.scoring.criteria.below_sma200 import BelowSMA200Criterion

        scoring_context.sma_data = {}

        criterion = BelowSMA200Criterion()
        result = criterion.evaluate(scoring_context)

        assert result.passed is False

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.below_sma200 import BelowSMA200Criterion

        criterion = BelowSMA200Criterion()
        assert criterion.name == "below_sma200"


# =============================================================================
# Tests for VolumeExhaustionCriterion
# =============================================================================


class TestVolumeExhaustionCriterion:
    """Tests for volume exhaustion criterion."""

    def test_passes_when_volume_low(self, scoring_context):
        """Stock with low volume at ignition should pass."""
        from stock_finder.scoring.criteria.volume_exhaustion import (
            VolumeExhaustionCriterion,
        )

        criterion = VolumeExhaustionCriterion(max_ratio=1.0)
        result = criterion.evaluate(scoring_context)

        # Our test data has declining volume, so should pass
        assert result.passed is True
        assert result.value is not None
        assert result.value <= 1.0  # Changed to <= since criterion uses <=

    def test_fails_when_volume_high(self):
        """Stock with high volume at ignition should fail."""
        from stock_finder.scoring.criteria.volume_exhaustion import (
            VolumeExhaustionCriterion,
        )

        # Create data with spike in volume at end
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = [50] * 100
        volumes = [100_000] * 90 + [500_000] * 10  # Spike at end

        df = pd.DataFrame(
            {
                "Open": prices,
                "High": prices,
                "Low": prices,
                "Close": prices,
                "Volume": volumes,
            },
            index=dates,
        )

        context = ScoringContext(
            ticker="HIGHVOL",
            ignition_date=date(2020, 4, 10),
            ignition_price=50.0,
            historical_data=df,
            gain_pct=100.0,
            high_date=date(2020, 6, 1),
            high_price=100.0,
        )

        criterion = VolumeExhaustionCriterion(max_ratio=1.0)
        result = criterion.evaluate(context)

        assert result.passed is False
        assert result.value > 1.0  # Above the <= 1.0 threshold

    def test_handles_missing_data(self, context_missing_data):
        """Should handle missing data gracefully."""
        from stock_finder.scoring.criteria.volume_exhaustion import (
            VolumeExhaustionCriterion,
        )

        criterion = VolumeExhaustionCriterion()
        result = criterion.evaluate(context_missing_data)

        assert result.passed is False
        assert result.value is None

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.volume_exhaustion import (
            VolumeExhaustionCriterion,
        )

        criterion = VolumeExhaustionCriterion()
        assert criterion.name == "volume_exhaustion"


# =============================================================================
# Tests for MarketCapCriterion
# =============================================================================


class TestMarketCapCriterion:
    """Tests for market cap sweet spot criterion."""

    def test_passes_when_in_sweet_spot(self, scoring_context):
        """Stock with $200M market cap should pass $200M-$2B range."""
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion

        criterion = MarketCapCriterion(
            min_cap=200_000_000,
            max_cap=2_000_000_000,
        )
        result = criterion.evaluate(scoring_context)

        # 10M shares * $20 = $200M - right at the boundary
        assert result.passed is True
        assert result.value == 200_000_000

    def test_fails_when_too_small(self, scoring_context):
        """Stock with tiny market cap should fail."""
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion

        # Make it a micro-cap
        scoring_context.shares_outstanding = 100_000  # 100K shares * $20 = $2M

        criterion = MarketCapCriterion(min_cap=200_000_000)
        result = criterion.evaluate(scoring_context)

        assert result.passed is False
        assert result.value == 2_000_000

    def test_fails_when_too_large(self, scoring_context):
        """Stock with huge market cap should fail."""
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion

        # Make it a mega-cap
        scoring_context.shares_outstanding = 1_000_000_000  # 1B shares * $20 = $20B

        criterion = MarketCapCriterion(max_cap=2_000_000_000)
        result = criterion.evaluate(scoring_context)

        assert result.passed is False

    def test_handles_missing_shares(self, context_missing_data):
        """Should handle missing shares_outstanding gracefully."""
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion

        criterion = MarketCapCriterion()
        result = criterion.evaluate(context_missing_data)

        assert result.passed is False
        assert result.value is None
        assert "shares" in result.details.lower() or "market cap" in result.details.lower()

    def test_configurable_range(self, scoring_context):
        """Should respect custom min/max caps."""
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion

        # Very narrow range
        criterion = MarketCapCriterion(
            min_cap=100_000_000,
            max_cap=150_000_000,
        )
        result = criterion.evaluate(scoring_context)

        # $200M doesn't fit in $100M-$150M range
        assert result.passed is False

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion

        criterion = MarketCapCriterion()
        assert criterion.name == "market_cap"


# =============================================================================
# Tests for TrendlineBreakCriterion
# =============================================================================


class TestTrendlineBreakCriterion:
    """Tests for trendline break (SMA crossover) criterion."""

    def test_passes_when_crossing_above_sma(self):
        """Stock crossing above SMA50 should pass."""
        from stock_finder.scoring.criteria.trendline_break import (
            TrendlineBreakCriterion,
        )

        # Create data where price crosses above SMA
        dates = pd.date_range("2020-01-01", periods=100, freq="D")

        # Price starts below and crosses above at the end
        prices = [40] * 80 + list(range(40, 60))  # Rises from 40 to 59

        df = pd.DataFrame(
            {
                "Open": prices,
                "High": [p * 1.01 for p in prices],
                "Low": [p * 0.99 for p in prices],
                "Close": prices,
                "Volume": [100_000] * 100,
            },
            index=dates,
        )

        context = ScoringContext(
            ticker="BREAKOUT",
            ignition_date=date(2020, 4, 10),
            ignition_price=59.0,  # Above the SMA now
            historical_data=df,
            gain_pct=200.0,
            high_date=date(2020, 6, 1),
            high_price=120.0,
            sma_data={"sma50": 45.0},  # Price (59) is above SMA (45)
        )

        criterion = TrendlineBreakCriterion()
        result = criterion.evaluate(context)

        assert result.passed is True

    def test_fails_when_still_below_sma(self, scoring_context):
        """Stock still below SMA should fail."""
        from stock_finder.scoring.criteria.trendline_break import (
            TrendlineBreakCriterion,
        )

        # scoring_context has price=20, sma50=35, so still below
        criterion = TrendlineBreakCriterion()
        result = criterion.evaluate(scoring_context)

        assert result.passed is False

    def test_handles_missing_sma_data(self, scoring_context):
        """Should handle missing SMA data gracefully."""
        from stock_finder.scoring.criteria.trendline_break import (
            TrendlineBreakCriterion,
        )

        scoring_context.sma_data = {}

        criterion = TrendlineBreakCriterion()
        result = criterion.evaluate(scoring_context)

        assert result.passed is False
        assert "sma" in result.details.lower()

    def test_has_correct_name(self):
        """Criterion should have identifiable name."""
        from stock_finder.scoring.criteria.trendline_break import (
            TrendlineBreakCriterion,
        )

        criterion = TrendlineBreakCriterion()
        assert criterion.name == "trendline_break"


# =============================================================================
# Contract Tests - Verify All Criteria Implement Interface
# =============================================================================


class TestCriteriaContract:
    """Verify all criteria properly implement the Criterion interface."""

    @pytest.fixture
    def all_criteria(self):
        """Get all criterion classes."""
        from stock_finder.scoring.criteria.below_sma50 import BelowSMA50Criterion
        from stock_finder.scoring.criteria.below_sma200 import BelowSMA200Criterion
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion
        from stock_finder.scoring.criteria.extended_decline import (
            ExtendedDeclineCriterion,
        )
        from stock_finder.scoring.criteria.market_cap import MarketCapCriterion
        from stock_finder.scoring.criteria.near_lows import NearLowsCriterion
        from stock_finder.scoring.criteria.trendline_break import (
            TrendlineBreakCriterion,
        )
        from stock_finder.scoring.criteria.volume_exhaustion import (
            VolumeExhaustionCriterion,
        )

        return [
            DrawdownCriterion(),
            ExtendedDeclineCriterion(),
            NearLowsCriterion(),
            BelowSMA50Criterion(),
            BelowSMA200Criterion(),
            VolumeExhaustionCriterion(),
            MarketCapCriterion(),
            TrendlineBreakCriterion(),
        ]

    def test_all_have_unique_names(self, all_criteria):
        """All criteria should have unique names."""
        names = [c.name for c in all_criteria]
        assert len(names) == len(set(names)), f"Duplicate names found: {names}"

    def test_all_have_descriptions(self, all_criteria):
        """All criteria should have non-empty descriptions."""
        for criterion in all_criteria:
            assert criterion.description, f"{criterion.name} has no description"
            assert len(criterion.description) > 10

    def test_all_return_criterion_result(self, all_criteria, scoring_context):
        """All criteria should return CriterionResult from evaluate()."""
        for criterion in all_criteria:
            result = criterion.evaluate(scoring_context)
            assert isinstance(result, CriterionResult), f"{criterion.name} returned wrong type"

    def test_all_handle_missing_data(self, all_criteria, context_missing_data):
        """All criteria should handle missing data without raising exceptions."""
        for criterion in all_criteria:
            # Should not raise
            result = criterion.evaluate(context_missing_data)
            assert isinstance(result, CriterionResult)
            # With missing data, should fail gracefully
            assert result.passed is False

    def test_result_to_dict(self, all_criteria, scoring_context):
        """All results should be serializable to dict."""
        for criterion in all_criteria:
            result = criterion.evaluate(scoring_context)
            d = result.to_dict()
            assert "name" in d
            assert "passed" in d
            assert "value" in d
            assert "threshold" in d
            assert "details" in d


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exact_threshold_boundary_drawdown(self):
        """Test behavior at exact -50% drawdown threshold."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = [100] * 50 + [50] * 50  # Exact 50% decline

        df = pd.DataFrame(
            {
                "Open": prices,
                "High": [p * 1.01 for p in prices],
                "Low": [p * 0.99 for p in prices],
                "Close": prices,
                "Volume": [100_000] * 100,
            },
            index=dates,
        )

        context = ScoringContext(
            ticker="BOUNDARY",
            ignition_date=date(2020, 4, 10),
            ignition_price=50.0,
            historical_data=df,
            gain_pct=200.0,
            high_date=date(2020, 6, 1),
            high_price=150.0,
        )

        criterion = DrawdownCriterion(threshold=-0.50)
        result = criterion.evaluate(context)

        # Exactly -50% should pass (<=)
        assert result.passed is True

    def test_zero_volume(self, scoring_context):
        """Should handle zero volume gracefully."""
        from stock_finder.scoring.criteria.volume_exhaustion import (
            VolumeExhaustionCriterion,
        )

        # Set all volumes to 0
        scoring_context.historical_data["Volume"] = 0

        criterion = VolumeExhaustionCriterion()
        result = criterion.evaluate(scoring_context)

        # Should not crash, should handle gracefully
        assert isinstance(result, CriterionResult)

    def test_single_day_data(self):
        """Should handle single day of data."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        dates = pd.date_range("2020-01-01", periods=1, freq="D")
        df = pd.DataFrame(
            {
                "Open": [100],
                "High": [101],
                "Low": [99],
                "Close": [100],
                "Volume": [100_000],
            },
            index=dates,
        )

        context = ScoringContext(
            ticker="ONEDAY",
            ignition_date=date(2020, 1, 1),
            ignition_price=100.0,
            historical_data=df,
            gain_pct=100.0,
            high_date=date(2020, 3, 1),
            high_price=200.0,
        )

        criterion = DrawdownCriterion()
        result = criterion.evaluate(context)

        # Should fail gracefully (insufficient data)
        assert result.passed is False

    def test_nan_values_in_data(self, scoring_context):
        """Should handle NaN values in historical data."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion

        # Inject some NaN values
        scoring_context.historical_data.loc[
            scoring_context.historical_data.index[10:20], "High"
        ] = float("nan")

        criterion = DrawdownCriterion()
        result = criterion.evaluate(scoring_context)

        # Should not crash
        assert isinstance(result, CriterionResult)
