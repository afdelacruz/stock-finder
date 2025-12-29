"""TrendlineAnalyzer - Orchestrates trendline analysis for stocks."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pandas as pd
import structlog

from stock_finder.analysis.models import (
    TrendlineAnalysis,
    TrendlineConfig,
)
from stock_finder.analysis.trendline.swing_detection import (
    detect_swing_lows,
    filter_ascending_lows,
)
from stock_finder.analysis.trendline.trendline_fitting import fit_trendline
from stock_finder.analysis.trendline.touch_detection import detect_touches

if TYPE_CHECKING:
    from stock_finder.data.database import Database
    from stock_finder.data.providers.base import DataProvider

logger = structlog.get_logger()


class TrendlineAnalyzer:
    """
    Analyzes post-ignition price structure to detect rising trendlines.

    This analyzer:
    1. Fetches historical data around the stock's move (ignition to peak)
    2. Detects swing lows in the price data
    3. Filters for ascending (higher) lows
    4. Fits a trendline through the swing lows
    5. Detects touches/bounces off the trendline
    6. Calculates quality metrics (R², slope, etc.)
    """

    def __init__(
        self,
        provider: DataProvider,
        db: Database | None = None,
        config: TrendlineConfig | None = None,
    ):
        """
        Initialize the analyzer.

        Args:
            provider: Data provider for fetching historical prices
            db: Optional database for persisting results
            config: Configuration options (uses defaults if not provided)
        """
        self.provider = provider
        self.db = db
        self.config = config or TrendlineConfig()

    def analyze_stock(
        self,
        scan_result: dict,
        timeframe: str = "daily",
        save: bool = False,
    ) -> TrendlineAnalysis:
        """
        Analyze trendline formation for a single stock.

        Args:
            scan_result: Dict with scan result data including:
                - id: scan_result_id
                - ticker: stock symbol
                - low_date: ignition date (start of move)
                - high_date: peak date (end of move)
                - gain_pct: percentage gain
                - days_to_peak: trading days from low to high
            timeframe: 'daily' or 'weekly'
            save: Whether to save to database

        Returns:
            TrendlineAnalysis with results
        """
        ticker = scan_result["ticker"]
        scan_result_id = scan_result["id"]

        logger.debug("Analyzing trendline", ticker=ticker, timeframe=timeframe)

        # Parse dates
        low_date = self._parse_date(scan_result["low_date"])
        high_date = self._parse_date(scan_result["high_date"])

        # Fetch data with buffer
        start_date = low_date - timedelta(days=self.config.data_buffer_days)
        end_date = high_date + timedelta(days=self.config.data_buffer_days)

        stock_data = self.provider.get_historical(ticker, start_date, end_date)

        # Handle empty data - provider may return StockData or DataFrame
        if stock_data is None:
            df = pd.DataFrame()
        elif hasattr(stock_data, 'data'):
            # StockData object
            df = stock_data.data
        else:
            # Already a DataFrame
            df = stock_data

        if len(df) == 0:
            analysis = TrendlineAnalysis(
                ticker=ticker,
                scan_result_id=scan_result_id,
                timeframe=timeframe,
                trendline_formed=False,
                swing_low_count=0,
                gain_pct=scan_result.get("gain_pct"),
                days_to_peak=scan_result.get("days_to_peak"),
            )
            if save and self.db:
                self.db.add_trendline_analysis(analysis)
            return analysis

        # Resample to weekly if needed
        if timeframe == "weekly":
            df = self._resample_to_weekly(df)

        # Filter to analysis period (ignition to peak)
        df = self._filter_to_period(df, low_date, high_date)

        if len(df) == 0:
            analysis = TrendlineAnalysis(
                ticker=ticker,
                scan_result_id=scan_result_id,
                timeframe=timeframe,
                trendline_formed=False,
                swing_low_count=0,
                gain_pct=scan_result.get("gain_pct"),
                days_to_peak=scan_result.get("days_to_peak"),
            )
            if save and self.db:
                self.db.add_trendline_analysis(analysis)
            return analysis

        # Detect swing lows
        swing_lows = detect_swing_lows(df, lookback=self.config.swing_lookback)

        # Filter for ascending lows
        ascending_lows = filter_ascending_lows(swing_lows)

        # Not enough swing lows for a trendline
        if len(ascending_lows) < self.config.min_touches:
            analysis = TrendlineAnalysis(
                ticker=ticker,
                scan_result_id=scan_result_id,
                timeframe=timeframe,
                trendline_formed=False,
                swing_low_count=len(swing_lows),
                swing_lows=swing_lows,
                gain_pct=scan_result.get("gain_pct"),
                days_to_peak=scan_result.get("days_to_peak"),
            )
            if save and self.db:
                self.db.add_trendline_analysis(analysis)
            return analysis

        # Fit trendline
        trendline = fit_trendline(ascending_lows)

        if trendline is None:
            analysis = TrendlineAnalysis(
                ticker=ticker,
                scan_result_id=scan_result_id,
                timeframe=timeframe,
                trendline_formed=False,
                swing_low_count=len(swing_lows),
                swing_lows=swing_lows,
                gain_pct=scan_result.get("gain_pct"),
                days_to_peak=scan_result.get("days_to_peak"),
            )
            if save and self.db:
                self.db.add_trendline_analysis(analysis)
            return analysis

        # Check if R² meets minimum threshold
        trendline_formed = trendline.r_squared >= self.config.min_r_squared

        # Detect touches
        touches = detect_touches(df, trendline, tolerance=self.config.touch_tolerance)

        # Calculate metrics
        days_to_form = None
        if len(ascending_lows) >= 2:
            first_low = ascending_lows[0]
            last_low = ascending_lows[-1]
            days_to_form = (last_low.date - first_low.date).days

        slope_pct_per_day = None
        if trendline.slope != 0 and trendline.intercept != 0:
            # Convert absolute slope to percentage slope per day
            slope_pct_per_day = (trendline.slope / trendline.intercept) * 100

        avg_bounce_pct = None
        max_deviation_pct = None
        if touches:
            deviations = [abs(t.deviation_pct) for t in touches]
            avg_bounce_pct = sum(deviations) / len(deviations) * 100
            max_deviation_pct = max(deviations) * 100

        analysis = TrendlineAnalysis(
            ticker=ticker,
            scan_result_id=scan_result_id,
            timeframe=timeframe,
            trendline_formed=trendline_formed,
            days_to_form=days_to_form,
            swing_low_count=len(swing_lows),
            r_squared=trendline.r_squared,
            slope_pct_per_day=slope_pct_per_day,
            touch_count=len(touches),
            avg_bounce_pct=avg_bounce_pct,
            max_deviation_pct=max_deviation_pct,
            gain_pct=scan_result.get("gain_pct"),
            days_to_peak=scan_result.get("days_to_peak"),
            trendline_fit=trendline,
            swing_lows=swing_lows,
            touches=touches,
        )

        if save and self.db:
            self.db.add_trendline_analysis(analysis)

        logger.debug(
            "Trendline analysis complete",
            ticker=ticker,
            formed=trendline_formed,
            r_squared=trendline.r_squared,
            touches=len(touches),
        )

        return analysis

    def analyze_all(
        self,
        scan_results: list[dict],
        timeframe: str = "daily",
        save: bool = True,
    ) -> list[TrendlineAnalysis]:
        """
        Analyze trendlines for multiple stocks.

        Args:
            scan_results: List of scan result dicts
            timeframe: 'daily', 'weekly', or 'both'
            save: Whether to save results to database

        Returns:
            List of TrendlineAnalysis results
        """
        results = []
        total = len(scan_results)

        for i, scan_result in enumerate(scan_results, 1):
            ticker = scan_result["ticker"]
            logger.info(f"Analyzing {ticker}", progress=f"{i}/{total}")

            try:
                if timeframe == "both":
                    # Analyze both daily and weekly
                    daily = self.analyze_stock(scan_result, "daily", save=save)
                    weekly = self.analyze_stock(scan_result, "weekly", save=save)
                    results.extend([daily, weekly])
                else:
                    result = self.analyze_stock(scan_result, timeframe, save=save)
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to analyze {ticker}: {e}")
                continue

        return results

    def _parse_date(self, date_value) -> date:
        """Parse date from various formats."""
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            return date.fromisoformat(date_value)
        raise ValueError(f"Cannot parse date: {date_value}")

    def _resample_to_weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample daily data to weekly OHLCV."""
        return df.resample("W").agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        ).dropna()

    def _filter_to_period(
        self, df: pd.DataFrame, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Filter DataFrame to date range."""
        mask = (df.index.date >= start_date) & (df.index.date <= end_date)
        return df[mask].copy()
