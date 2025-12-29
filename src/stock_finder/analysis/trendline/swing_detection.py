"""Swing low and high detection algorithms."""

import pandas as pd

from stock_finder.analysis.models import SwingPoint


def detect_swing_lows(df: pd.DataFrame, lookback: int = 10) -> list[SwingPoint]:
    """
    Detect swing lows in price data.

    A swing low is a bar where the Low price is the lowest
    of the surrounding N bars (lookback on each side).

    Args:
        df: DataFrame with OHLCV data and DatetimeIndex
        lookback: Number of bars to look back and forward

    Returns:
        List of SwingPoint objects for each detected swing low
    """
    if len(df) < (2 * lookback + 1):
        return []

    swing_lows = []

    for i in range(lookback, len(df) - lookback):
        # Get the window of bars: [i-lookback, i+lookback]
        window_start = i - lookback
        window_end = i + lookback + 1  # +1 for inclusive
        window = df["Low"].iloc[window_start:window_end]

        current_low = df["Low"].iloc[i]

        # Check if current bar's Low is strictly the minimum
        if current_low < window.drop(df["Low"].index[i]).min():
            swing_lows.append(
                SwingPoint(
                    date=df.index[i].date(),
                    price=float(current_low),
                    bar_index=i,
                )
            )

    return swing_lows


def detect_swing_highs(df: pd.DataFrame, lookback: int = 10) -> list[SwingPoint]:
    """
    Detect swing highs in price data.

    A swing high is a bar where the High price is the highest
    of the surrounding N bars (lookback on each side).

    Args:
        df: DataFrame with OHLCV data and DatetimeIndex
        lookback: Number of bars to look back and forward

    Returns:
        List of SwingPoint objects for each detected swing high
    """
    if len(df) < (2 * lookback + 1):
        return []

    swing_highs = []

    for i in range(lookback, len(df) - lookback):
        window_start = i - lookback
        window_end = i + lookback + 1
        window = df["High"].iloc[window_start:window_end]

        current_high = df["High"].iloc[i]

        # Check if current bar's High is strictly the maximum
        if current_high > window.drop(df["High"].index[i]).max():
            swing_highs.append(
                SwingPoint(
                    date=df.index[i].date(),
                    price=float(current_high),
                    bar_index=i,
                )
            )

    return swing_highs


def filter_ascending_lows(swing_lows: list[SwingPoint]) -> list[SwingPoint]:
    """
    Filter swing lows to keep only those forming higher lows.

    Each kept swing low must be higher than the previous one,
    forming an ascending pattern (rising trendline support).

    Args:
        swing_lows: List of detected swing lows

    Returns:
        Filtered list with only ascending swing lows
    """
    if len(swing_lows) == 0:
        return []

    if len(swing_lows) == 1:
        return [swing_lows[0]]

    ascending = [swing_lows[0]]

    for low in swing_lows[1:]:
        if low.price > ascending[-1].price:
            ascending.append(low)

    return ascending
