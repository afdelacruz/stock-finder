"""Tests for swing low/high detection algorithms."""

import pandas as pd
import pytest
from datetime import date

from stock_finder.analysis.models import SwingPoint
from stock_finder.analysis.trendline.swing_detection import (
    detect_swing_lows,
    detect_swing_highs,
    filter_ascending_lows,
)


def make_ohlcv_df(prices: list[float], start_date: str = "2020-01-01") -> pd.DataFrame:
    """Create a simple OHLCV DataFrame for testing.

    Uses the price as both High and Low for simplicity.
    For swing detection, we primarily care about Low (for lows) and High (for highs).
    """
    dates = pd.date_range(start=start_date, periods=len(prices), freq="D")
    return pd.DataFrame(
        {
            "Open": prices,
            "High": prices,
            "Low": prices,
            "Close": prices,
            "Volume": [1000000] * len(prices),
        },
        index=dates,
    )


def make_ohlcv_df_with_lows(lows: list[float], start_date: str = "2020-01-01") -> pd.DataFrame:
    """Create OHLCV DataFrame where Low values are specified."""
    dates = pd.date_range(start=start_date, periods=len(lows), freq="D")
    # High is slightly above low, Close somewhere in between
    highs = [l + 1.0 for l in lows]
    closes = [l + 0.5 for l in lows]
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


class TestDetectSwingLows:
    """Tests for detect_swing_lows function."""

    def test_empty_dataframe_returns_empty_list(self):
        """Empty DataFrame should return empty list."""
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = detect_swing_lows(df, lookback=3)
        assert result == []

    def test_dataframe_too_short_returns_empty(self):
        """DataFrame shorter than 2*lookback+1 should return empty."""
        # With lookback=3, need at least 7 bars to find any swing
        df = make_ohlcv_df([10, 9, 8, 9, 10])  # 5 bars
        result = detect_swing_lows(df, lookback=3)
        assert result == []

    def test_single_swing_low_in_middle(self):
        """Detect a single clear swing low in the middle of data."""
        # V-shape: prices go down then up
        # With lookback=2, bar index 4 (price 5) should be detected
        prices = [10, 8, 7, 6, 5, 6, 7, 8, 10]
        df = make_ohlcv_df_with_lows(prices)
        result = detect_swing_lows(df, lookback=2)

        assert len(result) == 1
        assert result[0].price == 5.0
        assert result[0].bar_index == 4

    def test_multiple_swing_lows(self):
        """Detect multiple swing lows (W pattern)."""
        # W-shape: two valleys
        prices = [10, 8, 5, 8, 10, 8, 6, 8, 10]
        df = make_ohlcv_df_with_lows(prices)
        result = detect_swing_lows(df, lookback=2)

        assert len(result) == 2
        assert result[0].price == 5.0  # First valley
        assert result[0].bar_index == 2
        assert result[1].price == 6.0  # Second valley
        assert result[1].bar_index == 6

    def test_lookback_affects_sensitivity(self):
        """Larger lookback should filter out minor swing lows."""
        # Minor dip followed by major dip
        prices = [10, 9, 8, 9, 10, 8, 5, 8, 10, 11, 12]
        df = make_ohlcv_df_with_lows(prices)

        # With lookback=2, both should be detected
        result_small = detect_swing_lows(df, lookback=2)

        # With lookback=4, only the major low at 5 should be detected
        # because we need 4 bars on each side
        result_large = detect_swing_lows(df, lookback=4)

        assert len(result_small) >= 1
        assert len(result_large) >= 1
        # The larger lookback should find the major low
        assert any(s.price == 5.0 for s in result_large)

    def test_swing_low_returns_swingpoint_objects(self):
        """Result should be SwingPoint dataclass instances."""
        prices = [10, 8, 5, 8, 10]
        df = make_ohlcv_df_with_lows(prices)
        result = detect_swing_lows(df, lookback=2)

        assert len(result) == 1
        assert isinstance(result[0], SwingPoint)
        assert isinstance(result[0].date, date)
        assert isinstance(result[0].price, float)
        assert isinstance(result[0].bar_index, int)

    def test_swing_low_date_matches_dataframe_index(self):
        """SwingPoint date should match the DataFrame index."""
        prices = [10, 8, 5, 8, 10]
        df = make_ohlcv_df_with_lows(prices, start_date="2020-06-15")
        result = detect_swing_lows(df, lookback=2)

        assert len(result) == 1
        # Bar index 2 -> 2 days after start -> 2020-06-17
        assert result[0].date == date(2020, 6, 17)

    def test_flat_prices_no_swing_lows(self):
        """Flat prices should not produce swing lows."""
        prices = [10, 10, 10, 10, 10, 10, 10]
        df = make_ohlcv_df_with_lows(prices)
        result = detect_swing_lows(df, lookback=2)
        # When all prices are equal, no bar is strictly lower than neighbors
        assert result == []

    def test_monotonic_decline_no_swing_lows(self):
        """Steadily declining prices have no swing lows."""
        prices = [10, 9, 8, 7, 6, 5, 4]
        df = make_ohlcv_df_with_lows(prices)
        result = detect_swing_lows(df, lookback=2)
        assert result == []

    def test_monotonic_increase_no_swing_lows(self):
        """Steadily rising prices have no swing lows."""
        prices = [4, 5, 6, 7, 8, 9, 10]
        df = make_ohlcv_df_with_lows(prices)
        result = detect_swing_lows(df, lookback=2)
        assert result == []


class TestDetectSwingHighs:
    """Tests for detect_swing_highs function."""

    def test_single_swing_high(self):
        """Detect a single swing high (peak)."""
        # Inverted V: prices go up then down
        highs = [5, 7, 10, 7, 5]
        dates = pd.date_range(start="2020-01-01", periods=len(highs), freq="D")
        df = pd.DataFrame(
            {
                "Open": [h - 0.5 for h in highs],
                "High": highs,
                "Low": [h - 1.0 for h in highs],
                "Close": [h - 0.5 for h in highs],
                "Volume": [1000000] * len(highs),
            },
            index=dates,
        )
        result = detect_swing_highs(df, lookback=2)

        assert len(result) == 1
        assert result[0].price == 10.0
        assert result[0].bar_index == 2

    def test_multiple_swing_highs(self):
        """Detect multiple swing highs (M pattern)."""
        # M-shape: two peaks with enough bars on each side
        highs = [5, 7, 10, 7, 5, 7, 12, 7, 5]
        dates = pd.date_range(start="2020-01-01", periods=len(highs), freq="D")
        df = pd.DataFrame(
            {
                "Open": [h - 0.5 for h in highs],
                "High": highs,
                "Low": [h - 1.0 for h in highs],
                "Close": [h - 0.5 for h in highs],
                "Volume": [1000000] * len(highs),
            },
            index=dates,
        )
        result = detect_swing_highs(df, lookback=2)

        assert len(result) == 2
        assert result[0].price == 10.0
        assert result[1].price == 12.0


class TestFilterAscendingLows:
    """Tests for filter_ascending_lows function."""

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        result = filter_ascending_lows([])
        assert result == []

    def test_single_point_returns_single(self):
        """Single swing low is returned as-is."""
        swing = SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0)
        result = filter_ascending_lows([swing])
        assert result == [swing]

    def test_ascending_lows_all_kept(self):
        """Truly ascending swing lows are all kept."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=12.0, bar_index=10),
            SwingPoint(date=date(2020, 1, 20), price=15.0, bar_index=20),
        ]
        result = filter_ascending_lows(swings)
        assert len(result) == 3
        assert result == swings

    def test_descending_low_filtered_out(self):
        """A lower low breaks the ascending pattern and is filtered."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=15.0, bar_index=10),
            SwingPoint(date=date(2020, 1, 20), price=12.0, bar_index=20),  # Lower than 15
        ]
        result = filter_ascending_lows(swings)
        # Should keep only first two (10, 15) since 12 < 15
        assert len(result) == 2
        assert result[0].price == 10.0
        assert result[1].price == 15.0

    def test_equal_lows_filtered_out(self):
        """Equal lows should be filtered (not strictly ascending)."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=10.0, bar_index=10),  # Equal
        ]
        result = filter_ascending_lows(swings)
        assert len(result) == 1
        assert result[0].price == 10.0

    def test_mixed_pattern_filters_correctly(self):
        """Complex pattern with some ascending, some descending."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 5), price=8.0, bar_index=5),    # Lower - filtered
            SwingPoint(date=date(2020, 1, 10), price=12.0, bar_index=10), # Higher than 10 - kept
            SwingPoint(date=date(2020, 1, 15), price=11.0, bar_index=15), # Lower than 12 - filtered
            SwingPoint(date=date(2020, 1, 20), price=15.0, bar_index=20), # Higher than 12 - kept
        ]
        result = filter_ascending_lows(swings)
        # Expected: 10 -> 12 -> 15
        assert len(result) == 3
        assert [s.price for s in result] == [10.0, 12.0, 15.0]

    def test_returns_new_list(self):
        """Result should be a new list, not mutate input."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=5.0, bar_index=10),
        ]
        original_len = len(swings)
        result = filter_ascending_lows(swings)
        assert len(swings) == original_len  # Original unchanged
        assert result is not swings
