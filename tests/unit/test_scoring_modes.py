"""Unit tests for scoring modes."""

import pytest

from stock_finder.scoring.modes import (
    ScoringMode,
    CRITERIA_WEIGHTS,
    CORE_CRITERIA,
    MAX_SCORES,
    get_weight,
    get_max_score,
)


class TestScoringMode:
    """Tests for ScoringMode enum."""

    def test_enum_values(self):
        """Test that all expected modes exist."""
        assert ScoringMode.FULL.value == "full"
        assert ScoringMode.CORE.value == "core"
        assert ScoringMode.WEIGHTED.value == "weighted"

    def test_enum_from_string(self):
        """Test creating enum from string."""
        assert ScoringMode("full") == ScoringMode.FULL
        assert ScoringMode("core") == ScoringMode.CORE
        assert ScoringMode("weighted") == ScoringMode.WEIGHTED


class TestCriteriaWeights:
    """Tests for criteria weights configuration."""

    def test_all_criteria_have_weights(self):
        """Test that all expected criteria have weights defined."""
        expected_criteria = {
            "drawdown",
            "extended_decline",
            "near_lows",
            "volume_exhaustion",
            "below_sma50",
            "below_sma200",
            "market_cap",
            "trendline_break",
        }
        assert set(CRITERIA_WEIGHTS.keys()) == expected_criteria

    def test_drawdown_has_highest_weight(self):
        """Test that drawdown has the highest weight (best predictor)."""
        assert CRITERIA_WEIGHTS["drawdown"] == max(CRITERIA_WEIGHTS.values())
        assert CRITERIA_WEIGHTS["drawdown"] == 3

    def test_extended_decline_has_second_highest_weight(self):
        """Test that extended_decline has second highest weight."""
        assert CRITERIA_WEIGHTS["extended_decline"] == 2

    def test_below_sma200_has_zero_weight(self):
        """Test that below_sma200 has zero weight (nearly useless predictor)."""
        assert CRITERIA_WEIGHTS["below_sma200"] == 0

    def test_core_criteria_are_top_predictors(self):
        """Test that core criteria are the top predictors."""
        assert CORE_CRITERIA == {"drawdown", "extended_decline"}


class TestMaxScores:
    """Tests for max scores by mode."""

    def test_full_mode_max_score(self):
        """Test max score for full mode is 8 (all criteria)."""
        assert MAX_SCORES[ScoringMode.FULL] == 8

    def test_core_mode_max_score(self):
        """Test max score for core mode is 2 (only top 2 criteria)."""
        assert MAX_SCORES[ScoringMode.CORE] == 2

    def test_weighted_mode_max_score(self):
        """Test max score for weighted mode is sum of weights."""
        expected = sum(CRITERIA_WEIGHTS.values())
        assert MAX_SCORES[ScoringMode.WEIGHTED] == expected
        assert MAX_SCORES[ScoringMode.WEIGHTED] == 10


class TestGetWeight:
    """Tests for get_weight function."""

    def test_full_mode_all_criteria_equal(self):
        """Test that all criteria have weight 1 in full mode."""
        for criterion in CRITERIA_WEIGHTS.keys():
            assert get_weight(criterion, ScoringMode.FULL) == 1

    def test_core_mode_only_core_criteria(self):
        """Test that only core criteria have weight in core mode."""
        assert get_weight("drawdown", ScoringMode.CORE) == 1
        assert get_weight("extended_decline", ScoringMode.CORE) == 1
        assert get_weight("near_lows", ScoringMode.CORE) == 0
        assert get_weight("below_sma50", ScoringMode.CORE) == 0
        assert get_weight("below_sma200", ScoringMode.CORE) == 0
        assert get_weight("volume_exhaustion", ScoringMode.CORE) == 0
        assert get_weight("market_cap", ScoringMode.CORE) == 0
        assert get_weight("trendline_break", ScoringMode.CORE) == 0

    def test_weighted_mode_uses_weights(self):
        """Test that weighted mode uses the defined weights."""
        assert get_weight("drawdown", ScoringMode.WEIGHTED) == 3
        assert get_weight("extended_decline", ScoringMode.WEIGHTED) == 2
        assert get_weight("near_lows", ScoringMode.WEIGHTED) == 1
        assert get_weight("below_sma200", ScoringMode.WEIGHTED) == 0

    def test_unknown_criterion_defaults_to_one(self):
        """Test that unknown criteria default to weight 1."""
        assert get_weight("unknown_criterion", ScoringMode.FULL) == 1
        assert get_weight("unknown_criterion", ScoringMode.WEIGHTED) == 1


class TestGetMaxScore:
    """Tests for get_max_score function."""

    def test_full_mode(self):
        """Test get_max_score for full mode."""
        assert get_max_score(ScoringMode.FULL) == 8

    def test_core_mode(self):
        """Test get_max_score for core mode."""
        assert get_max_score(ScoringMode.CORE) == 2

    def test_weighted_mode(self):
        """Test get_max_score for weighted mode."""
        assert get_max_score(ScoringMode.WEIGHTED) == 10


class TestScoringModeIntegration:
    """Integration tests for scoring with different modes."""

    def test_weighted_score_higher_than_full_for_top_criteria(self):
        """
        Test that weighted scoring gives higher scores when top criteria pass.

        If drawdown and extended_decline pass:
        - Full mode: 2 points (1+1)
        - Weighted mode: 5 points (3+2)
        """
        # Simulate a stock that passes only drawdown and extended_decline
        full_score = get_weight("drawdown", ScoringMode.FULL) + \
                     get_weight("extended_decline", ScoringMode.FULL)
        weighted_score = get_weight("drawdown", ScoringMode.WEIGHTED) + \
                         get_weight("extended_decline", ScoringMode.WEIGHTED)

        assert full_score == 2
        assert weighted_score == 5
        assert weighted_score > full_score

    def test_below_sma200_contributes_nothing_in_weighted(self):
        """Test that below_sma200 adds no points in weighted mode."""
        full_score = get_weight("below_sma200", ScoringMode.FULL)
        weighted_score = get_weight("below_sma200", ScoringMode.WEIGHTED)

        assert full_score == 1  # Still counts in full mode
        assert weighted_score == 0  # Zero in weighted mode
