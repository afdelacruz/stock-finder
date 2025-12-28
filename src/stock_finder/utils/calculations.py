"""Pure calculation functions for stock analysis."""

from datetime import date

import pandas as pd

from stock_finder.models.results import ScanResult


def calculate_max_gain(
    ticker: str,
    df: pd.DataFrame,
    min_gain_pct: float = 500.0,
) -> ScanResult | None:
    """
    Calculate the maximum gain (lowest to highest) within a price series.

    This finds the maximum "drawup" - the best possible gain if you bought
    at the lowest point and sold at the highest point AFTER that low.

    Args:
        ticker: Stock ticker symbol
        df: DataFrame with 'Close' column and DatetimeIndex
        min_gain_pct: Minimum gain percentage to return a result

    Returns:
        ScanResult if gain meets threshold, None otherwise
    """
    if df.empty or len(df) < 2:
        return None

    # Ensure we have the Close column
    if "Close" not in df.columns:
        return None

    close = df["Close"].dropna()
    if len(close) < 2:
        return None

    # Find the maximum drawup (lowest point to highest point after it)
    # For each point, track the minimum seen so far
    # Then find max gain from that minimum to current price

    best_gain_pct = 0.0
    best_low_idx = None
    best_high_idx = None
    best_low_price = None
    best_high_price = None

    min_price = close.iloc[0]
    min_idx = close.index[0]

    for i in range(1, len(close)):
        current_price = close.iloc[i]
        current_idx = close.index[i]

        # Update minimum if we found a new low
        if current_price < min_price:
            min_price = current_price
            min_idx = current_idx
        else:
            # Calculate gain from minimum to current
            if min_price > 0:
                gain_pct = ((current_price - min_price) / min_price) * 100

                if gain_pct > best_gain_pct:
                    best_gain_pct = gain_pct
                    best_low_idx = min_idx
                    best_high_idx = current_idx
                    best_low_price = min_price
                    best_high_price = current_price

    # Check if gain meets threshold
    if best_gain_pct < min_gain_pct:
        return None

    if best_low_idx is None or best_high_idx is None:
        return None

    # Calculate trading days between low and high
    low_loc = close.index.get_loc(best_low_idx)
    high_loc = close.index.get_loc(best_high_idx)
    days_to_peak = high_loc - low_loc

    # Get current price (last close)
    current_price = close.iloc[-1]

    return ScanResult(
        ticker=ticker,
        gain_pct=best_gain_pct,
        low_date=pd.Timestamp(best_low_idx).date(),
        high_date=pd.Timestamp(best_high_idx).date(),
        low_price=best_low_price,
        high_price=best_high_price,
        current_price=current_price,
        days_to_peak=days_to_peak,
    )
