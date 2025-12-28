"""Unit tests for calculation functions."""

from datetime import date

import pandas as pd
import pytest

from stock_finder.utils.calculations import calculate_max_gain


class TestCalculateMaxGain:
    """Tests for calculate_max_gain function."""

    def test_simple_uptrend(self):
        """Stock goes from 10 to 60 = 500% gain."""
        dates = pd.date_range("2022-01-01", periods=5, freq="D")
        df = pd.DataFrame({"Close": [10, 20, 30, 40, 60]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.ticker == "TEST"
        assert result.gain_pct == 500.0
        assert result.low_price == 10
        assert result.high_price == 60

    def test_gain_below_threshold_returns_none(self):
        """Stock with only 100% gain should return None for 500% threshold."""
        dates = pd.date_range("2022-01-01", periods=5, freq="D")
        df = pd.DataFrame({"Close": [10, 15, 20, 18, 20]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is None

    def test_finds_best_gain_with_dip(self):
        """Stock dips then rallies - should find the dip as entry."""
        dates = pd.date_range("2022-01-01", periods=7, freq="D")
        # Starts at 50, dips to 10, rallies to 70
        df = pd.DataFrame({"Close": [50, 40, 30, 10, 30, 50, 70]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.low_price == 10
        assert result.high_price == 70
        assert result.gain_pct == 600.0

    def test_multiple_rallies_finds_best(self):
        """With multiple rallies, finds the best overall gain."""
        dates = pd.date_range("2022-01-01", periods=10, freq="D")
        # Two rallies: 10->50 (400%), then dips to 5, then 5->35 (600%)
        df = pd.DataFrame(
            {"Close": [10, 20, 30, 50, 40, 5, 10, 20, 30, 35]},
            index=dates,
        )

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.low_price == 5
        assert result.high_price == 35
        assert result.gain_pct == 600.0

    def test_empty_dataframe_returns_none(self):
        """Empty DataFrame should return None."""
        df = pd.DataFrame({"Close": []})

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is None

    def test_single_row_returns_none(self):
        """Single data point can't have a gain."""
        dates = pd.date_range("2022-01-01", periods=1, freq="D")
        df = pd.DataFrame({"Close": [100]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is None

    def test_calculates_days_to_peak(self):
        """Should correctly calculate trading days from low to high."""
        dates = pd.date_range("2022-01-01", periods=10, freq="D")
        # Low on day 2 (index 1), high on day 8 (index 7)
        df = pd.DataFrame(
            {"Close": [50, 10, 20, 30, 40, 50, 60, 70, 65, 60]},
            index=dates,
        )

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.days_to_peak == 6  # From index 1 to index 7

    def test_tracks_correct_dates(self):
        """Should record the correct low and high dates."""
        dates = pd.date_range("2022-06-15", periods=5, freq="D")
        df = pd.DataFrame({"Close": [100, 10, 30, 60, 70]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.low_date == date(2022, 6, 16)
        assert result.high_date == date(2022, 6, 19)

    def test_current_price_is_last_close(self):
        """Current price should be the most recent close."""
        dates = pd.date_range("2022-01-01", periods=5, freq="D")
        df = pd.DataFrame({"Close": [10, 20, 70, 50, 40]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.current_price == 40  # Last value

    def test_missing_close_column_returns_none(self):
        """DataFrame without Close column should return None."""
        dates = pd.date_range("2022-01-01", periods=5, freq="D")
        df = pd.DataFrame({"Open": [10, 20, 30, 40, 50]}, index=dates)

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is None

    def test_handles_nan_values(self):
        """Should handle NaN values in data."""
        dates = pd.date_range("2022-01-01", periods=7, freq="D")
        df = pd.DataFrame(
            {"Close": [10, float("nan"), 20, 30, float("nan"), 60, 65]},
            index=dates,
        )

        result = calculate_max_gain("TEST", df, min_gain_pct=500)

        assert result is not None
        assert result.gain_pct == 550.0  # 10 to 65
