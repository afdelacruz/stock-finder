"""Fetch ticker lists from NASDAQ FTP."""

import re
import urllib.request
from io import StringIO

import pandas as pd
import structlog

logger = structlog.get_logger()

NASDAQ_FTP_URL = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqtraded.txt"


def fetch_nasdaq_tickers(
    include_etfs: bool = False,
    exchanges: list[str] | None = None,
) -> pd.DataFrame:
    """
    Fetch all traded tickers from NASDAQ FTP.

    Args:
        include_etfs: Whether to include ETFs (default: False)
        exchanges: Filter to specific exchanges. Options:
            - 'Q' = NASDAQ
            - 'N' = NYSE
            - 'A' = NYSE American (AMEX)
            - 'P' = NYSE Arca
            - 'Z' = BATS
            - None = all exchanges

    Returns:
        DataFrame with columns: symbol, name, exchange, etf
    """
    logger.info("Fetching tickers from NASDAQ FTP", url=NASDAQ_FTP_URL)

    try:
        with urllib.request.urlopen(NASDAQ_FTP_URL, timeout=30) as response:
            content = response.read().decode("utf-8")
    except Exception as e:
        logger.error("Failed to fetch NASDAQ FTP", error=str(e))
        raise

    # Parse the pipe-delimited file
    df = pd.read_csv(StringIO(content), sep="|")

    # Clean column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Filter out the footer row (contains "File Creation Time")
    df = df[~df["symbol"].astype(str).str.contains("File Creation", na=False)]

    # Only include actively traded
    df = df[df["nasdaq_traded"] == "Y"]

    # Filter out test issues
    df = df[df["test_issue"] == "N"]

    # Filter out ETFs unless requested
    if not include_etfs:
        df = df[df["etf"] == "N"]

    # Filter by exchange if specified
    if exchanges:
        df = df[df["listing_exchange"].isin(exchanges)]

    # Clean up symbols - remove ones with special characters (warrants, units, etc.)
    # Keep only standard ticker symbols (letters, up to 5 chars typically)
    df = df[df["symbol"].str.match(r"^[A-Z]{1,5}$", na=False)]

    # Select and rename columns
    result = pd.DataFrame({
        "symbol": df["symbol"],
        "name": df["security_name"].str.strip(),
        "exchange": df["listing_exchange"],
        "etf": df["etf"] == "Y",
    })

    logger.info("Fetched tickers", count=len(result))

    return result.reset_index(drop=True)


def get_common_stock_tickers(
    exchanges: list[str] | None = None,
) -> list[str]:
    """
    Get a list of common stock tickers (no ETFs, warrants, etc.).

    Args:
        exchanges: Filter to specific exchanges (Q=NASDAQ, N=NYSE, etc.)

    Returns:
        List of ticker symbols
    """
    df = fetch_nasdaq_tickers(include_etfs=False, exchanges=exchanges)
    return df["symbol"].tolist()


def get_nasdaq_tickers() -> list[str]:
    """Get all NASDAQ-listed common stocks."""
    return get_common_stock_tickers(exchanges=["Q"])


def get_nyse_tickers() -> list[str]:
    """Get all NYSE-listed common stocks."""
    return get_common_stock_tickers(exchanges=["N"])


def get_all_us_tickers() -> list[str]:
    """Get all US common stocks (NASDAQ + NYSE + others)."""
    return get_common_stock_tickers(exchanges=None)
