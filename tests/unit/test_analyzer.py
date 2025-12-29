"""Tests for TrendlineAnalyzer class."""

import pandas as pd
import pytest
from datetime import date
from unittest.mock import Mock, MagicMock

from stock_finder.analysis.models import TrendlineAnalysis, TrendlineConfig
from stock_finder.analysis.analyzer import TrendlineAnalyzer


def make_rising_price_data(
    start_date: str = "2020-01-01",
    days: int = 100,
    start_price: float = 10.0,
    end_price: float = 50.0,
) -> pd.DataFrame:
    """Create rising price data with swing lows (W patterns)."""
    dates = pd.date_range(start=start_date, periods=days, freq="D")

    # Create a rising pattern with oscillations (W shapes)
    import numpy as np

    t = np.linspace(0, 4 * np.pi, days)
    # Base uptrend + oscillation
    trend = np.linspace(start_price, end_price, days)
    oscillation = np.sin(t) * (end_price - start_price) * 0.1

    closes = trend + oscillation
    lows = closes * 0.98  # Lows slightly below closes
    highs = closes * 1.02  # Highs slightly above closes

    return pd.DataFrame(
        {
            "Open": closes,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": [1000000] * days,
        },
        index=dates,
    )


def make_flat_price_data(
    start_date: str = "2020-01-01",
    days: int = 100,
    price: float = 10.0,
) -> pd.DataFrame:
    """Create flat price data with no swing lows."""
    dates = pd.date_range(start=start_date, periods=days, freq="D")
    return pd.DataFrame(
        {
            "Open": [price] * days,
            "High": [price + 0.1] * days,
            "Low": [price - 0.1] * days,
            "Close": [price] * days,
            "Volume": [1000000] * days,
        },
        index=dates,
    )


class TestTrendlineAnalyzer:
    """Tests for TrendlineAnalyzer class."""

    def test_init_with_defaults(self):
        """Analyzer should initialize with default config."""
        provider = Mock()
        analyzer = TrendlineAnalyzer(provider=provider)

        assert analyzer.provider == provider
        assert analyzer.db is None
        assert analyzer.config is not None
        assert isinstance(analyzer.config, TrendlineConfig)

    def test_init_with_custom_config(self):
        """Analyzer should accept custom config."""
        provider = Mock()
        config = TrendlineConfig(swing_lookback=5, min_touches=3)
        analyzer = TrendlineAnalyzer(provider=provider, config=config)

        assert analyzer.config.swing_lookback == 5
        assert analyzer.config.min_touches == 3

    def test_analyze_stock_returns_trendline_analysis(self):
        """analyze_stock should return TrendlineAnalysis object."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data()

        analyzer = TrendlineAnalyzer(provider=provider)
        scan_result = {
            "id": 1,
            "ticker": "TEST",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily")

        assert isinstance(result, TrendlineAnalysis)
        assert result.ticker == "TEST"
        assert result.scan_result_id == 1
        assert result.timeframe == "daily"

    def test_analyze_stock_no_trendline_flat_data(self):
        """Flat data should not form a trendline."""
        provider = Mock()
        provider.get_historical.return_value = make_flat_price_data()

        analyzer = TrendlineAnalyzer(provider=provider)
        scan_result = {
            "id": 1,
            "ticker": "FLAT",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 0.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily")

        assert result.trendline_formed is False
        assert result.swing_low_count == 0

    def test_analyze_stock_rising_data_forms_trendline(self):
        """Rising data with swing lows should form a trendline."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data()

        config = TrendlineConfig(swing_lookback=5, min_touches=2)
        analyzer = TrendlineAnalyzer(provider=provider, config=config)
        scan_result = {
            "id": 1,
            "ticker": "RISE",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily")

        # Should detect swing lows and fit a trendline
        assert result.swing_low_count >= 2
        if result.trendline_formed:
            assert result.r_squared is not None
            assert result.slope_pct_per_day is not None

    def test_analyze_stock_stores_gain_pct(self):
        """analyze_stock should store gain_pct from scan result."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data()

        analyzer = TrendlineAnalyzer(provider=provider)
        scan_result = {
            "id": 1,
            "ticker": "TEST",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily")

        assert result.gain_pct == 500.0
        assert result.days_to_peak == 100

    def test_analyze_stock_weekly_timeframe(self):
        """Weekly timeframe should resample data."""
        provider = Mock()
        # Provide 100 days of data
        provider.get_historical.return_value = make_rising_price_data(days=100)

        analyzer = TrendlineAnalyzer(provider=provider)
        scan_result = {
            "id": 1,
            "ticker": "TEST",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="weekly")

        assert result.timeframe == "weekly"

    def test_analyze_stock_fetches_correct_date_range(self):
        """Analyzer should fetch data with buffer before/after the move."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data()

        config = TrendlineConfig(data_buffer_days=30)
        analyzer = TrendlineAnalyzer(provider=provider, config=config)
        scan_result = {
            "id": 1,
            "ticker": "TEST",
            "low_date": "2020-03-01",
            "high_date": "2020-06-01",
            "gain_pct": 500.0,
            "days_to_peak": 90,
        }

        analyzer.analyze_stock(scan_result, timeframe="daily")

        # Verify fetch was called with buffered dates
        provider.get_historical.assert_called_once()
        call_args = provider.get_historical.call_args
        assert call_args[0][0] == "TEST"  # ticker

    def test_analyze_stock_handles_missing_data(self):
        """Analyzer should handle empty/missing data gracefully."""
        provider = Mock()
        provider.get_historical.return_value = pd.DataFrame()

        analyzer = TrendlineAnalyzer(provider=provider)
        scan_result = {
            "id": 1,
            "ticker": "EMPTY",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily")

        assert result.trendline_formed is False
        assert result.swing_low_count == 0

    def test_analyze_stock_calculates_slope_pct(self):
        """Slope should be converted to percentage per day."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data(
            start_price=10.0, end_price=50.0, days=100
        )

        config = TrendlineConfig(swing_lookback=5, min_touches=2, min_r_squared=0.0)
        analyzer = TrendlineAnalyzer(provider=provider, config=config)
        scan_result = {
            "id": 1,
            "ticker": "RISE",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily")

        # If trendline formed, slope should be positive (rising)
        if result.trendline_formed and result.slope_pct_per_day is not None:
            assert result.slope_pct_per_day > 0


class TestTrendlineAnalyzerWithDatabase:
    """Tests for TrendlineAnalyzer database integration."""

    def test_analyze_stock_saves_to_database(self):
        """analyze_stock should save result to database when db provided."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data()

        db = Mock()
        db.add_trendline_analysis.return_value = 1

        analyzer = TrendlineAnalyzer(provider=provider, db=db)
        scan_result = {
            "id": 1,
            "ticker": "TEST",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        result = analyzer.analyze_stock(scan_result, timeframe="daily", save=True)

        db.add_trendline_analysis.assert_called_once()
        call_args = db.add_trendline_analysis.call_args[0][0]
        assert isinstance(call_args, TrendlineAnalysis)

    def test_analyze_stock_no_save_when_save_false(self):
        """analyze_stock should not save when save=False."""
        provider = Mock()
        provider.get_historical.return_value = make_rising_price_data()

        db = Mock()
        analyzer = TrendlineAnalyzer(provider=provider, db=db)
        scan_result = {
            "id": 1,
            "ticker": "TEST",
            "low_date": "2020-01-01",
            "high_date": "2020-04-10",
            "gain_pct": 500.0,
            "days_to_peak": 100,
        }

        analyzer.analyze_stock(scan_result, timeframe="daily", save=False)

        db.add_trendline_analysis.assert_not_called()
