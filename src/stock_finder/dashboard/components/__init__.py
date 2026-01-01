"""Dashboard components - data fetchers for each section."""

from stock_finder.dashboard.components.summary import get_summary_data
from stock_finder.dashboard.components.setup_quality import get_setup_quality_data
from stock_finder.dashboard.components.themes import get_theme_data
from stock_finder.dashboard.components.watchlist import get_watchlist_data

__all__ = [
    "get_summary_data",
    "get_setup_quality_data",
    "get_theme_data",
    "get_watchlist_data",
]
