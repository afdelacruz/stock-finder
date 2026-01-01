"""Theme performance component."""

from __future__ import annotations

from stock_finder.data.database import Database
from stock_finder.research.queries import ResearchQueries


def get_theme_data(db: Database) -> list[dict]:
    """
    Get theme performance data for the dashboard.

    Returns:
        List of theme dicts with theme, wave, count, avg_gain, avg_days
    """
    queries = ResearchQueries(db.db_path)
    results = queries.theme_performance()

    themes = []
    for result in results:
        # Parse theme and wave from finding_key (e.g., "crypto_wave1")
        key = result.finding_key
        if "_wave" in key:
            parts = key.rsplit("_wave", 1)
            theme_name = parts[0].replace("_", " ").title()
            wave = int(parts[1]) if parts[1].isdigit() else 1
        else:
            theme_name = key.replace("_", " ").title()
            wave = 1

        themes.append({
            "theme": theme_name,
            "wave": wave,
            "count": result.sample_size,
            "avg_gain": result.metrics.get("avg_gain", 0),
            "avg_days": result.metrics.get("avg_days", 0),
        })

    return themes
