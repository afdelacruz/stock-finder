"""Base scanner interface."""

from abc import ABC, abstractmethod

from stock_finder.models.results import ScanResult


class Scanner(ABC):
    """Abstract base class for stock scanners."""

    @abstractmethod
    def scan(self, tickers: list[str]) -> list[ScanResult]:
        """
        Scan a list of tickers and return matching results.

        Args:
            tickers: List of ticker symbols to scan

        Returns:
            List of ScanResult for tickers meeting criteria
        """
        pass

    @abstractmethod
    def scan_single(self, ticker: str) -> ScanResult | None:
        """
        Scan a single ticker.

        Args:
            ticker: Ticker symbol to scan

        Returns:
            ScanResult if ticker meets criteria, None otherwise
        """
        pass
