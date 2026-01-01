"""Watchlist component."""

from __future__ import annotations

from stock_finder.data.database import Database


def get_watchlist_data(db: Database) -> list[dict]:
    """
    Get current watchlist items for the dashboard.

    Returns:
        List of watchlist item dicts
    """
    # Get all watching items (not removed)
    items = db.get_watchlist(status="watching")

    # Also include triggered items
    triggered = db.get_watchlist(status="triggered")
    items.extend(triggered)

    return items
