"""Unit tests for the gainer scanner."""

import pytest

from stock_finder.scanners.gainer_scanner import GainerScanner


class TestGainerScanner:
    """Tests for GainerScanner."""

    def test_scan_single_finds_gainer(self, mock_provider, scan_config):
        """Should find a stock that meets the gain threshold."""
        scanner = GainerScanner(mock_provider, scan_config)

        result = scanner.scan_single("GAINER")

        assert result is not None
        assert result.ticker == "GAINER"
        assert result.gain_pct >= 500

    def test_scan_single_rejects_loser(self, mock_provider, scan_config):
        """Should not return a stock that doesn't meet threshold."""
        scanner = GainerScanner(mock_provider, scan_config)

        result = scanner.scan_single("LOSER")

        assert result is None

    def test_scan_single_rejects_flat(self, mock_provider, scan_config):
        """Should not return a flat stock."""
        scanner = GainerScanner(mock_provider, scan_config)

        result = scanner.scan_single("FLAT")

        assert result is None

    def test_scan_single_handles_unknown_ticker(self, mock_provider, scan_config):
        """Should return None for unknown ticker."""
        scanner = GainerScanner(mock_provider, scan_config)

        result = scanner.scan_single("UNKNOWN")

        assert result is None

    def test_scan_multiple_tickers(self, mock_provider, scan_config):
        """Should scan multiple tickers and return only gainers."""
        scanner = GainerScanner(mock_provider, scan_config)

        results = scanner.scan(["GAINER", "LOSER", "FLAT", "UNKNOWN"], show_progress=False)

        assert len(results) == 1
        assert results[0].ticker == "GAINER"

    def test_scan_returns_sorted_by_gain(self, mock_provider, scan_config):
        """Results should be sorted by gain percentage descending."""
        # Add another gainer with lower gain (450% gain: 10 to 55)
        import pandas as pd

        dates = pd.date_range("2023-01-01", periods=500, freq="D")
        small_gainer_prices = [10] * 100 + list(range(10, 55)) + [55] * 355
        mock_provider.data["SMALL_GAINER"] = pd.DataFrame(
            {
                "Open": small_gainer_prices,
                "High": small_gainer_prices,
                "Low": small_gainer_prices,
                "Close": small_gainer_prices,
                "Volume": [100000] * 500,
            },
            index=dates,
        )

        # Lower threshold to catch both
        scan_config.min_gain_pct = 400

        scanner = GainerScanner(mock_provider, scan_config)
        results = scanner.scan(["GAINER", "SMALL_GAINER"], show_progress=False)

        assert len(results) == 2
        assert results[0].gain_pct >= results[1].gain_pct

    def test_scan_empty_list(self, mock_provider, scan_config):
        """Should handle empty ticker list."""
        scanner = GainerScanner(mock_provider, scan_config)

        results = scanner.scan([], show_progress=False)

        assert results == []
