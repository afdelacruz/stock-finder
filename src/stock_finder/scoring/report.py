"""Report generator for Neumann scoring results."""

from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from stock_finder.data.database import Database


@dataclass
class ScoringReport:
    """Container for scoring report data."""

    total_scored: int
    avg_score: float
    avg_gain: float
    distribution: list[dict]
    criteria_stats: dict[str, dict]


def generate_report(db: Database) -> ScoringReport:
    """
    Generate a scoring report from the database.

    Args:
        db: Database containing Neumann scores

    Returns:
        ScoringReport with statistics
    """
    stats = db.get_neumann_score_stats()
    scores = db.get_neumann_scores()

    # Calculate criteria predictiveness
    criteria_stats = _calculate_criteria_stats(scores)

    return ScoringReport(
        total_scored=stats["total"],
        avg_score=stats["avg_score"] or 0,
        avg_gain=stats["avg_gain"] or 0,
        distribution=stats["distribution"],
        criteria_stats=criteria_stats,
    )


def _calculate_criteria_stats(scores: list[dict]) -> dict[str, dict]:
    """
    Calculate statistics for each criterion.

    For each criterion, calculates:
    - pass_rate: What % of stocks passed this criterion
    - avg_gain_when_passed: Average gain for stocks that passed
    - avg_gain_when_failed: Average gain for stocks that failed
    """
    if not scores:
        return {}

    criteria_names = set()
    for score in scores:
        if "criteria_results" in score:
            criteria_names.update(score["criteria_results"].keys())

    stats = {}
    for name in criteria_names:
        passed_gains = []
        failed_gains = []

        for score in scores:
            results = score.get("criteria_results", {})
            if name not in results:
                continue

            gain = score.get("gain_pct", 0) or 0
            if results[name].get("passed"):
                passed_gains.append(gain)
            else:
                failed_gains.append(gain)

        total = len(passed_gains) + len(failed_gains)
        stats[name] = {
            "pass_rate": len(passed_gains) / total if total > 0 else 0,
            "passed_count": len(passed_gains),
            "failed_count": len(failed_gains),
            "avg_gain_when_passed": (
                sum(passed_gains) / len(passed_gains) if passed_gains else 0
            ),
            "avg_gain_when_failed": (
                sum(failed_gains) / len(failed_gains) if failed_gains else 0
            ),
        }

    return stats


def print_report(report: ScoringReport, console: Console | None = None) -> None:
    """
    Print a formatted report to the console.

    Args:
        report: ScoringReport to display
        console: Rich Console (creates one if not provided)
    """
    if console is None:
        console = Console()

    console.print()
    console.print(f"[bold]Neumann Scoring Report[/bold]")
    console.print(f"[dim]{'=' * 50}[/dim]")
    console.print()

    # Summary
    console.print(f"[bold]Summary[/bold]")
    console.print(f"  Total Scored: {report.total_scored:,}")
    console.print(f"  Average Score: {report.avg_score:.2f} / 8")
    console.print(f"  Average Gain: {report.avg_gain:,.1f}%")
    console.print()

    # Score Distribution
    if report.distribution:
        table = Table(title="Score Distribution")
        table.add_column("Score", justify="right")
        table.add_column("Count", justify="right")
        table.add_column("Avg Gain %", justify="right")
        table.add_column("Avg Days", justify="right")

        for row in report.distribution:
            score = row.get("score", 0)
            count = row.get("count", 0)
            avg_gain = row.get("avg_gain", 0) or 0
            avg_days = row.get("avg_days", 0) or 0

            table.add_row(
                str(score),
                f"{count:,}",
                f"{avg_gain:,.1f}%",
                f"{avg_days:.0f}",
            )

        console.print(table)
        console.print()

    # Criteria Predictiveness
    if report.criteria_stats:
        table = Table(title="Criteria Predictiveness")
        table.add_column("Criterion", justify="left")
        table.add_column("Pass Rate", justify="right")
        table.add_column("Avg Gain (Pass)", justify="right")
        table.add_column("Avg Gain (Fail)", justify="right")
        table.add_column("Lift", justify="right")

        # Sort by lift (difference in gains)
        sorted_criteria = sorted(
            report.criteria_stats.items(),
            key=lambda x: x[1]["avg_gain_when_passed"] - x[1]["avg_gain_when_failed"],
            reverse=True,
        )

        for name, stats in sorted_criteria:
            pass_rate = stats["pass_rate"]
            avg_pass = stats["avg_gain_when_passed"]
            avg_fail = stats["avg_gain_when_failed"]
            lift = avg_pass - avg_fail

            table.add_row(
                name,
                f"{pass_rate*100:.1f}%",
                f"{avg_pass:,.1f}%",
                f"{avg_fail:,.1f}%",
                f"{lift:+,.1f}%",
            )

        console.print(table)
        console.print()

    # High scorers sample
    console.print("[bold]Note:[/bold] Use 'stock-finder neumann results --min-score 5' to see high scorers")
