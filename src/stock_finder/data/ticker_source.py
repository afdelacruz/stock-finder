"""Ticker list management."""

from pathlib import Path

import pandas as pd
import structlog

logger = structlog.get_logger()


def load_tickers_from_csv(file_path: Path | str) -> list[str]:
    """
    Load ticker symbols from a CSV file.

    Expects a column named 'ticker' or 'symbol', or uses the first column.

    Args:
        file_path: Path to CSV file

    Returns:
        List of ticker symbols
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error("Ticker file not found", path=str(file_path))
        return []

    df = pd.read_csv(file_path)

    # Try to find the ticker column
    ticker_col = None
    for col in ["ticker", "Ticker", "symbol", "Symbol", "TICKER", "SYMBOL"]:
        if col in df.columns:
            ticker_col = col
            break

    if ticker_col is None:
        # Use first column
        ticker_col = df.columns[0]
        logger.info("Using first column as ticker column", column=ticker_col)

    tickers = df[ticker_col].dropna().astype(str).str.upper().str.strip().tolist()

    logger.info("Loaded tickers from file", path=str(file_path), count=len(tickers))

    return tickers


def load_tickers_from_list(tickers: list[str]) -> list[str]:
    """
    Normalize a list of tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        Normalized list of tickers (uppercase, stripped)
    """
    return [t.upper().strip() for t in tickers if t]


def get_default_tickers() -> list[str]:
    """
    Get a default list of tickers for testing/demo.

    Returns a small set of well-known stocks.
    """
    return [
        # Known big gainers (for validation)
        "HIMS",
        "RKLB",
        "PL",
        "SMCI",
        "NVDA",
        # Some established stocks
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
        # Some smaller caps
        "PLTR",
        "SOFI",
        "HOOD",
        "IONQ",
        "AFRM",
    ]
