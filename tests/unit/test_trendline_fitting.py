"""Tests for trendline fitting using linear regression."""

import pytest
from datetime import date

from stock_finder.analysis.models import SwingPoint, TrendlineFit
from stock_finder.analysis.trendline.trendline_fitting import fit_trendline


class TestFitTrendline:
    """Tests for fit_trendline function."""

    def test_empty_list_returns_none(self):
        """No points should return None."""
        result = fit_trendline([])
        assert result is None

    def test_single_point_returns_none(self):
        """Single point cannot define a line."""
        swing = SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0)
        result = fit_trendline([swing])
        assert result is None

    def test_two_points_perfect_fit(self):
        """Two points always define a perfect line (R² = 1.0)."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=20.0, bar_index=10),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert isinstance(result, TrendlineFit)
        assert result.r_squared == pytest.approx(1.0)
        # Slope: (20-10)/(10-0) = 1.0 per bar
        assert result.slope == pytest.approx(1.0)
        # Intercept: 10.0 (price at bar 0)
        assert result.intercept == pytest.approx(10.0)

    def test_three_points_perfect_line(self):
        """Three collinear points should have R² = 1.0."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 5), price=15.0, bar_index=5),
            SwingPoint(date=date(2020, 1, 10), price=20.0, bar_index=10),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.r_squared == pytest.approx(1.0)
        assert result.slope == pytest.approx(1.0)

    def test_noisy_data_lower_r_squared(self):
        """Points not perfectly on a line should have R² < 1.0."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 5), price=18.0, bar_index=5),  # Above line
            SwingPoint(date=date(2020, 1, 10), price=20.0, bar_index=10),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.r_squared < 1.0
        assert result.r_squared > 0.0  # Should still be positively correlated

    def test_slope_positive_for_ascending_prices(self):
        """Ascending prices should have positive slope."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=15.0, bar_index=10),
            SwingPoint(date=date(2020, 1, 20), price=22.0, bar_index=20),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.slope > 0

    def test_slope_negative_for_descending_prices(self):
        """Descending prices should have negative slope."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=20.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=15.0, bar_index=10),
            SwingPoint(date=date(2020, 1, 20), price=8.0, bar_index=20),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.slope < 0

    def test_slope_zero_for_flat_prices(self):
        """Flat prices should have zero slope."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=10.0, bar_index=10),
            SwingPoint(date=date(2020, 1, 20), price=10.0, bar_index=20),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.slope == pytest.approx(0.0, abs=1e-10)
        assert result.intercept == pytest.approx(10.0)

    def test_points_stored_in_result(self):
        """Result should store the input points."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=20.0, bar_index=10),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.points == swings

    def test_price_at_bar_method(self):
        """TrendlineFit.price_at_bar should calculate correctly."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 10), price=20.0, bar_index=10),
        ]
        result = fit_trendline(swings)

        assert result is not None
        # Slope = 1.0, intercept = 10.0
        assert result.price_at_bar(0) == pytest.approx(10.0)
        assert result.price_at_bar(5) == pytest.approx(15.0)
        assert result.price_at_bar(10) == pytest.approx(20.0)
        assert result.price_at_bar(15) == pytest.approx(25.0)  # Extrapolate

    def test_many_points_regression(self):
        """Test with many points to verify regression."""
        # Create points along y = 0.5x + 10
        import pandas as pd

        dates = pd.date_range("2020-01-01", periods=10, freq="5D")
        swings = [
            SwingPoint(date=d.date(), price=10.0 + 0.5 * (i * 5), bar_index=i * 5)
            for i, d in enumerate(dates)
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.r_squared == pytest.approx(1.0)
        assert result.slope == pytest.approx(0.5)
        assert result.intercept == pytest.approx(10.0)

    def test_r_squared_range(self):
        """R² should always be between 0 and 1."""
        # Create some scattered points
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 5), price=25.0, bar_index=5),
            SwingPoint(date=date(2020, 1, 10), price=12.0, bar_index=10),
            SwingPoint(date=date(2020, 1, 15), price=30.0, bar_index=15),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert 0.0 <= result.r_squared <= 1.0

    def test_very_steep_slope(self):
        """Handle very steep slopes (large price increases)."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=1.0, bar_index=0),
            SwingPoint(date=date(2020, 1, 2), price=100.0, bar_index=1),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.slope == pytest.approx(99.0)

    def test_very_gradual_slope(self):
        """Handle very gradual slopes (small price changes)."""
        swings = [
            SwingPoint(date=date(2020, 1, 1), price=10.0, bar_index=0),
            SwingPoint(date=date(2020, 4, 10), price=10.1, bar_index=100),
        ]
        result = fit_trendline(swings)

        assert result is not None
        assert result.slope == pytest.approx(0.001)
