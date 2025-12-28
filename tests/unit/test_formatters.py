"""Unit tests for output formatters."""

import json
from datetime import date

import pytest

from stock_finder.models.results import ScanResult
from stock_finder.output.formatters import format_as_csv, format_as_json, format_as_table


@pytest.fixture
def sample_results() -> list[ScanResult]:
    """Create sample results for testing."""
    return [
        ScanResult(
            ticker="AAAA",
            gain_pct=600.0,
            low_date=date(2022, 1, 15),
            high_date=date(2022, 6, 15),
            low_price=10.0,
            high_price=70.0,
            current_price=65.0,
            days_to_peak=100,
        ),
        ScanResult(
            ticker="BBBB",
            gain_pct=500.5,
            low_date=date(2022, 3, 1),
            high_date=date(2022, 9, 1),
            low_price=5.0,
            high_price=30.03,
            current_price=28.0,
            days_to_peak=150,
        ),
    ]


class TestFormatAsCsv:
    """Tests for CSV formatting."""

    def test_includes_header(self, sample_results):
        """CSV should include header row."""
        csv = format_as_csv(sample_results)

        lines = csv.strip().split("\n")
        header = lines[0]

        assert "ticker" in header
        assert "gain_pct" in header
        assert "low_date" in header

    def test_includes_all_results(self, sample_results):
        """CSV should include all results."""
        csv = format_as_csv(sample_results)

        lines = csv.strip().split("\n")
        # Header + 2 data rows
        assert len(lines) == 3

    def test_correct_values(self, sample_results):
        """CSV should have correct values."""
        csv = format_as_csv(sample_results)

        assert "AAAA" in csv
        assert "BBBB" in csv
        assert "600.0" in csv
        assert "2022-01-15" in csv

    def test_empty_results(self):
        """Should handle empty results."""
        csv = format_as_csv([])

        lines = csv.strip().split("\n")
        assert len(lines) == 1  # Just header


class TestFormatAsJson:
    """Tests for JSON formatting."""

    def test_valid_json(self, sample_results):
        """Output should be valid JSON."""
        output = format_as_json(sample_results)

        # Should not raise
        data = json.loads(output)
        assert isinstance(data, list)

    def test_includes_all_fields(self, sample_results):
        """JSON should include all fields."""
        output = format_as_json(sample_results)
        data = json.loads(output)

        first = data[0]
        assert "ticker" in first
        assert "gain_pct" in first
        assert "low_date" in first
        assert "high_date" in first
        assert "low_price" in first
        assert "high_price" in first
        assert "current_price" in first
        assert "days_to_peak" in first

    def test_correct_values(self, sample_results):
        """JSON should have correct values."""
        output = format_as_json(sample_results)
        data = json.loads(output)

        first = data[0]
        assert first["ticker"] == "AAAA"
        assert first["gain_pct"] == 600.0
        assert first["low_date"] == "2022-01-15"

    def test_empty_results(self):
        """Should handle empty results."""
        output = format_as_json([])

        data = json.loads(output)
        assert data == []


class TestFormatAsTable:
    """Tests for table formatting."""

    def test_includes_ticker(self, sample_results):
        """Table should include ticker symbols."""
        table = format_as_table(sample_results)

        assert "AAAA" in table
        assert "BBBB" in table

    def test_includes_gain(self, sample_results):
        """Table should include gain percentages."""
        table = format_as_table(sample_results)

        assert "600" in table
        assert "500" in table

    def test_empty_results(self):
        """Should handle empty results."""
        table = format_as_table([])

        assert "0 stocks" in table
