"""Research runner for executing and storing analyses."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import structlog

from stock_finder.data.database import Database
from stock_finder.research.queries import QueryResult, ResearchQueries

logger = structlog.get_logger()


class ResearchRunner:
    """
    Orchestrates research analyses and stores results.

    Example usage:
        runner = ResearchRunner()
        results = runner.run_full_analysis(
            run_id="analysis_2025-01-01",
            notes="Monthly analysis run"
        )
        print(f"Stored {results['findings_count']} findings")
    """

    def __init__(self, db_path: Path | str = "data/stock_finder.db"):
        self.db = Database(db_path)
        self.queries = ResearchQueries(db_path)

    def run_full_analysis(
        self,
        run_id: str | None = None,
        time_window_start: str | None = None,
        time_window_end: str | None = None,
        max_gain: float = 50000,
        notes: str | None = None,
    ) -> dict:
        """
        Run all analyses and store results.

        Args:
            run_id: Unique identifier (auto-generated if not provided)
            time_window_start: Start date for data window
            time_window_end: End date for data window
            max_gain: Exclude outliers above this gain %
            notes: Optional notes about the run

        Returns:
            Dict with run metadata and counts
        """
        if run_id is None:
            run_id = f"full_analysis_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"

        # Start the run
        self.db.start_research_run(
            run_id=run_id,
            run_type="full_analysis",
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            parameters={"max_gain": max_gain},
            notes=notes,
        )

        # Run all analyses
        all_results: list[QueryResult] = []

        analyses = [
            ("summary_stats", self.queries.summary_stats),
            ("criteria_lift", self.queries.criteria_lift),
            ("setup_quality", self.queries.setup_quality_tiers),
            ("theme_performance", self.queries.theme_performance),
            ("themed_vs_unthemed", self.queries.themed_vs_unthemed),
            ("timing_by_month", self.queries.timing_by_month),
            ("timing_by_year", self.queries.timing_by_year),
            ("score_distribution", self.queries.score_distribution),
            ("simulated_score", self.queries.simulated_score_distribution),
            ("volume_profile", self.queries.volume_profile),
            ("move_speed", self.queries.move_speed_profile),
        ]

        for name, query_fn in analyses:
            try:
                results = query_fn(max_gain=max_gain)
                all_results.extend(results)
                logger.info(f"Completed {name}", count=len(results))
            except Exception as e:
                logger.error(f"Failed {name}", error=str(e))

        # Store all findings
        findings = []
        for result in all_results:
            for metric_name, metric_value in result.metrics.items():
                # Skip non-numeric values
                if not isinstance(metric_value, (int, float)) or metric_value is None:
                    continue
                findings.append({
                    "run_id": run_id,
                    "finding_type": result.finding_type,
                    "finding_key": result.finding_key,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "sample_size": result.sample_size,
                    "time_window_start": time_window_start,
                    "time_window_end": time_window_end,
                })

        count = self.db.add_findings_bulk(findings)

        logger.info(
            "Research run complete",
            run_id=run_id,
            findings_count=count,
        )

        return {
            "run_id": run_id,
            "findings_count": count,
            "analyses_run": len(analyses),
        }

    def run_single_analysis(
        self,
        analysis_name: str,
        run_id: str | None = None,
        max_gain: float = 50000,
    ) -> list[QueryResult]:
        """
        Run a single analysis and optionally store results.

        Args:
            analysis_name: Name of the analysis to run
            run_id: If provided, store results under this run ID
            max_gain: Exclude outliers above this gain %

        Returns:
            List of QueryResult objects
        """
        analysis_map: dict[str, Callable] = {
            "summary": self.queries.summary_stats,
            "criteria_lift": self.queries.criteria_lift,
            "setup_quality": self.queries.setup_quality_tiers,
            "theme_performance": self.queries.theme_performance,
            "themed_vs_unthemed": self.queries.themed_vs_unthemed,
            "timing_month": self.queries.timing_by_month,
            "timing_year": self.queries.timing_by_year,
            "score_distribution": self.queries.score_distribution,
            "simulated_score": self.queries.simulated_score_distribution,
            "volume_profile": self.queries.volume_profile,
            "move_speed": self.queries.move_speed_profile,
        }

        if analysis_name not in analysis_map:
            available = ", ".join(analysis_map.keys())
            raise ValueError(f"Unknown analysis: {analysis_name}. Available: {available}")

        results = analysis_map[analysis_name](max_gain=max_gain)

        if run_id:
            findings = []
            for result in results:
                for metric_name, metric_value in result.metrics.items():
                    if not isinstance(metric_value, (int, float)) or metric_value is None:
                        continue
                    findings.append({
                        "run_id": run_id,
                        "finding_type": result.finding_type,
                        "finding_key": result.finding_key,
                        "metric_name": metric_name,
                        "metric_value": metric_value,
                        "sample_size": result.sample_size,
                    })
            self.db.add_findings_bulk(findings)

        return results

    def compare_runs(
        self,
        run_id_1: str,
        run_id_2: str,
        finding_type: str | None = None,
    ) -> list[dict]:
        """
        Compare findings between two research runs.

        Args:
            run_id_1: First run ID (baseline)
            run_id_2: Second run ID (comparison)
            finding_type: Optional filter by finding type

        Returns:
            List of comparison dicts with both values and % change
        """
        return self.db.compare_findings(run_id_1, run_id_2, finding_type)

    def get_latest_findings(
        self,
        finding_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get findings from the most recent run.

        Args:
            finding_type: Optional filter by finding type
            limit: Max runs to check

        Returns:
            List of finding dicts
        """
        runs = self.db.get_research_runs(limit=1)
        if not runs:
            return []

        return self.db.get_findings(
            run_id=runs[0]["id"],
            finding_type=finding_type,
        )

    def format_results(self, results: list[QueryResult]) -> str:
        """Format QueryResult list as readable text."""
        lines = []
        current_type = None

        for result in results:
            if result.finding_type != current_type:
                current_type = result.finding_type
                lines.append(f"\n## {current_type.replace('_', ' ').title()}\n")

            lines.append(f"**{result.finding_key}** (n={result.sample_size})")
            for key, value in result.metrics.items():
                if isinstance(value, float):
                    lines.append(f"  - {key}: {value:,.1f}")
                else:
                    lines.append(f"  - {key}: {value}")
            lines.append("")

        return "\n".join(lines)

    def format_comparison(self, comparisons: list[dict]) -> str:
        """Format comparison results as readable text."""
        lines = ["## Run Comparison\n"]
        current_type = None

        for row in comparisons:
            if row["finding_type"] != current_type:
                current_type = row["finding_type"]
                lines.append(f"\n### {current_type.replace('_', ' ').title()}\n")
                lines.append("| Key | Metric | Run 1 | Run 2 | Change |")
                lines.append("|-----|--------|-------|-------|--------|")

            change = row["pct_change"]
            change_str = f"{change:+.1f}%" if change else "N/A"
            lines.append(
                f"| {row['finding_key']} | {row['metric_name']} | "
                f"{row['value_1']:.1f} | {row['value_2']:.1f} | {change_str} |"
            )

        return "\n".join(lines)
