"""Setup quality tiers component."""

from __future__ import annotations

from stock_finder.data.database import Database
from stock_finder.research.queries import ResearchQueries


def get_setup_quality_data(db: Database) -> list[dict]:
    """
    Get setup quality tier data for the dashboard.

    Returns:
        List of tier dicts with tier, count, avg_gain, avg_days
    """
    queries = ResearchQueries(db.db_path)
    results = queries.setup_quality_tiers()

    tiers = []
    for result in results:
        tiers.append({
            "tier": result.finding_key,
            "count": result.sample_size,
            "avg_gain": result.metrics.get("avg_gain", 0),
            "avg_days": result.metrics.get("avg_days", 0),
        })

    return tiers
