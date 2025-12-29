"""SQLite database for storing scan results."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import TYPE_CHECKING

import structlog

from stock_finder.models.results import NeumannScore, ScanResult

if TYPE_CHECKING:
    from stock_finder.analysis.models import TrendlineAnalysis

logger = structlog.get_logger()

DEFAULT_DB_PATH = Path("data/stock_finder.db")


class Database:
    """SQLite database for persisting scan results."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    min_gain_pct REAL NOT NULL,
                    lookback_years INTEGER NOT NULL,
                    universe TEXT,
                    ticker_count INTEGER,
                    results_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                );

                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    gain_pct REAL NOT NULL,
                    low_price REAL NOT NULL,
                    low_date DATE NOT NULL,
                    high_price REAL NOT NULL,
                    high_date DATE NOT NULL,
                    current_price REAL NOT NULL,
                    days_to_peak INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_results_ticker ON scan_results(ticker);
                CREATE INDEX IF NOT EXISTS idx_results_gain ON scan_results(gain_pct DESC);
                CREATE INDEX IF NOT EXISTS idx_results_scan_run ON scan_results(scan_run_id);

                CREATE TABLE IF NOT EXISTS neumann_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_result_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    criteria_json TEXT NOT NULL,
                    drawdown REAL,
                    days_since_high INTEGER,
                    range_position REAL,
                    pct_from_sma50 REAL,
                    pct_from_sma200 REAL,
                    vol_ratio REAL,
                    market_cap_estimate REAL,
                    sma_crossover BOOLEAN,
                    gain_pct REAL,
                    days_to_peak INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scan_result_id) REFERENCES scan_results(id)
                );

                CREATE INDEX IF NOT EXISTS idx_neumann_score ON neumann_scores(score DESC);
                CREATE INDEX IF NOT EXISTS idx_neumann_ticker ON neumann_scores(ticker);
                CREATE INDEX IF NOT EXISTS idx_neumann_scan_result ON neumann_scores(scan_result_id);

                CREATE TABLE IF NOT EXISTS trendline_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_result_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    timeframe TEXT NOT NULL,

                    -- Formation
                    trendline_formed BOOLEAN NOT NULL,
                    days_to_form INTEGER,
                    swing_low_count INTEGER,

                    -- Quality
                    r_squared REAL,
                    slope_pct_per_day REAL,

                    -- Touches
                    touch_count INTEGER,
                    avg_bounce_pct REAL,
                    max_deviation_pct REAL,

                    -- Break
                    break_date DATE,
                    break_price REAL,

                    -- From scan result
                    gain_pct REAL,
                    days_to_peak INTEGER,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scan_result_id) REFERENCES scan_results(id)
                );

                CREATE INDEX IF NOT EXISTS idx_trendline_ticker ON trendline_analysis(ticker);
                CREATE INDEX IF NOT EXISTS idx_trendline_r_squared ON trendline_analysis(r_squared DESC);
                CREATE INDEX IF NOT EXISTS idx_trendline_timeframe ON trendline_analysis(timeframe);
                CREATE INDEX IF NOT EXISTS idx_trendline_scan_result ON trendline_analysis(scan_result_id);
            """)
        logger.info("Database initialized", path=str(self.db_path))

    def start_scan_run(
        self,
        min_gain_pct: float,
        lookback_years: int,
        universe: str | None = None,
        ticker_count: int | None = None,
    ) -> int:
        """Start a new scan run and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scan_runs (started_at, min_gain_pct, lookback_years, universe, ticker_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (datetime.now(), min_gain_pct, lookback_years, universe, ticker_count),
            )
            scan_run_id = cursor.lastrowid
            logger.info("Started scan run", scan_run_id=scan_run_id)
            return scan_run_id

    def add_result(self, scan_run_id: int, result: ScanResult) -> int:
        """Add a single scan result. Returns the result ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scan_results
                (scan_run_id, ticker, gain_pct, low_price, low_date, high_price, high_date, current_price, days_to_peak)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_run_id,
                    result.ticker,
                    result.gain_pct,
                    result.low_price,
                    result.low_date,
                    result.high_price,
                    result.high_date,
                    result.current_price,
                    result.days_to_peak,
                ),
            )
            # Update results count
            conn.execute(
                "UPDATE scan_runs SET results_count = results_count + 1 WHERE id = ?",
                (scan_run_id,),
            )
            return cursor.lastrowid

    def complete_scan_run(self, scan_run_id: int, status: str = "completed"):
        """Mark a scan run as completed."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE scan_runs SET completed_at = ?, status = ? WHERE id = ?",
                (datetime.now(), status, scan_run_id),
            )
            logger.info("Completed scan run", scan_run_id=scan_run_id, status=status)

    def get_scan_run(self, scan_run_id: int) -> dict | None:
        """Get scan run metadata."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM scan_runs WHERE id = ?", (scan_run_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_results(
        self,
        scan_run_id: int | None = None,
        min_gain: float | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Get scan results with optional filters."""
        query = "SELECT * FROM scan_results WHERE 1=1"
        params = []

        if scan_run_id is not None:
            query += " AND scan_run_id = ?"
            params.append(scan_run_id)

        if min_gain is not None:
            query += " AND gain_pct >= ?"
            params.append(min_gain)

        query += " ORDER BY gain_pct DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_latest_scan_run(self) -> dict | None:
        """Get the most recent scan run."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM scan_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_all_scan_runs(self) -> list[dict]:
        """Get all scan runs."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scan_runs ORDER BY started_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_top_gainers(self, limit: int = 50) -> list[dict]:
        """Get top gainers across all scans."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT ticker, MAX(gain_pct) as gain_pct,
                       low_price, low_date, high_price, high_date, current_price, days_to_peak
                FROM scan_results
                GROUP BY ticker
                ORDER BY gain_pct DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Neumann Scores Methods
    # =========================================================================

    def add_neumann_score(self, score: NeumannScore) -> int:
        """
        Add a Neumann score to the database.

        Args:
            score: NeumannScore object to save

        Returns:
            The ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO neumann_scores (
                    scan_result_id, ticker, score, criteria_json,
                    drawdown, days_since_high, range_position,
                    pct_from_sma50, pct_from_sma200, vol_ratio,
                    market_cap_estimate, sma_crossover, gain_pct, days_to_peak
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.scan_result_id,
                    score.ticker,
                    score.score,
                    json.dumps(score.criteria_results),
                    score.drawdown,
                    score.days_since_high,
                    score.range_position,
                    score.pct_from_sma50,
                    score.pct_from_sma200,
                    score.vol_ratio,
                    score.market_cap_estimate,
                    score.sma_crossover,
                    score.gain_pct,
                    score.days_to_peak,
                ),
            )
            return cursor.lastrowid

    def get_neumann_scores(
        self,
        min_score: int | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Get Neumann scores with optional filters.

        Args:
            min_score: Minimum score filter
            limit: Maximum number of results

        Returns:
            List of score records as dictionaries
        """
        query = "SELECT * FROM neumann_scores WHERE 1=1"
        params = []

        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)

        query += " ORDER BY score DESC, gain_pct DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                # Parse JSON back to dict
                if d.get("criteria_json"):
                    d["criteria_results"] = json.loads(d["criteria_json"])
                results.append(d)
            return results

    def get_neumann_score_stats(self) -> dict:
        """Get aggregate statistics for Neumann scores."""
        with self._get_connection() as conn:
            # Score distribution
            dist = conn.execute(
                """
                SELECT score, COUNT(*) as count, AVG(gain_pct) as avg_gain,
                       AVG(days_to_peak) as avg_days
                FROM neumann_scores
                GROUP BY score
                ORDER BY score DESC
                """
            ).fetchall()

            # Total counts
            totals = conn.execute(
                """
                SELECT COUNT(*) as total,
                       AVG(score) as avg_score,
                       AVG(gain_pct) as avg_gain
                FROM neumann_scores
                """
            ).fetchone()

            return {
                "distribution": [dict(row) for row in dist],
                "total": totals["total"] if totals else 0,
                "avg_score": totals["avg_score"] if totals else 0,
                "avg_gain": totals["avg_gain"] if totals else 0,
            }

    def clear_neumann_scores(self) -> int:
        """Clear all Neumann scores. Returns number of rows deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM neumann_scores")
            return cursor.rowcount

    # =========================================================================
    # Trendline Analysis Methods
    # =========================================================================

    def add_trendline_analysis(self, analysis: "TrendlineAnalysis") -> int:
        """
        Add a trendline analysis to the database.

        Args:
            analysis: TrendlineAnalysis object to save

        Returns:
            The ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trendline_analysis (
                    scan_result_id, ticker, timeframe,
                    trendline_formed, days_to_form, swing_low_count,
                    r_squared, slope_pct_per_day,
                    touch_count, avg_bounce_pct, max_deviation_pct,
                    break_date, break_price,
                    gain_pct, days_to_peak
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.scan_result_id,
                    analysis.ticker,
                    analysis.timeframe,
                    analysis.trendline_formed,
                    analysis.days_to_form,
                    analysis.swing_low_count,
                    analysis.r_squared,
                    analysis.slope_pct_per_day,
                    analysis.touch_count,
                    analysis.avg_bounce_pct,
                    analysis.max_deviation_pct,
                    analysis.break_date,
                    analysis.break_price,
                    analysis.gain_pct,
                    analysis.days_to_peak,
                ),
            )
            return cursor.lastrowid

    def get_trendline_analyses(
        self,
        min_r_squared: float | None = None,
        timeframe: str | None = None,
        formed_only: bool = False,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Get trendline analyses with optional filters.

        Args:
            min_r_squared: Minimum R² filter
            timeframe: Filter by timeframe ('daily' or 'weekly')
            formed_only: Only return stocks where trendline formed
            limit: Maximum number of results

        Returns:
            List of analysis records as dictionaries
        """
        query = "SELECT * FROM trendline_analysis WHERE 1=1"
        params = []

        if min_r_squared is not None:
            query += " AND r_squared >= ?"
            params.append(min_r_squared)

        if timeframe is not None:
            query += " AND timeframe = ?"
            params.append(timeframe)

        if formed_only:
            query += " AND trendline_formed = 1"

        query += " ORDER BY r_squared DESC, gain_pct DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_trendline_stats(self, timeframe: str | None = None) -> dict:
        """Get aggregate statistics for trendline analyses."""
        where_clause = ""
        params = []
        if timeframe:
            where_clause = " WHERE timeframe = ?"
            params = [timeframe]

        with self._get_connection() as conn:
            # Formation stats
            formation = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN trendline_formed = 1 THEN 1 ELSE 0 END) as formed,
                    AVG(CASE WHEN trendline_formed = 1 THEN days_to_form END) as avg_days_to_form,
                    AVG(CASE WHEN trendline_formed = 1 THEN swing_low_count END) as avg_swing_lows
                FROM trendline_analysis{where_clause}
                """,
                params,
            ).fetchone()

            # Quality distribution
            quality_dist = conn.execute(
                f"""
                SELECT
                    CASE
                        WHEN r_squared >= 0.9 THEN 'clean'
                        WHEN r_squared >= 0.7 THEN 'moderate'
                        ELSE 'messy'
                    END as quality,
                    COUNT(*) as count,
                    AVG(gain_pct) as avg_gain
                FROM trendline_analysis
                WHERE trendline_formed = 1{' AND timeframe = ?' if timeframe else ''}
                GROUP BY quality
                ORDER BY
                    CASE quality
                        WHEN 'clean' THEN 1
                        WHEN 'moderate' THEN 2
                        ELSE 3
                    END
                """,
                params,
            ).fetchall()

            # Touch stats
            touch_stats = conn.execute(
                f"""
                SELECT
                    AVG(touch_count) as avg_touches,
                    AVG(avg_bounce_pct) as avg_bounce_pct
                FROM trendline_analysis
                WHERE trendline_formed = 1{' AND timeframe = ?' if timeframe else ''}
                """,
                params,
            ).fetchone()

            return {
                "total": formation["total"] if formation else 0,
                "formed": formation["formed"] if formation else 0,
                "formed_pct": (formation["formed"] / formation["total"] * 100)
                if formation and formation["total"] > 0
                else 0,
                "avg_days_to_form": formation["avg_days_to_form"] if formation else 0,
                "avg_swing_lows": formation["avg_swing_lows"] if formation else 0,
                "quality_distribution": [dict(row) for row in quality_dist],
                "avg_touches": touch_stats["avg_touches"] if touch_stats else 0,
                "avg_bounce_pct": touch_stats["avg_bounce_pct"] if touch_stats else 0,
            }

    def clear_trendline_analyses(self, timeframe: str | None = None) -> int:
        """Clear trendline analyses. Returns number of rows deleted."""
        with self._get_connection() as conn:
            if timeframe:
                cursor = conn.execute(
                    "DELETE FROM trendline_analysis WHERE timeframe = ?",
                    (timeframe,),
                )
            else:
                cursor = conn.execute("DELETE FROM trendline_analysis")
            return cursor.rowcount
