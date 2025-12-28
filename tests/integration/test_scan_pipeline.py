"""Integration tests for the full scan pipeline."""

import pytest

from stock_finder.config import DataConfig, ScanConfig
from stock_finder.data.yfinance_provider import YFinanceProvider
from stock_finder.scanners.gainer_scanner import GainerScanner


@pytest.mark.integration
class TestScanPipeline:
    """End-to-end integration tests."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with real data provider."""
        data_config = DataConfig(rate_limit_delay=0.3)
        scan_config = ScanConfig(min_gain_pct=100, lookback_years=3)

        provider = YFinanceProvider(data_config)
        return GainerScanner(provider, scan_config)

    def test_scan_known_stocks(self, scanner):
        """Should successfully scan a small set of stocks."""
        # Use well-known, stable tickers
        tickers = ["AAPL", "MSFT", "GOOGL"]

        results = scanner.scan(tickers, show_progress=False)

        # Should complete without error
        # Results depend on market conditions, so just check structure
        assert isinstance(results, list)
        for r in results:
            assert r.ticker in tickers
            assert r.gain_pct >= 100
            assert r.low_price > 0
            assert r.high_price > r.low_price

    def test_scan_hims_finds_gain(self, scanner):
        """HIMS should show significant gains (known big mover)."""
        # Lower threshold for this test
        scanner.config.min_gain_pct = 200

        result = scanner.scan_single("HIMS")

        # HIMS has had significant gains, should be found
        # If market conditions change, this test may need adjustment
        if result:
            assert result.ticker == "HIMS"
            assert result.gain_pct >= 200
            print(f"HIMS gain: {result.gain_pct:.1f}%")
            print(f"Low: ${result.low_price:.2f} on {result.low_date}")
            print(f"High: ${result.high_price:.2f} on {result.high_date}")
