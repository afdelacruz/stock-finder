"""Summary metrics component."""

from __future__ import annotations

from stock_finder.data.database import Database


def get_summary_data(db: Database) -> dict | None:
    """
    Get summary statistics for the dashboard.

    Returns:
        Dict with total_records, unique_tickers, avg_gain, avg_days
    """
    stats = db.get_neumann_score_stats()

    if not stats or stats.get("total", 0) == 0:
        return None

    return {
        "total_records": stats["total"],
        "unique_tickers": stats["total"],  # TODO: Get unique count
        "avg_gain": stats["avg_gain"] or 0,
        "avg_days": 500,  # TODO: Calculate from data
        "avg_score": stats["avg_score"] or 0,
    }
