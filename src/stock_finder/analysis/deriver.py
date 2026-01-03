"""Criteria derivation from statistical analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import structlog

from stock_finder.data.database import DEFAULT_DB_PATH, Database

logger = structlog.get_logger()


@dataclass
class DerivedThreshold:
    """A single derived threshold for a variable."""

    variable_name: str
    operator: str
    threshold_value: float
    capture_rate: float  # % of winners captured
    exclusion_rate: float  # % of non-winners excluded


@dataclass
class DerivedCriteria:
    """Complete derived criteria set."""

    criteria_set_id: str
    name: str
    source_analysis_id: str
    regime_tag: str | None
    target_capture_rate: float
    actual_capture_rate: float
    thresholds: list[DerivedThreshold] = field(default_factory=list)


# Variable configurations: which direction indicates "more like a winner"
VARIABLE_CONFIG = {
    "drawdown": {"operator": "<=", "direction": "lower"},  # More negative = deeper drawdown
    "days_since_high": {"operator": ">=", "direction": "higher"},  # Longer decline
    "vol_ratio": {"operator": "<=", "direction": "lower"},  # Lower volume at bottom
    "range_position": {"operator": "<=", "direction": "lower"},  # Near bottom of range
    "pct_from_sma50": {"operator": "<=", "direction": "lower"},  # Below SMA
    "pct_from_sma200": {"operator": "<=", "direction": "lower"},  # Below SMA
}


class CriteriaDeriver:
    """
    Derives optimal criteria thresholds from statistical analysis.

    Given an analysis run and a target capture rate, computes the threshold
    for each variable that captures approximately that % of winners.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db = Database(db_path)

    def derive(
        self,
        source_analysis_id: str,
        target_capture_rate: float = 0.70,
        regime_tag: str | None = None,
        variables: list[str] | None = None,
        name: str | None = None,
        notes: str | None = None,
        save: bool = True,
    ) -> DerivedCriteria:
        """
        Derive criteria thresholds from an analysis run.

        Args:
            source_analysis_id: The analysis run to derive from
            target_capture_rate: Target % of winners to capture (0-1)
            regime_tag: Market regime tag (e.g., 'post_covid')
            variables: Variables to derive thresholds for (default: all configured)
            name: Name for the criteria set
            notes: Optional notes
            save: Whether to save to database

        Returns:
            DerivedCriteria with computed thresholds
        """
        variables = variables or list(VARIABLE_CONFIG.keys())

        # Verify analysis exists
        analysis = self.db.get_analysis_run(source_analysis_id)
        if not analysis:
            raise ValueError(f"Analysis run not found: {source_analysis_id}")

        logger.info(
            "Deriving criteria",
            source=source_analysis_id,
            target_capture_rate=target_capture_rate,
            variables=variables,
        )

        # Get the raw data for this analysis period
        start_date = analysis["start_date"]
        end_date = analysis["end_date"]
        min_gain = analysis["min_gain_pct"]

        winners_data, non_winners_data = self._get_population_data(
            start_date, end_date, min_gain
        )

        logger.info(
            "Data loaded",
            winners=len(winners_data),
            non_winners=len(non_winners_data),
        )

        # Derive threshold for each variable
        thresholds = []
        for var in variables:
            if var not in VARIABLE_CONFIG:
                logger.warning(f"Unknown variable: {var}, skipping")
                continue

            threshold = self._derive_threshold(
                var,
                winners_data,
                non_winners_data,
                target_capture_rate,
            )
            if threshold:
                thresholds.append(threshold)

        # Calculate combined capture rate (stocks meeting ALL criteria)
        actual_capture_rate = self._calculate_combined_capture_rate(
            thresholds, winners_data
        )

        # Generate ID and name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        criteria_set_id = f"criteria_{timestamp}"
        if regime_tag:
            criteria_set_id = f"{regime_tag}_{criteria_set_id}"

        if not name:
            name = f"Derived from {source_analysis_id} @ {target_capture_rate:.0%}"

        result = DerivedCriteria(
            criteria_set_id=criteria_set_id,
            name=name,
            source_analysis_id=source_analysis_id,
            regime_tag=regime_tag,
            target_capture_rate=target_capture_rate,
            actual_capture_rate=actual_capture_rate,
            thresholds=thresholds,
        )

        if save:
            self._save_criteria(result, notes)

        logger.info(
            "Criteria derived",
            criteria_set_id=criteria_set_id,
            thresholds=len(thresholds),
            actual_capture_rate=f"{actual_capture_rate:.1%}",
        )

        return result

    def _get_population_data(
        self,
        start_date: str,
        end_date: str,
        min_gain: float,
    ) -> tuple[list[dict], list[dict]]:
        """Get winners and non-winners data for the analysis period."""
        with self.db._get_connection() as conn:
            # Winners
            winners = conn.execute(
                """
                SELECT ns.*
                FROM neumann_scores ns
                JOIN scan_results sr ON ns.scan_result_id = sr.id
                WHERE sr.low_date >= ? AND sr.low_date <= ?
                AND ns.gain_pct >= ?
                """,
                (start_date, end_date, min_gain),
            ).fetchall()

            # Non-winners (below threshold)
            non_winners = conn.execute(
                """
                SELECT ns.*
                FROM neumann_scores ns
                JOIN scan_results sr ON ns.scan_result_id = sr.id
                WHERE sr.low_date >= ? AND sr.low_date <= ?
                AND ns.gain_pct < ?
                """,
                (start_date, end_date, min_gain),
            ).fetchall()

            return [dict(r) for r in winners], [dict(r) for r in non_winners]

    def _derive_threshold(
        self,
        variable: str,
        winners: list[dict],
        non_winners: list[dict],
        target_capture_rate: float,
    ) -> DerivedThreshold | None:
        """Derive optimal threshold for a single variable."""
        config = VARIABLE_CONFIG[variable]
        operator = config["operator"]
        direction = config["direction"]

        # Get values for this variable
        winner_values = [w[variable] for w in winners if w.get(variable) is not None]
        non_winner_values = [n[variable] for n in non_winners if n.get(variable) is not None]

        if not winner_values:
            logger.warning(f"No winner data for {variable}")
            return None

        # Sort values
        sorted_winners = sorted(winner_values)

        # Find threshold that captures target % of winners
        if direction == "lower":
            # For "lower is better", find the value at the target percentile
            # e.g., 70% capture rate means 70th percentile (30% are below)
            idx = int(len(sorted_winners) * target_capture_rate)
            idx = min(idx, len(sorted_winners) - 1)
            threshold_value = sorted_winners[idx]
        else:
            # For "higher is better", find value where target % are above
            idx = int(len(sorted_winners) * (1 - target_capture_rate))
            idx = max(idx, 0)
            threshold_value = sorted_winners[idx]

        # Calculate actual capture rate
        if direction == "lower":
            captured_winners = sum(1 for v in winner_values if v <= threshold_value)
            excluded_non_winners = sum(1 for v in non_winner_values if v > threshold_value)
        else:
            captured_winners = sum(1 for v in winner_values if v >= threshold_value)
            excluded_non_winners = sum(1 for v in non_winner_values if v < threshold_value)

        capture_rate = captured_winners / len(winner_values) if winner_values else 0
        exclusion_rate = excluded_non_winners / len(non_winner_values) if non_winner_values else 0

        return DerivedThreshold(
            variable_name=variable,
            operator=operator,
            threshold_value=round(threshold_value, 4),
            capture_rate=round(capture_rate, 4),
            exclusion_rate=round(exclusion_rate, 4),
        )

    def _calculate_combined_capture_rate(
        self,
        thresholds: list[DerivedThreshold],
        winners: list[dict],
    ) -> float:
        """Calculate % of winners that meet ALL criteria."""
        if not thresholds or not winners:
            return 0.0

        def meets_all(stock: dict) -> bool:
            for t in thresholds:
                value = stock.get(t.variable_name)
                if value is None:
                    return False
                if t.operator == "<=" and value > t.threshold_value:
                    return False
                if t.operator == ">=" and value < t.threshold_value:
                    return False
            return True

        matching = sum(1 for w in winners if meets_all(w))
        return round(matching / len(winners), 4)

    def _save_criteria(self, criteria: DerivedCriteria, notes: str | None) -> None:
        """Save derived criteria to database."""
        # Create criteria set
        self.db.create_criteria_set(
            criteria_set_id=criteria.criteria_set_id,
            name=criteria.name,
            source_analysis_id=criteria.source_analysis_id,
            regime_tag=criteria.regime_tag,
            target_capture_rate=criteria.target_capture_rate,
            actual_capture_rate=criteria.actual_capture_rate,
            is_active=False,
            notes=notes,
        )

        # Add thresholds
        threshold_dicts = [
            {
                "criteria_set_id": criteria.criteria_set_id,
                "variable_name": t.variable_name,
                "operator": t.operator,
                "threshold_value": t.threshold_value,
                "capture_rate": t.capture_rate,
                "exclusion_rate": t.exclusion_rate,
            }
            for t in criteria.thresholds
        ]
        self.db.add_criteria_thresholds_bulk(threshold_dicts)

    def list_criteria_sets(
        self,
        regime_tag: str | None = None,
        active_only: bool = False,
    ) -> list[dict]:
        """List all criteria sets."""
        return self.db.get_criteria_sets(regime_tag=regime_tag, active_only=active_only)

    def get_criteria_set(self, criteria_set_id: str) -> dict | None:
        """Get a criteria set with its thresholds."""
        return self.db.get_criteria_set(criteria_set_id)

    def activate(self, criteria_set_id: str) -> bool:
        """Activate a criteria set."""
        return self.db.activate_criteria_set(criteria_set_id)

    def delete(self, criteria_set_id: str) -> bool:
        """Delete a criteria set."""
        return self.db.delete_criteria_set(criteria_set_id) > 0
