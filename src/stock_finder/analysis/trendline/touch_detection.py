"""Touch detection for trendlines."""

import pandas as pd

from stock_finder.analysis.models import TrendlineFit, TouchPoint


def detect_touches(
    df: pd.DataFrame,
    trendline: TrendlineFit,
    tolerance: float = 0.02,
) -> list[TouchPoint]:
    """
    Detect points where price touched or came close to the trendline.

    A touch is detected when the Low price is within the tolerance
    percentage of the trendline value at that bar.

    Args:
        df: DataFrame with OHLCV data and DatetimeIndex
        trendline: Fitted trendline to check against
        tolerance: Percentage tolerance for touch detection (default 2%)
                   0.02 means within ±2% of trendline

    Returns:
        List of TouchPoint objects sorted by bar index
    """
    if len(df) == 0:
        return []

    touches = []

    for i in range(len(df)):
        row = df.iloc[i]
        trendline_price = trendline.price_at_bar(i)

        # Calculate deviation as percentage
        if trendline_price == 0:
            continue  # Avoid division by zero

        deviation_pct = (row["Low"] - trendline_price) / trendline_price

        # Check if within tolerance
        if abs(deviation_pct) <= tolerance:
            touches.append(
                TouchPoint(
                    date=df.index[i].date(),
                    price=float(row["Low"]),
                    trendline_price=float(trendline_price),
                    deviation_pct=float(deviation_pct),
                    bar_index=i,
                )
            )

    return touches
