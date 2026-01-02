"""Statistical analysis framework for deriving data-driven criteria."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import structlog

from stock_finder.analysis.models import AnalysisConfig, AnalysisResult, VariableStats
from stock_finder.analysis.statistics import calculate_lift, calculate_stats
from stock_finder.data.database import DEFAULT_DB_PATH, Database

logger = structlog.get_logger()


class AnalysisFramework:
    """
    Framework for analyzing any time period to derive data-driven criteria.

    Calculates statistics for winners (stocks with large gains) vs all stocks,
    enabling data-driven derivation of criteria thresholds.
    """

    # Variables available for analysis from neumann_scores table
    AVAILABLE_VARIABLES = [
        "drawdown",
        "days_since_high",
        "vol_ratio",
        "range_position",
        "pct_from_sma50",
        "pct_from_sma200",
        "gain_pct",
        "days_to_peak",
    ]

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        """
        Initialize the analysis framework.

        Args:
            db_path: Path to the SQLite database
        """
        self.db = Database(db_path)

    def run(
        self,
        start_date: str,
        end_date: str,
        min_gain_pct: float = 300.0,
        universe: str = "all",
        variables: list[str] | None = None,
        notes: str | None = None,
    ) -> AnalysisResult:
        """
        Run statistical analysis on a time period.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_gain_pct: Minimum gain to qualify as a "winner"
            universe: Ticker universe ('all', 'nasdaq', 'nyse', or custom list)
            variables: Variables to analyze (defaults to all available)
            notes: Optional notes for the run

        Returns:
            AnalysisResult with statistics for winners and all stocks
        """
        variables = variables or self.AVAILABLE_VARIABLES
        config = AnalysisConfig(
            start_date=start_date,
            end_date=end_date,
            min_gain_pct=min_gain_pct,
            universe=universe,
            variables=variables,
        )

        # Generate unique run ID
        run_id = f"analysis_{start_date.replace('-', '')}_{end_date.replace('-', '')}_{datetime.now().strftime('%H%M%S')}"

        logger.info(
            "Starting analysis run",
            run_id=run_id,
            period=f"{start_date} to {end_date}",
            min_gain=min_gain_pct,
        )

        # Get data from database
        winners_data = self._get_winners_data(start_date, end_date, min_gain_pct)
        all_data = self._get_all_data(start_date, end_date)

        logger.info(
            "Data loaded",
            winners_count=len(winners_data),
            total_count=len(all_data),
        )

        # Calculate statistics
        winners_stats: dict[str, VariableStats] = {}
        all_stats: dict[str, VariableStats] = {}
        lift: dict[str, float] = {}

        for var in variables:
            # Extract values for this variable
            winners_values = [row.get(var) for row in winners_data if row.get(var) is not None]
            all_values = [row.get(var) for row in all_data if row.get(var) is not None]

            # Calculate stats
            winners_stats[var] = calculate_stats(winners_values, var)
            all_stats[var] = calculate_stats(all_values, var)

            # Calculate lift
            lift_val = calculate_lift(
                winners_stats[var].mean,
                all_stats[var].mean,
                var,
            )
            if lift_val is not None:
                lift[var] = lift_val

        # Create result
        result = AnalysisResult(
            run_id=run_id,
            config=config,
            winners_count=len(winners_data),
            total_count=len(all_data),
            winners_stats=winners_stats,
            all_stats=all_stats,
            lift=lift,
        )

        # Store in database
        self._store_result(result, notes)

        logger.info(
            "Analysis complete",
            run_id=run_id,
            winners=len(winners_data),
            variables_analyzed=len(variables),
        )

        return result

    def _get_winners_data(
        self,
        start_date: str,
        end_date: str,
        min_gain_pct: float,
    ) -> list[dict]:
        """
        Get neumann_scores data for winners (stocks with gain >= min_gain_pct).

        Filters by low_date falling within the analysis window.
        """
        with self.db._get_connection() as conn:
            # Join with scan_results to filter by date range
            rows = conn.execute(
                """
                SELECT ns.*
                FROM neumann_scores ns
                JOIN scan_results sr ON ns.scan_result_id = sr.id
                WHERE sr.low_date >= ? AND sr.low_date <= ?
                  AND ns.gain_pct >= ?
                ORDER BY ns.gain_pct DESC
                """,
                (start_date, end_date, min_gain_pct),
            ).fetchall()
            return [dict(row) for row in rows]

    def _get_all_data(
        self,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """
        Get neumann_scores data for all stocks in the analysis window.

        This represents the baseline population to compare against winners.
        """
        with self.db._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT ns.*
                FROM neumann_scores ns
                JOIN scan_results sr ON ns.scan_result_id = sr.id
                WHERE sr.low_date >= ? AND sr.low_date <= ?
                ORDER BY ns.gain_pct DESC
                """,
                (start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def _store_result(self, result: AnalysisResult, notes: str | None = None) -> None:
        """Store analysis results in the database."""
        # Create the run
        self.db.create_analysis_run(
            run_id=result.run_id,
            start_date=result.config.start_date,
            end_date=result.config.end_date,
            min_gain_pct=result.config.min_gain_pct,
            universe=result.config.universe,
            winners_count=result.winners_count,
            total_count=result.total_count,
            parameters={"variables": result.config.variables},
            notes=notes,
        )

        # Store results for each variable
        db_results = []

        for var, stats in result.winners_stats.items():
            db_results.append({
                "run_id": result.run_id,
                "variable_name": var,
                "population": "winners",
                **stats.to_dict(),
            })

        for var, stats in result.all_stats.items():
            db_results.append({
                "run_id": result.run_id,
                "variable_name": var,
                "population": "all",
                **stats.to_dict(),
            })

        self.db.add_analysis_results_bulk(db_results)

    def list_runs(self, limit: int | None = None) -> list[dict]:
        """List all analysis runs."""
        return self.db.get_analysis_runs(limit=limit)

    def get_run(self, run_id: str) -> dict | None:
        """Get details of a specific run."""
        return self.db.get_analysis_run(run_id)

    def get_results(
        self,
        run_id: str,
        variable: str | None = None,
        population: str | None = None,
    ) -> list[dict]:
        """Get analysis results for a run."""
        return self.db.get_analysis_results(run_id, variable, population)

    def get_lift(self, run_id: str) -> list[dict]:
        """Get lift (winners vs all) for each variable."""
        return self.db.get_analysis_lift(run_id)

    def compare_runs(
        self,
        run_id_1: str,
        run_id_2: str,
        variable: str | None = None,
    ) -> list[dict]:
        """Compare results between two runs."""
        return self.db.get_analysis_comparison(run_id_1, run_id_2, variable)

    def delete_run(self, run_id: str) -> bool:
        """Delete a run and its results."""
        return self.db.delete_analysis_run(run_id) > 0
