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

                -- Research tables for tracking themes, findings, and watchlists

                CREATE TABLE IF NOT EXISTS themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    wave INTEGER DEFAULT 1,
                    added_date DATE DEFAULT CURRENT_DATE,
                    notes TEXT,
                    UNIQUE(ticker, theme, wave)
                );

                CREATE INDEX IF NOT EXISTS idx_themes_ticker ON themes(ticker);
                CREATE INDEX IF NOT EXISTS idx_themes_theme ON themes(theme);

                CREATE TABLE IF NOT EXISTS research_runs (
                    id TEXT PRIMARY KEY,
                    run_type TEXT NOT NULL,
                    time_window_start DATE,
                    time_window_end DATE,
                    parameters TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_research_runs_type ON research_runs(run_type);
                CREATE INDEX IF NOT EXISTS idx_research_runs_created ON research_runs(created_at DESC);

                CREATE TABLE IF NOT EXISTS research_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    finding_type TEXT NOT NULL,
                    finding_key TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    sample_size INTEGER,
                    time_window_start DATE,
                    time_window_end DATE,
                    parameters TEXT,
                    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES research_runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_findings_run ON research_findings(run_id);
                CREATE INDEX IF NOT EXISTS idx_findings_type ON research_findings(finding_type);
                CREATE INDEX IF NOT EXISTS idx_findings_key ON research_findings(finding_key);

                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    theme TEXT,
                    setup_score INTEGER,
                    drawdown REAL,
                    days_declining INTEGER,
                    vol_ratio REAL,
                    price_at_add REAL,
                    added_date DATE DEFAULT CURRENT_DATE,
                    status TEXT DEFAULT 'watching',
                    trigger_date DATE,
                    trigger_price REAL,
                    notes TEXT,
                    UNIQUE(ticker, added_date)
                );

                CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON watchlist(ticker);
                CREATE INDEX IF NOT EXISTS idx_watchlist_status ON watchlist(status);
                CREATE INDEX IF NOT EXISTS idx_watchlist_theme ON watchlist(theme);

                -- Statistical analysis framework tables

                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id TEXT PRIMARY KEY,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    min_gain_pct REAL NOT NULL,
                    universe TEXT,
                    winners_count INTEGER,
                    total_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parameters TEXT,
                    notes TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_analysis_runs_dates ON analysis_runs(start_date, end_date);
                CREATE INDEX IF NOT EXISTS idx_analysis_runs_created ON analysis_runs(created_at DESC);

                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    variable_name TEXT NOT NULL,
                    population TEXT NOT NULL,
                    mean REAL,
                    median REAL,
                    std_dev REAL,
                    min_val REAL,
                    max_val REAL,
                    p10 REAL,
                    p25 REAL,
                    p75 REAL,
                    p90 REAL,
                    sample_size INTEGER,
                    FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_analysis_results_run ON analysis_results(run_id);
                CREATE INDEX IF NOT EXISTS idx_analysis_results_variable ON analysis_results(variable_name);
                CREATE INDEX IF NOT EXISTS idx_analysis_results_population ON analysis_results(population);
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

    # =========================================================================
    # Theme Methods
    # =========================================================================

    def add_theme(
        self,
        ticker: str,
        theme: str,
        wave: int = 1,
        notes: str | None = None,
    ) -> int:
        """
        Add a ticker-theme mapping.

        Args:
            ticker: Stock ticker symbol
            theme: Theme name (e.g., 'Crypto', 'Nuclear', 'Meme')
            wave: Wave number for multi-wave themes (default 1)
            notes: Optional notes

        Returns:
            The ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO themes (ticker, theme, wave, notes)
                VALUES (?, ?, ?, ?)
                """,
                (ticker.upper(), theme, wave, notes),
            )
            return cursor.lastrowid

    def add_themes_bulk(self, themes: list[dict]) -> int:
        """
        Add multiple theme mappings at once.

        Args:
            themes: List of dicts with keys: ticker, theme, wave (optional), notes (optional)

        Returns:
            Number of rows inserted
        """
        with self._get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT OR REPLACE INTO themes (ticker, theme, wave, notes)
                VALUES (:ticker, :theme, :wave, :notes)
                """,
                [
                    {
                        "ticker": t["ticker"].upper(),
                        "theme": t["theme"],
                        "wave": t.get("wave", 1),
                        "notes": t.get("notes"),
                    }
                    for t in themes
                ],
            )
            return cursor.rowcount

    def get_themes(self, theme: str | None = None) -> list[dict]:
        """
        Get theme mappings, optionally filtered by theme name.

        Args:
            theme: Optional theme name to filter by

        Returns:
            List of theme records
        """
        query = "SELECT * FROM themes"
        params = []

        if theme:
            query += " WHERE theme = ?"
            params.append(theme)

        query += " ORDER BY theme, wave, ticker"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_theme_for_ticker(self, ticker: str) -> list[dict]:
        """Get all themes associated with a ticker."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM themes WHERE ticker = ? ORDER BY theme, wave",
                (ticker.upper(),),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_theme_summary(self) -> list[dict]:
        """Get summary of themes with stock counts."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT theme, wave, COUNT(*) as stock_count,
                       GROUP_CONCAT(ticker) as tickers
                FROM themes
                GROUP BY theme, wave
                ORDER BY theme, wave
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_theme(self, ticker: str, theme: str, wave: int = 1) -> int:
        """Delete a specific theme mapping."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM themes WHERE ticker = ? AND theme = ? AND wave = ?",
                (ticker.upper(), theme, wave),
            )
            return cursor.rowcount

    def clear_themes(self) -> int:
        """Clear all themes. Returns number of rows deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM themes")
            return cursor.rowcount

    # =========================================================================
    # Research Run Methods
    # =========================================================================

    def start_research_run(
        self,
        run_id: str,
        run_type: str,
        time_window_start: str | None = None,
        time_window_end: str | None = None,
        parameters: dict | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Start a new research run.

        Args:
            run_id: Unique identifier for the run (e.g., 'phase2_2025-01-01')
            run_type: Type of research (e.g., 'phase1', 'phase2', 'criteria_analysis')
            time_window_start: Start date for data window
            time_window_end: End date for data window
            parameters: Optional dict of parameters used
            notes: Optional notes

        Returns:
            The run_id
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO research_runs
                (id, run_type, time_window_start, time_window_end, parameters, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_type,
                    time_window_start,
                    time_window_end,
                    json.dumps(parameters) if parameters else None,
                    notes,
                ),
            )
            logger.info("Started research run", run_id=run_id, run_type=run_type)
            return run_id

    def get_research_run(self, run_id: str) -> dict | None:
        """Get a specific research run."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row:
                d = dict(row)
                if d.get("parameters"):
                    d["parameters"] = json.loads(d["parameters"])
                return d
            return None

    def get_research_runs(
        self,
        run_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Get research runs with optional filters."""
        query = "SELECT * FROM research_runs"
        params = []

        if run_type:
            query += " WHERE run_type = ?"
            params.append(run_type)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get("parameters"):
                    d["parameters"] = json.loads(d["parameters"])
                results.append(d)
            return results

    # =========================================================================
    # Research Findings Methods
    # =========================================================================

    def add_finding(
        self,
        run_id: str,
        finding_type: str,
        finding_key: str,
        metric_name: str,
        metric_value: float | None,
        sample_size: int | None = None,
        time_window_start: str | None = None,
        time_window_end: str | None = None,
        parameters: dict | None = None,
    ) -> int:
        """
        Add a research finding.

        Args:
            run_id: ID of the research run
            finding_type: Category (e.g., 'criteria_lift', 'theme_performance', 'timing')
            finding_key: Specific item (e.g., 'drawdown_85', 'crypto_wave1')
            metric_name: What was measured (e.g., 'avg_gain', 'count', 'lift')
            metric_value: The computed value
            sample_size: Number of observations
            time_window_start: Start of data window
            time_window_end: End of data window
            parameters: Optional parameters used

        Returns:
            The ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO research_findings
                (run_id, finding_type, finding_key, metric_name, metric_value,
                 sample_size, time_window_start, time_window_end, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    finding_type,
                    finding_key,
                    metric_name,
                    metric_value,
                    sample_size,
                    time_window_start,
                    time_window_end,
                    json.dumps(parameters) if parameters else None,
                ),
            )
            return cursor.lastrowid

    def add_findings_bulk(self, findings: list[dict]) -> int:
        """
        Add multiple findings at once.

        Args:
            findings: List of finding dicts

        Returns:
            Number of rows inserted
        """
        with self._get_connection() as conn:
            prepared = []
            for f in findings:
                prepared.append({
                    "run_id": f["run_id"],
                    "finding_type": f["finding_type"],
                    "finding_key": f["finding_key"],
                    "metric_name": f["metric_name"],
                    "metric_value": f.get("metric_value"),
                    "sample_size": f.get("sample_size"),
                    "time_window_start": f.get("time_window_start"),
                    "time_window_end": f.get("time_window_end"),
                    "parameters": json.dumps(f["parameters"]) if f.get("parameters") else None,
                })
            cursor = conn.executemany(
                """
                INSERT INTO research_findings
                (run_id, finding_type, finding_key, metric_name, metric_value,
                 sample_size, time_window_start, time_window_end, parameters)
                VALUES (:run_id, :finding_type, :finding_key, :metric_name, :metric_value,
                        :sample_size, :time_window_start, :time_window_end, :parameters)
                """,
                prepared,
            )
            return cursor.rowcount

    def get_findings(
        self,
        run_id: str | None = None,
        finding_type: str | None = None,
        finding_key: str | None = None,
    ) -> list[dict]:
        """Get findings with optional filters."""
        query = "SELECT * FROM research_findings WHERE 1=1"
        params = []

        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        if finding_type:
            query += " AND finding_type = ?"
            params.append(finding_type)

        if finding_key:
            query += " AND finding_key = ?"
            params.append(finding_key)

        query += " ORDER BY finding_type, finding_key, metric_name"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get("parameters"):
                    d["parameters"] = json.loads(d["parameters"])
                results.append(d)
            return results

    def compare_findings(
        self,
        run_id_1: str,
        run_id_2: str,
        finding_type: str | None = None,
    ) -> list[dict]:
        """
        Compare findings between two research runs.

        Returns findings that exist in both runs with their values side-by-side.
        """
        query = """
            SELECT
                f1.finding_type,
                f1.finding_key,
                f1.metric_name,
                f1.metric_value as value_1,
                f2.metric_value as value_2,
                f1.sample_size as n_1,
                f2.sample_size as n_2,
                CASE
                    WHEN f1.metric_value IS NULL OR f1.metric_value = 0 THEN NULL
                    ELSE ROUND((f2.metric_value - f1.metric_value) / f1.metric_value * 100, 2)
                END as pct_change
            FROM research_findings f1
            JOIN research_findings f2
                ON f1.finding_type = f2.finding_type
                AND f1.finding_key = f2.finding_key
                AND f1.metric_name = f2.metric_name
            WHERE f1.run_id = ? AND f2.run_id = ?
        """
        params = [run_id_1, run_id_2]

        if finding_type:
            query += " AND f1.finding_type = ?"
            params.append(finding_type)

        query += " ORDER BY f1.finding_type, f1.finding_key, f1.metric_name"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def clear_findings(self, run_id: str | None = None) -> int:
        """Clear findings, optionally for a specific run."""
        with self._get_connection() as conn:
            if run_id:
                cursor = conn.execute(
                    "DELETE FROM research_findings WHERE run_id = ?", (run_id,)
                )
            else:
                cursor = conn.execute("DELETE FROM research_findings")
            return cursor.rowcount

    # =========================================================================
    # Watchlist Methods
    # =========================================================================

    def add_to_watchlist(
        self,
        ticker: str,
        theme: str | None = None,
        setup_score: int | None = None,
        drawdown: float | None = None,
        days_declining: int | None = None,
        vol_ratio: float | None = None,
        price_at_add: float | None = None,
        notes: str | None = None,
    ) -> int:
        """
        Add a ticker to the watchlist.

        Args:
            ticker: Stock ticker symbol
            theme: Optional theme classification
            setup_score: Calculated setup score
            drawdown: Current drawdown from high
            days_declining: Days since all-time high
            vol_ratio: Volume ratio vs average
            price_at_add: Price when added
            notes: Optional notes

        Returns:
            The ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO watchlist
                (ticker, theme, setup_score, drawdown, days_declining,
                 vol_ratio, price_at_add, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker.upper(),
                    theme,
                    setup_score,
                    drawdown,
                    days_declining,
                    vol_ratio,
                    price_at_add,
                    notes,
                ),
            )
            logger.info("Added to watchlist", ticker=ticker)
            return cursor.lastrowid

    def get_watchlist(
        self,
        status: str | None = None,
        theme: str | None = None,
        min_score: int | None = None,
    ) -> list[dict]:
        """Get watchlist with optional filters."""
        query = "SELECT * FROM watchlist WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if theme:
            query += " AND theme = ?"
            params.append(theme)

        if min_score is not None:
            query += " AND setup_score >= ?"
            params.append(min_score)

        query += " ORDER BY setup_score DESC, added_date DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def update_watchlist_status(
        self,
        ticker: str,
        status: str,
        trigger_date: str | None = None,
        trigger_price: float | None = None,
    ) -> int:
        """
        Update watchlist item status.

        Args:
            ticker: Stock ticker
            status: New status ('watching', 'triggered', 'entered', 'exited', 'removed')
            trigger_date: Date of trigger event
            trigger_price: Price at trigger

        Returns:
            Number of rows updated
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE watchlist
                SET status = ?, trigger_date = ?, trigger_price = ?
                WHERE ticker = ? AND status = 'watching'
                """,
                (status, trigger_date, trigger_price, ticker.upper()),
            )
            return cursor.rowcount

    def remove_from_watchlist(self, ticker: str) -> int:
        """Remove a ticker from the active watchlist."""
        return self.update_watchlist_status(ticker, "removed")

    def get_watchlist_summary(self) -> dict:
        """Get summary statistics for the watchlist."""
        with self._get_connection() as conn:
            # Status breakdown
            status_dist = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM watchlist
                GROUP BY status
                ORDER BY count DESC
                """
            ).fetchall()

            # Theme breakdown for watching status
            theme_dist = conn.execute(
                """
                SELECT theme, COUNT(*) as count, AVG(setup_score) as avg_score
                FROM watchlist
                WHERE status = 'watching' AND theme IS NOT NULL
                GROUP BY theme
                ORDER BY count DESC
                """
            ).fetchall()

            # Score distribution for watching
            score_dist = conn.execute(
                """
                SELECT setup_score, COUNT(*) as count
                FROM watchlist
                WHERE status = 'watching' AND setup_score IS NOT NULL
                GROUP BY setup_score
                ORDER BY setup_score DESC
                """
            ).fetchall()

            return {
                "status_distribution": [dict(row) for row in status_dist],
                "theme_distribution": [dict(row) for row in theme_dist],
                "score_distribution": [dict(row) for row in score_dist],
            }

    def clear_watchlist(self, status: str | None = None) -> int:
        """Clear watchlist, optionally only for a specific status."""
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute(
                    "DELETE FROM watchlist WHERE status = ?", (status,)
                )
            else:
                cursor = conn.execute("DELETE FROM watchlist")
            return cursor.rowcount

    # =========================================================================
    # Statistical Analysis Methods
    # =========================================================================

    def create_analysis_run(
        self,
        run_id: str,
        start_date: str,
        end_date: str,
        min_gain_pct: float,
        universe: str | None = None,
        winners_count: int | None = None,
        total_count: int | None = None,
        parameters: dict | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Create a new statistical analysis run.

        Args:
            run_id: Unique identifier (e.g., 'analysis_2018_2022')
            start_date: Start of analysis period
            end_date: End of analysis period
            min_gain_pct: Minimum gain to qualify as a winner
            universe: Ticker universe used ('all', 'nasdaq', etc.)
            winners_count: Number of winners found
            total_count: Total stocks analyzed
            parameters: Additional parameters as dict
            notes: Optional notes

        Returns:
            The run_id
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO analysis_runs
                (id, start_date, end_date, min_gain_pct, universe,
                 winners_count, total_count, parameters, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    start_date,
                    end_date,
                    min_gain_pct,
                    universe,
                    winners_count,
                    total_count,
                    json.dumps(parameters) if parameters else None,
                    notes,
                ),
            )
            logger.info("Created analysis run", run_id=run_id)
            return run_id

    def get_analysis_run(self, run_id: str) -> dict | None:
        """Get a specific analysis run."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row:
                d = dict(row)
                if d.get("parameters"):
                    d["parameters"] = json.loads(d["parameters"])
                return d
            return None

    def get_analysis_runs(
        self,
        limit: int | None = None,
    ) -> list[dict]:
        """Get all analysis runs, newest first."""
        query = "SELECT * FROM analysis_runs ORDER BY created_at DESC"
        params = []

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get("parameters"):
                    d["parameters"] = json.loads(d["parameters"])
                results.append(d)
            return results

    def update_analysis_run_counts(
        self,
        run_id: str,
        winners_count: int,
        total_count: int,
    ) -> int:
        """Update the counts for an analysis run."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE analysis_runs
                SET winners_count = ?, total_count = ?
                WHERE id = ?
                """,
                (winners_count, total_count, run_id),
            )
            return cursor.rowcount

    def add_analysis_result(
        self,
        run_id: str,
        variable_name: str,
        population: str,
        mean: float | None = None,
        median: float | None = None,
        std_dev: float | None = None,
        min_val: float | None = None,
        max_val: float | None = None,
        p10: float | None = None,
        p25: float | None = None,
        p75: float | None = None,
        p90: float | None = None,
        sample_size: int | None = None,
    ) -> int:
        """
        Add a statistical result for a variable.

        Args:
            run_id: Analysis run ID
            variable_name: Name of variable (e.g., 'drawdown', 'vol_ratio')
            population: 'winners' or 'all'
            mean, median, std_dev: Central tendency and spread
            min_val, max_val: Range
            p10, p25, p75, p90: Percentiles
            sample_size: Number of observations

        Returns:
            ID of inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_results
                (run_id, variable_name, population, mean, median, std_dev,
                 min_val, max_val, p10, p25, p75, p90, sample_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    variable_name,
                    population,
                    mean,
                    median,
                    std_dev,
                    min_val,
                    max_val,
                    p10,
                    p25,
                    p75,
                    p90,
                    sample_size,
                ),
            )
            return cursor.lastrowid

    def add_analysis_results_bulk(self, results: list[dict]) -> int:
        """
        Add multiple analysis results at once.

        Args:
            results: List of dicts with run_id, variable_name, population, and stats

        Returns:
            Number of rows inserted
        """
        with self._get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT INTO analysis_results
                (run_id, variable_name, population, mean, median, std_dev,
                 min_val, max_val, p10, p25, p75, p90, sample_size)
                VALUES (:run_id, :variable_name, :population, :mean, :median, :std_dev,
                        :min_val, :max_val, :p10, :p25, :p75, :p90, :sample_size)
                """,
                results,
            )
            return cursor.rowcount

    def get_analysis_results(
        self,
        run_id: str,
        variable_name: str | None = None,
        population: str | None = None,
    ) -> list[dict]:
        """
        Get analysis results with optional filters.

        Args:
            run_id: Analysis run ID
            variable_name: Optional filter by variable
            population: Optional filter by 'winners' or 'all'

        Returns:
            List of result records
        """
        query = "SELECT * FROM analysis_results WHERE run_id = ?"
        params = [run_id]

        if variable_name:
            query += " AND variable_name = ?"
            params.append(variable_name)

        if population:
            query += " AND population = ?"
            params.append(population)

        query += " ORDER BY variable_name, population"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_analysis_comparison(
        self,
        run_id_1: str,
        run_id_2: str,
        variable_name: str | None = None,
    ) -> list[dict]:
        """
        Compare analysis results between two runs.

        Returns results for both populations (winners, all) side by side.
        """
        query = """
            SELECT
                r1.variable_name,
                r1.population,
                r1.mean as mean_1,
                r2.mean as mean_2,
                r1.median as median_1,
                r2.median as median_2,
                r1.p25 as p25_1,
                r2.p25 as p25_2,
                r1.p75 as p75_1,
                r2.p75 as p75_2,
                r1.sample_size as n_1,
                r2.sample_size as n_2,
                CASE
                    WHEN r1.mean IS NULL OR r1.mean = 0 THEN NULL
                    ELSE ROUND((r2.mean - r1.mean) / ABS(r1.mean) * 100, 2)
                END as mean_pct_change
            FROM analysis_results r1
            JOIN analysis_results r2
                ON r1.variable_name = r2.variable_name
                AND r1.population = r2.population
            WHERE r1.run_id = ? AND r2.run_id = ?
        """
        params = [run_id_1, run_id_2]

        if variable_name:
            query += " AND r1.variable_name = ?"
            params.append(variable_name)

        query += " ORDER BY r1.variable_name, r1.population"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_analysis_lift(self, run_id: str) -> list[dict]:
        """
        Calculate lift (winners vs all) for each variable.

        Lift = winners_mean / all_mean (for positive metrics)
        For negative metrics like drawdown, lift = all_mean / winners_mean
        """
        query = """
            SELECT
                w.variable_name,
                w.mean as winners_mean,
                a.mean as all_mean,
                w.median as winners_median,
                a.median as all_median,
                w.sample_size as winners_n,
                a.sample_size as all_n,
                CASE
                    WHEN a.mean IS NULL OR a.mean = 0 THEN NULL
                    WHEN w.variable_name IN ('drawdown', 'pct_from_sma50', 'pct_from_sma200')
                        THEN ROUND(a.mean / w.mean, 2)
                    ELSE ROUND(w.mean / a.mean, 2)
                END as lift
            FROM analysis_results w
            JOIN analysis_results a
                ON w.variable_name = a.variable_name
            WHERE w.run_id = ? AND a.run_id = ?
                AND w.population = 'winners'
                AND a.population = 'all'
            ORDER BY lift DESC
        """
        with self._get_connection() as conn:
            rows = conn.execute(query, (run_id, run_id)).fetchall()
            return [dict(row) for row in rows]

    def delete_analysis_run(self, run_id: str) -> int:
        """Delete an analysis run and all its results."""
        with self._get_connection() as conn:
            # Delete results first (foreign key)
            conn.execute(
                "DELETE FROM analysis_results WHERE run_id = ?", (run_id,)
            )
            cursor = conn.execute(
                "DELETE FROM analysis_runs WHERE id = ?", (run_id,)
            )
            return cursor.rowcount
