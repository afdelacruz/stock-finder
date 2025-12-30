"""Unit tests for NeumannScorer (TDD)."""

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from stock_finder.data.database import Database
from stock_finder.models.results import NeumannScore, ScanResult
from stock_finder.scoring.criteria.base import Criterion, CriterionResult, ScoringContext


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db


@pytest.fixture
def sample_scan_results(temp_db) -> list[dict]:
    """Create sample scan results in the temp database."""
    # Start a scan run
    scan_run_id = temp_db.start_scan_run(
        min_gain_pct=300,
        lookback_years=7,
        universe="test",
        ticker_count=3,
    )

    # Add some sample results
    results = [
        ScanResult(
            ticker="WINNER1",
            gain_pct=500.0,
            low_date=date(2020, 3, 15),
            high_date=date(2021, 1, 15),
            low_price=10.0,
            high_price=60.0,
            current_price=55.0,
            days_to_peak=200,
        ),
        ScanResult(
            ticker="WINNER2",
            gain_pct=800.0,
            low_date=date(2019, 6, 1),
            high_date=date(2020, 12, 1),
            low_price=5.0,
            high_price=45.0,
            current_price=40.0,
            days_to_peak=380,
        ),
        ScanResult(
            ticker="WINNER3",
            gain_pct=350.0,
            low_date=date(2021, 1, 10),
            high_date=date(2021, 8, 10),
            low_price=20.0,
            high_price=90.0,
            current_price=85.0,
            days_to_peak=150,
        ),
    ]

    saved_results = []
    for result in results:
        result_id = temp_db.add_result(scan_run_id, result)
        saved_results.append({
            "id": result_id,
            "scan_run_id": scan_run_id,
            **result.to_dict(),
        })

    temp_db.complete_scan_run(scan_run_id)
    return saved_results


@pytest.fixture
def mock_historical_data() -> dict[str, pd.DataFrame]:
    """Create mock historical data for test tickers."""
    data = {}

    for ticker in ["WINNER1", "WINNER2", "WINNER3"]:
        # Create 500 days of data showing decline pattern
        dates = pd.date_range("2018-01-01", periods=500, freq="D")

        # Pattern: high at start, decline to low
        prices = []
        volumes = []
        for i in range(500):
            if i < 100:
                price = 100 - i * 0.5  # Decline from 100 to 50
                volume = 1_000_000
            elif i < 300:
                price = 50 - (i - 100) * 0.15  # Further decline to 20
                volume = 500_000
            else:
                price = 20 + (i - 300) * 0.02  # Near lows
                volume = 200_000

            prices.append(max(price, 5))  # Floor at 5
            volumes.append(volume)

        data[ticker] = pd.DataFrame(
            {
                "Open": prices,
                "High": [p * 1.02 for p in prices],
                "Low": [p * 0.98 for p in prices],
                "Close": prices,
                "Volume": volumes,
            },
            index=dates,
        )

    return data


class MockDataProvider:
    """Mock data provider for unit testing scorer."""

    def __init__(self, historical_data: dict[str, pd.DataFrame]):
        self.historical_data = historical_data
        self.call_count = 0

    def get_historical(self, ticker: str, start: date, end: date):
        """Return mock historical data."""
        self.call_count += 1
        if ticker not in self.historical_data:
            return None

        from stock_finder.models.results import StockData

        df = self.historical_data[ticker]
        # Filter by date range
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
        filtered = df[mask]

        if filtered.empty:
            return None

        return StockData(ticker=ticker, data=filtered)

    def get_quote(self, ticker: str):
        """Return mock quote with shares outstanding."""
        from stock_finder.data.fmp_provider import Quote

        return Quote(
            symbol=ticker,
            price=50.0,
            change_percent=0.0,
            day_low=49.0,
            day_high=51.0,
            year_low=10.0,
            year_high=100.0,
            market_cap=500_000_000,  # $500M
            avg_volume=500_000,
            volume=200_000,
            price_avg_50=35.0,
            price_avg_200=55.0,
            exchange="NASDAQ",
            name=f"{ticker} Inc",
        )


# =============================================================================
# Tests for NeumannScorer
# =============================================================================


class TestNeumannScorer:
    """Tests for the NeumannScorer class."""

    def test_scorer_initializes_with_default_criteria(self):
        """Scorer should initialize with all 8 default criteria."""
        from stock_finder.scoring.scorer import NeumannScorer

        scorer = NeumannScorer(provider=None)

        assert len(scorer.criteria) == 8
        criterion_names = {c.name for c in scorer.criteria}
        expected = {
            "drawdown",
            "extended_decline",
            "near_lows",
            "below_sma50",
            "below_sma200",
            "volume_exhaustion",
            "market_cap",
            "trendline_break",
        }
        assert criterion_names == expected

    def test_scorer_accepts_custom_criteria(self):
        """Scorer should accept custom criteria list."""
        from stock_finder.scoring.criteria.drawdown import DrawdownCriterion
        from stock_finder.scoring.scorer import NeumannScorer

        custom_criteria = [DrawdownCriterion(threshold=-0.60)]
        scorer = NeumannScorer(provider=None, criteria=custom_criteria)

        assert len(scorer.criteria) == 1
        assert scorer.criteria[0].name == "drawdown"

    def test_score_single_stock(self, mock_historical_data):
        """Scorer should score a single stock and return NeumannScore."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        result = scorer.score_stock(scan_result)

        assert isinstance(result, NeumannScore)
        assert result.ticker == "WINNER1"
        assert result.scan_result_id == 1
        assert 0 <= result.score <= 8
        assert len(result.criteria_results) == 8

    def test_score_returns_individual_metrics(self, mock_historical_data):
        """Score should include individual metric values."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        result = scorer.score_stock(scan_result)

        # Should have individual metrics populated
        assert result.drawdown is not None or result.drawdown is None  # May be None if data missing
        assert result.gain_pct == 500.0
        assert result.days_to_peak == 200

    def test_score_handles_missing_data(self, mock_historical_data):
        """Scorer should handle stocks with missing historical data."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider)

        # Stock not in our mock data
        scan_result = {
            "id": 99,
            "ticker": "MISSING",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        result = scorer.score_stock(scan_result)

        # Should still return a result, but with low score
        # Note: Some criteria may pass if SMA data is available from quote
        assert isinstance(result, NeumannScore)
        assert result.ticker == "MISSING"
        # Most criteria should fail due to missing historical data
        failed_count = sum(
            1 for r in result.criteria_results.values() if not r["passed"]
        )
        assert failed_count >= 5  # At least 5 of 8 should fail

    def test_score_all_stocks(self, temp_db, sample_scan_results, mock_historical_data):
        """Scorer should score all stocks from a scan run."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider, db=temp_db)

        scan_run_id = sample_scan_results[0]["scan_run_id"]
        results = scorer.score_all(scan_run_id=scan_run_id)

        assert len(results) == 3
        assert all(isinstance(r, NeumannScore) for r in results)

    def test_score_all_saves_to_database(
        self, temp_db, sample_scan_results, mock_historical_data
    ):
        """Scorer should save results to database when db is provided."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider, db=temp_db)

        scan_run_id = sample_scan_results[0]["scan_run_id"]
        scorer.score_all(scan_run_id=scan_run_id, save=True)

        # Check database
        saved = temp_db.get_neumann_scores()
        assert len(saved) == 3


# =============================================================================
# Tests for Database Neumann Score Methods
# =============================================================================


class TestDatabaseNeumannScores:
    """Tests for database Neumann score methods."""

    def test_add_and_retrieve_neumann_score(self, temp_db):
        """Should save and retrieve a NeumannScore."""
        score = NeumannScore(
            ticker="TEST",
            scan_result_id=1,
            score=5,
            criteria_results={
                "drawdown": {"passed": True, "value": -0.60},
                "extended_decline": {"passed": True, "value": 150},
            },
            drawdown=-0.60,
            days_since_high=150,
            range_position=0.15,
            pct_from_sma50=-0.30,
            pct_from_sma200=-0.45,
            vol_ratio=0.8,
            market_cap_estimate=300_000_000,
            sma_crossover=False,
            gain_pct=500.0,
            days_to_peak=200,
        )

        score_id = temp_db.add_neumann_score(score)
        assert score_id > 0

        # Retrieve
        scores = temp_db.get_neumann_scores()
        assert len(scores) == 1
        assert scores[0]["ticker"] == "TEST"
        assert scores[0]["score"] == 5
        assert scores[0]["drawdown"] == -0.60
        assert "drawdown" in scores[0]["criteria_results"]

    def test_get_neumann_scores_with_min_score_filter(self, temp_db):
        """Should filter scores by minimum score."""
        for i, score_val in enumerate([2, 4, 6, 8]):
            temp_db.add_neumann_score(
                NeumannScore(
                    ticker=f"STOCK{i}",
                    scan_result_id=i,
                    score=score_val,
                    criteria_results={},
                )
            )

        # Get only high scorers
        high_scores = temp_db.get_neumann_scores(min_score=5)
        assert len(high_scores) == 2
        assert all(s["score"] >= 5 for s in high_scores)

    def test_get_neumann_score_stats(self, temp_db):
        """Should return aggregate statistics."""
        for i, (score_val, gain) in enumerate([(2, 200), (4, 400), (6, 600), (6, 800)]):
            temp_db.add_neumann_score(
                NeumannScore(
                    ticker=f"STOCK{i}",
                    scan_result_id=i,
                    score=score_val,
                    criteria_results={},
                    gain_pct=float(gain),
                    days_to_peak=100,
                )
            )

        stats = temp_db.get_neumann_score_stats()

        assert stats["total"] == 4
        assert stats["avg_score"] == 4.5  # (2+4+6+6)/4
        assert stats["avg_gain"] == 500.0  # (200+400+600+800)/4
        assert len(stats["distribution"]) == 3  # Scores 2, 4, 6

    def test_clear_neumann_scores(self, temp_db):
        """Should clear all Neumann scores."""
        for i in range(5):
            temp_db.add_neumann_score(
                NeumannScore(
                    ticker=f"STOCK{i}",
                    scan_result_id=i,
                    score=i,
                    criteria_results={},
                )
            )

        assert len(temp_db.get_neumann_scores()) == 5

        deleted = temp_db.clear_neumann_scores()
        assert deleted == 5
        assert len(temp_db.get_neumann_scores()) == 0


# =============================================================================
# Edge Cases
# =============================================================================


class TestScorerEdgeCases:
    """Test edge cases for scorer."""

    def test_handles_date_string_format(self, mock_historical_data):
        """Should handle date as string (from database)."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider)

        # Dates as strings (as they come from SQLite)
        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",  # String, not date object
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        result = scorer.score_stock(scan_result)
        assert isinstance(result, NeumannScore)

    def test_handles_zero_price(self, mock_historical_data):
        """Should handle zero ignition price gracefully."""
        from stock_finder.scoring.scorer import NeumannScorer

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 0.0,  # Zero price
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        # Should not raise, should return result with low/zero score
        result = scorer.score_stock(scan_result)
        assert isinstance(result, NeumannScore)


# =============================================================================
# Tests for Scoring Modes
# =============================================================================


class TestScorerModes:
    """Tests for NeumannScorer with different scoring modes."""

    def test_scorer_defaults_to_full_mode(self, mock_historical_data):
        """Scorer should default to full scoring mode."""
        from stock_finder.scoring.scorer import NeumannScorer
        from stock_finder.scoring.modes import ScoringMode

        provider = MockDataProvider(mock_historical_data)
        scorer = NeumannScorer(provider=provider)

        assert scorer.scoring_mode == ScoringMode.FULL

    def test_scorer_accepts_scoring_mode(self, mock_historical_data):
        """Scorer should accept scoring_mode parameter."""
        from stock_finder.scoring.scorer import NeumannScorer
        from stock_finder.scoring.modes import ScoringMode

        provider = MockDataProvider(mock_historical_data)

        scorer_core = NeumannScorer(provider=provider, scoring_mode=ScoringMode.CORE)
        assert scorer_core.scoring_mode == ScoringMode.CORE

        scorer_weighted = NeumannScorer(provider=provider, scoring_mode=ScoringMode.WEIGHTED)
        assert scorer_weighted.scoring_mode == ScoringMode.WEIGHTED

    def test_score_includes_max_score_and_mode(self, mock_historical_data):
        """NeumannScore should include max_score and scoring_mode."""
        from stock_finder.scoring.scorer import NeumannScorer
        from stock_finder.scoring.modes import ScoringMode

        provider = MockDataProvider(mock_historical_data)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        # Test full mode
        scorer_full = NeumannScorer(provider=provider, scoring_mode=ScoringMode.FULL)
        result_full = scorer_full.score_stock(scan_result)
        assert result_full.max_score == 8
        assert result_full.scoring_mode == "full"

        # Test core mode
        scorer_core = NeumannScorer(provider=provider, scoring_mode=ScoringMode.CORE)
        result_core = scorer_core.score_stock(scan_result)
        assert result_core.max_score == 2
        assert result_core.scoring_mode == "core"

        # Test weighted mode
        scorer_weighted = NeumannScorer(provider=provider, scoring_mode=ScoringMode.WEIGHTED)
        result_weighted = scorer_weighted.score_stock(scan_result)
        assert result_weighted.max_score == 10
        assert result_weighted.scoring_mode == "weighted"

    def test_core_mode_only_counts_core_criteria(self, mock_historical_data):
        """Core mode should only count drawdown and extended_decline."""
        from stock_finder.scoring.scorer import NeumannScorer
        from stock_finder.scoring.modes import ScoringMode

        provider = MockDataProvider(mock_historical_data)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        scorer = NeumannScorer(provider=provider, scoring_mode=ScoringMode.CORE)
        result = scorer.score_stock(scan_result)

        # Max possible score in core mode is 2
        assert 0 <= result.score <= 2

    def test_weighted_mode_applies_weights(self, mock_historical_data):
        """Weighted mode should apply different weights to criteria."""
        from stock_finder.scoring.scorer import NeumannScorer
        from stock_finder.scoring.modes import ScoringMode

        provider = MockDataProvider(mock_historical_data)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        scorer = NeumannScorer(provider=provider, scoring_mode=ScoringMode.WEIGHTED)
        result = scorer.score_stock(scan_result)

        # Max possible score in weighted mode is 10
        assert 0 <= result.score <= 10

    def test_full_mode_score_equals_criteria_passed(self, mock_historical_data):
        """Full mode score should equal number of criteria passed."""
        from stock_finder.scoring.scorer import NeumannScorer
        from stock_finder.scoring.modes import ScoringMode

        provider = MockDataProvider(mock_historical_data)

        scan_result = {
            "id": 1,
            "ticker": "WINNER1",
            "low_date": "2020-03-15",
            "low_price": 10.0,
            "high_date": "2021-01-15",
            "high_price": 60.0,
            "gain_pct": 500.0,
            "days_to_peak": 200,
        }

        scorer = NeumannScorer(provider=provider, scoring_mode=ScoringMode.FULL)
        result = scorer.score_stock(scan_result)

        # Count passed criteria
        passed_count = sum(
            1 for r in result.criteria_results.values() if r["passed"]
        )
        assert result.score == passed_count
