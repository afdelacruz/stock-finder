"""Scanner for finding stocks with significant gains."""

from datetime import date, timedelta
from typing import Callable

import structlog
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from stock_finder.config import ScanConfig
from stock_finder.data.base import DataProvider
from stock_finder.models.results import ScanResult
from stock_finder.scanners.base import Scanner
from stock_finder.utils.calculations import calculate_max_gain

logger = structlog.get_logger()

# Type alias for result callback
ResultCallback = Callable[[ScanResult], None]


class GainerScanner(Scanner):
    """Scanner that finds stocks with significant percentage gains."""

    def __init__(
        self,
        data_provider: DataProvider,
        config: ScanConfig | None = None,
    ):
        """
        Initialize the gainer scanner.

        Args:
            data_provider: Data provider for fetching stock data
            config: Scan configuration. If None, uses defaults.
        """
        self.data_provider = data_provider
        self.config = config or ScanConfig()

    def _get_date_range(self) -> tuple[date, date]:
        """Get the start and end dates for scanning."""
        end = date.today()
        start = end - timedelta(days=self.config.lookback_years * 365)
        return start, end

    def scan_single(self, ticker: str) -> ScanResult | None:
        """
        Scan a single ticker for gains.

        Args:
            ticker: Ticker symbol to scan

        Returns:
            ScanResult if ticker meets gain threshold, None otherwise
        """
        start, end = self._get_date_range()

        logger.debug("Scanning ticker", ticker=ticker, start=start, end=end)

        df = self.data_provider.get_historical_df(ticker, start, end)

        if df is None or df.empty:
            logger.debug("No data for ticker", ticker=ticker)
            return None

        result = calculate_max_gain(
            ticker=ticker,
            df=df,
            min_gain_pct=self.config.min_gain_pct,
        )

        if result:
            logger.info(
                "Found gainer",
                ticker=ticker,
                gain_pct=f"{result.gain_pct:.1f}%",
            )

        return result

    def scan(
        self,
        tickers: list[str],
        show_progress: bool = True,
        on_result: ResultCallback | None = None,
    ) -> list[ScanResult]:
        """
        Scan multiple tickers for gains.

        Args:
            tickers: List of ticker symbols to scan
            show_progress: Whether to show progress bar
            on_result: Optional callback called for each result found (for incremental saves)

        Returns:
            List of ScanResult for tickers meeting gain threshold,
            sorted by gain percentage (descending)
        """
        results: list[ScanResult] = []
        errors: list[str] = []

        logger.info("Starting scan", ticker_count=len(tickers))

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("[cyan]{task.completed}/{task.total}"),
            ) as progress:
                task = progress.add_task("Scanning...", total=len(tickers))

                for ticker in tickers:
                    try:
                        result = self.scan_single(ticker)
                        if result:
                            results.append(result)
                            if on_result:
                                on_result(result)
                    except Exception as e:
                        logger.error("Error scanning ticker", ticker=ticker, error=str(e))
                        errors.append(ticker)

                    progress.update(task, advance=1)
        else:
            for ticker in tickers:
                try:
                    result = self.scan_single(ticker)
                    if result:
                        results.append(result)
                        if on_result:
                            on_result(result)
                except Exception as e:
                    logger.error("Error scanning ticker", ticker=ticker, error=str(e))
                    errors.append(ticker)

        # Sort by gain percentage descending
        results.sort(key=lambda r: r.gain_pct, reverse=True)

        logger.info(
            "Scan complete",
            tickers_scanned=len(tickers),
            gainers_found=len(results),
            errors=len(errors),
        )

        return results
