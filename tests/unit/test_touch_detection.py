"""Tests for trendline touch detection."""

import pandas as pd
import pytest
from datetime import date

from stock_finder.analysis.models import SwingPoint, TrendlineFit, TouchPoint
from stock_finder.analysis.trendline.touch_detection import detect_touches


def make_trendline(slope: float, intercept: float) -> TrendlineFit:
    """Create a simple trendline for testing."""
    return TrendlineFit(
        slope=slope,
        intercept=intercept,
        r_squared=1.0,
        points=[],
    )


def make_ohlcv_df(lows: list[float], start_date: str = "2020-01-01") -> pd.DataFrame:
    """Create OHLCV DataFrame with specified Low values."""
    dates = pd.date_range(start=start_date, periods=len(lows), freq="D")
    highs = [l + 2.0 for l in lows]
    closes = [l + 1.0 for l in lows]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": [1000000] * len(lows),
        },
        index=dates,
    )


class TestDetectTouches:
    """Tests for detect_touches function."""

    def test_empty_dataframe_returns_empty(self):
        """Empty DataFrame should return no touches."""
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        trendline = make_trendline(slope=1.0, intercept=10.0)
        result = detect_touches(df, trendline)
        assert result == []

    def test_price_exactly_on_trendline(self):
        """Price exactly on trendline should be detected as touch."""
        # Trendline: y = 1.0*x + 10 -> at bar 5, y = 15
        trendline = make_trendline(slope=1.0, intercept=10.0)
        # Low prices exactly on trendline: 10, 11, 12, 13, 14, 15
        lows = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        # All bars should be touches (deviation = 0)
        assert len(result) == 6
        for touch in result:
            assert touch.deviation_pct == pytest.approx(0.0)

    def test_price_within_tolerance(self):
        """Price within tolerance should be detected as touch."""
        # Trendline: y = 0*x + 10 (flat at 10)
        trendline = make_trendline(slope=0.0, intercept=10.0)
        # Low at 10.1 is 1% above trendline (within 2% tolerance)
        lows = [10.1, 9.9, 10.15, 9.85]  # All within 2%
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 4

    def test_price_outside_tolerance(self):
        """Price outside tolerance should not be a touch."""
        # Trendline: y = 0*x + 10 (flat at 10)
        trendline = make_trendline(slope=0.0, intercept=10.0)
        # Low at 12 is 20% above trendline (outside 2% tolerance)
        lows = [12.0, 8.0, 15.0, 5.0]  # All way outside 2%
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 0

    def test_mixed_touches_and_non_touches(self):
        """Mixed prices should only detect valid touches."""
        # Trendline: y = 0*x + 10
        trendline = make_trendline(slope=0.0, intercept=10.0)
        # Some prices within 2%, some outside
        lows = [10.0, 15.0, 10.1, 5.0, 9.9, 20.0]
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        # Only bars 0, 2, 4 should be touches
        assert len(result) == 3
        bar_indices = [t.bar_index for t in result]
        assert 0 in bar_indices
        assert 2 in bar_indices
        assert 4 in bar_indices

    def test_touch_returns_touchpoint_objects(self):
        """Result should be TouchPoint dataclass instances."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [10.0]
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 1
        assert isinstance(result[0], TouchPoint)
        assert isinstance(result[0].date, date)
        assert isinstance(result[0].price, float)
        assert isinstance(result[0].trendline_price, float)
        assert isinstance(result[0].deviation_pct, float)
        assert isinstance(result[0].bar_index, int)

    def test_touch_deviation_positive_above_trendline(self):
        """Deviation should be positive when price is above trendline."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [10.1]  # 1% above trendline
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 1
        assert result[0].deviation_pct > 0
        assert result[0].deviation_pct == pytest.approx(0.01)

    def test_touch_deviation_negative_below_trendline(self):
        """Deviation should be negative when price is below trendline."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [9.9]  # 1% below trendline
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 1
        assert result[0].deviation_pct < 0
        assert result[0].deviation_pct == pytest.approx(-0.01)

    def test_trendline_price_stored_correctly(self):
        """TouchPoint should store the trendline price at that bar."""
        # Trendline: y = 1.0*x + 10
        trendline = make_trendline(slope=1.0, intercept=10.0)
        # At bar 5, trendline = 15. Price at 15 is exact touch.
        lows = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        # Check trendline prices
        for touch in result:
            expected_trendline = trendline.price_at_bar(touch.bar_index)
            assert touch.trendline_price == pytest.approx(expected_trendline)

    def test_tolerance_parameter_affects_detection(self):
        """Different tolerance values should change detection."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [10.3]  # 3% above trendline
        df = make_ohlcv_df(lows)

        # With 2% tolerance, should not be detected
        result_tight = detect_touches(df, trendline, tolerance=0.02)
        assert len(result_tight) == 0

        # With 5% tolerance, should be detected
        result_loose = detect_touches(df, trendline, tolerance=0.05)
        assert len(result_loose) == 1

    def test_sloped_trendline_touches(self):
        """Touches should work correctly with sloped trendlines."""
        # Trendline: y = 0.5*x + 10
        # At bar 0: 10, bar 2: 11, bar 4: 12, bar 6: 13
        trendline = make_trendline(slope=0.5, intercept=10.0)
        # Prices exactly on trendline
        lows = [10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0]
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        # All should be touches
        assert len(result) == 7

    def test_bar_index_stored_correctly(self):
        """TouchPoint bar_index should match position in DataFrame."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [15.0, 15.0, 10.0, 15.0, 10.0]  # Touches at bars 2 and 4
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 2
        assert result[0].bar_index == 2
        assert result[1].bar_index == 4

    def test_date_stored_correctly(self):
        """TouchPoint date should match DataFrame index."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [10.0]
        df = make_ohlcv_df(lows, start_date="2020-06-15")

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 1
        assert result[0].date == date(2020, 6, 15)

    def test_returns_sorted_by_bar_index(self):
        """Touches should be returned in bar index order."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [10.0, 20.0, 10.0, 20.0, 10.0]  # Touches at 0, 2, 4
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.02)

        assert len(result) == 3
        assert result[0].bar_index < result[1].bar_index < result[2].bar_index

    def test_zero_tolerance_exact_matches_only(self):
        """Zero tolerance should only match exact prices."""
        trendline = make_trendline(slope=0.0, intercept=10.0)
        lows = [10.0, 10.001, 9.999]  # First is exact, others very close
        df = make_ohlcv_df(lows)

        result = detect_touches(df, trendline, tolerance=0.0)

        # Only exact match
        assert len(result) == 1
        assert result[0].bar_index == 0
