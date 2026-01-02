"""Reusable research queries for stock analysis."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = Path("data/stock_finder.db")


@dataclass
class QueryResult:
    """Result from a research query."""
    finding_type: str
    finding_key: str
    metrics: dict[str, float | int | None]
    sample_size: int


class ResearchQueries:
    """
    Collection of reusable research queries.

    Each method returns QueryResult objects that can be stored in the database.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Criteria Lift Analysis
    # =========================================================================

    def criteria_lift(self, max_gain: float = 50000) -> list[QueryResult]:
        """
        Calculate lift for each scoring criteria.

        Lift = avg_gain_when_passed / avg_gain_when_failed

        Args:
            max_gain: Exclude outliers above this gain %

        Returns:
            List of QueryResult for each criteria
        """
        criteria = [
            ("drawdown_50", "drawdown <= -0.50"),
            ("drawdown_85", "drawdown <= -0.85"),
            ("extended_decline_90d", "days_since_high >= 90"),
            ("extended_decline_180d", "days_since_high >= 180"),
            ("extended_decline_365d", "days_since_high >= 365"),
            ("near_lows", "range_position <= 0.10"),
            ("below_sma50", "pct_from_sma50 < 0"),
            ("below_sma200", "pct_from_sma200 < 0"),
            ("vol_exhaustion_1x", "vol_ratio < 1.0"),
            ("vol_exhaustion_075x", "vol_ratio < 0.75"),
            ("vol_exhaustion_05x", "vol_ratio < 0.5"),
        ]

        results = []
        conn = self._connect()

        for key, condition in criteria:
            row = conn.execute(f"""
                SELECT
                    AVG(CASE WHEN {condition} THEN gain_pct END) as avg_when_pass,
                    AVG(CASE WHEN NOT ({condition}) THEN gain_pct END) as avg_when_fail,
                    SUM(CASE WHEN {condition} THEN 1 ELSE 0 END) as count_pass,
                    SUM(CASE WHEN NOT ({condition}) THEN 1 ELSE 0 END) as count_fail,
                    COUNT(*) as total
                FROM neumann_scores
                WHERE gain_pct < ? AND {condition.split()[0]} IS NOT NULL
            """, (max_gain,)).fetchone()

            if row and row["avg_when_pass"] and row["avg_when_fail"]:
                lift = row["avg_when_pass"] / row["avg_when_fail"]
                results.append(QueryResult(
                    finding_type="criteria_lift",
                    finding_key=key,
                    metrics={
                        "avg_when_pass": round(row["avg_when_pass"], 1),
                        "avg_when_fail": round(row["avg_when_fail"], 1),
                        "lift": round(lift, 2),
                        "count_pass": row["count_pass"],
                        "count_fail": row["count_fail"],
                    },
                    sample_size=row["total"],
                ))

        conn.close()
        return results

    # =========================================================================
    # Setup Quality Analysis
    # =========================================================================

    def setup_quality_tiers(self, max_gain: float = 50000) -> list[QueryResult]:
        """
        Analyze performance by setup quality tier.

        Tiers:
        - Ideal: deep drawdown + long decline + low volume
        - Good (deep+vol): deep drawdown + low volume
        - Good (deep+long): deep drawdown + long decline
        - Moderate: deep drawdown only
        - Weak: no deep drawdown

        Returns:
            List of QueryResult for each tier
        """
        query = """
            SELECT
                CASE
                    WHEN drawdown <= -0.85 AND days_since_high >= 365 AND vol_ratio < 0.75
                        THEN 'ideal'
                    WHEN drawdown <= -0.85 AND vol_ratio < 0.75
                        THEN 'good_deep_vol'
                    WHEN drawdown <= -0.85 AND days_since_high >= 365
                        THEN 'good_deep_long'
                    WHEN drawdown <= -0.85
                        THEN 'moderate'
                    ELSE 'weak'
                END as tier,
                COUNT(*) as count,
                ROUND(AVG(gain_pct), 0) as avg_gain,
                ROUND(AVG(days_to_peak), 0) as avg_days,
                ROUND(MIN(gain_pct), 0) as min_gain,
                ROUND(MAX(gain_pct), 0) as max_gain
            FROM neumann_scores
            WHERE gain_pct < ? AND drawdown IS NOT NULL
            GROUP BY tier
            ORDER BY avg_gain DESC
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(QueryResult(
                finding_type="setup_quality",
                finding_key=row["tier"],
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_days": row["avg_days"],
                    "min_gain": row["min_gain"],
                    "max_gain": row["max_gain"],
                },
                sample_size=row["count"],
            ))

        return results

    # =========================================================================
    # Theme Performance Analysis
    # =========================================================================

    def theme_performance(self, max_gain: float = 50000) -> list[QueryResult]:
        """
        Analyze performance by theme.

        Returns:
            List of QueryResult for each theme/wave
        """
        query = """
            SELECT
                t.theme,
                t.wave,
                COUNT(*) as count,
                ROUND(AVG(ns.gain_pct), 0) as avg_gain,
                ROUND(AVG(ns.days_to_peak), 0) as avg_days,
                MAX(ns.ticker || ': ' || CAST(ROUND(ns.gain_pct, 0) AS TEXT) || '%') as top_performer
            FROM themes t
            JOIN neumann_scores ns ON t.ticker = ns.ticker
            WHERE ns.gain_pct < ?
            GROUP BY t.theme, t.wave
            ORDER BY avg_gain DESC
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            key = f"{row['theme'].lower()}_wave{row['wave']}"
            results.append(QueryResult(
                finding_type="theme_performance",
                finding_key=key,
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_days": row["avg_days"],
                    "top_performer": row["top_performer"],
                },
                sample_size=row["count"],
            ))

        return results

    def themed_vs_unthemed(self, max_gain: float = 50000) -> list[QueryResult]:
        """Compare themed stocks vs unthemed."""
        query = """
            SELECT
                CASE WHEN t.ticker IS NOT NULL THEN 'themed' ELSE 'unthemed' END as category,
                COUNT(*) as count,
                ROUND(AVG(ns.gain_pct), 0) as avg_gain,
                ROUND(AVG(ns.days_to_peak), 0) as avg_days
            FROM neumann_scores ns
            LEFT JOIN themes t ON ns.ticker = t.ticker
            WHERE ns.gain_pct < ?
            GROUP BY category
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(QueryResult(
                finding_type="theme_comparison",
                finding_key=row["category"],
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_days": row["avg_days"],
                },
                sample_size=row["count"],
            ))

        return results

    # =========================================================================
    # Timing Analysis
    # =========================================================================

    def timing_by_month(self, max_gain: float = 50000) -> list[QueryResult]:
        """
        Analyze ignition timing by month.

        Returns performance metrics for each month of the year.
        """
        query = """
            SELECT
                CAST(strftime('%m', sr.low_date) AS INTEGER) as month,
                COUNT(*) as count,
                ROUND(AVG(ns.gain_pct), 0) as avg_gain,
                ROUND(AVG(ns.days_to_peak), 0) as avg_days
            FROM neumann_scores ns
            JOIN scan_results sr ON ns.scan_result_id = sr.id
            WHERE ns.gain_pct < ? AND sr.low_date IS NOT NULL
            GROUP BY month
            ORDER BY month
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        month_names = [
            "", "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        ]

        results = []
        for row in rows:
            month_num = row["month"]
            if 1 <= month_num <= 12:
                results.append(QueryResult(
                    finding_type="timing_month",
                    finding_key=month_names[month_num],
                    metrics={
                        "avg_gain": row["avg_gain"],
                        "avg_days": row["avg_days"],
                    },
                    sample_size=row["count"],
                ))

        return results

    def timing_by_year(self, max_gain: float = 50000) -> list[QueryResult]:
        """Analyze ignition timing by year."""
        query = """
            SELECT
                strftime('%Y', sr.low_date) as year,
                COUNT(*) as count,
                ROUND(AVG(ns.gain_pct), 0) as avg_gain,
                ROUND(AVG(ns.days_to_peak), 0) as avg_days
            FROM neumann_scores ns
            JOIN scan_results sr ON ns.scan_result_id = sr.id
            WHERE ns.gain_pct < ? AND sr.low_date IS NOT NULL
            GROUP BY year
            ORDER BY year
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            if row["year"]:
                results.append(QueryResult(
                    finding_type="timing_year",
                    finding_key=row["year"],
                    metrics={
                        "avg_gain": row["avg_gain"],
                        "avg_days": row["avg_days"],
                    },
                    sample_size=row["count"],
                ))

        return results

    # =========================================================================
    # Score Distribution Analysis
    # =========================================================================

    def score_distribution(self, max_gain: float = 50000) -> list[QueryResult]:
        """Analyze performance by current Neumann score."""
        query = """
            SELECT
                score,
                COUNT(*) as count,
                ROUND(AVG(gain_pct), 0) as avg_gain,
                ROUND(AVG(days_to_peak), 0) as avg_days
            FROM neumann_scores
            WHERE gain_pct < ?
            GROUP BY score
            ORDER BY score DESC
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(QueryResult(
                finding_type="score_distribution",
                finding_key=f"score_{row['score']}",
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_days": row["avg_days"],
                },
                sample_size=row["count"],
            ))

        return results

    def simulated_score_distribution(self, max_gain: float = 50000) -> list[QueryResult]:
        """
        Analyze performance by proposed weighted score.

        Weighted score formula:
        - Drawdown: 0-3 points (3 for 85%+, 2 for 50-85%, 0 otherwise)
        - Decline: 0-2 points (2 for 12mo+, 1 for 6-12mo, 0 otherwise)
        - Volume: 0-2 points (2 for <0.75x, 0 otherwise)
        """
        query = """
            SELECT
                (CASE WHEN drawdown <= -0.85 THEN 3
                      WHEN drawdown <= -0.50 THEN 2
                      ELSE 0 END) +
                (CASE WHEN days_since_high >= 365 THEN 2
                      WHEN days_since_high >= 180 THEN 1
                      ELSE 0 END) +
                (CASE WHEN vol_ratio < 0.75 THEN 2 ELSE 0 END) as sim_score,
                COUNT(*) as count,
                ROUND(AVG(gain_pct), 0) as avg_gain,
                ROUND(AVG(days_to_peak), 0) as avg_days
            FROM neumann_scores
            WHERE gain_pct < ? AND drawdown IS NOT NULL AND vol_ratio IS NOT NULL
            GROUP BY sim_score
            ORDER BY sim_score DESC
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(QueryResult(
                finding_type="simulated_score",
                finding_key=f"score_{row['sim_score']}",
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_days": row["avg_days"],
                },
                sample_size=row["count"],
            ))

        return results

    # =========================================================================
    # Volume Dynamics
    # =========================================================================

    def volume_profile(self, max_gain: float = 50000) -> list[QueryResult]:
        """Analyze performance by volume ratio buckets."""
        query = """
            SELECT
                CASE
                    WHEN vol_ratio < 0.5 THEN 'very_low'
                    WHEN vol_ratio < 0.75 THEN 'low'
                    WHEN vol_ratio < 1.0 THEN 'below_avg'
                    WHEN vol_ratio < 1.5 THEN 'normal'
                    ELSE 'high'
                END as vol_bucket,
                COUNT(*) as count,
                ROUND(AVG(gain_pct), 0) as avg_gain,
                ROUND(AVG(days_to_peak), 0) as avg_days,
                ROUND(AVG(gain_pct) / NULLIF(AVG(days_to_peak), 0), 2) as velocity
            FROM neumann_scores
            WHERE gain_pct < ? AND vol_ratio IS NOT NULL
            GROUP BY vol_bucket
            ORDER BY MIN(vol_ratio)
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(QueryResult(
                finding_type="volume_profile",
                finding_key=row["vol_bucket"],
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_days": row["avg_days"],
                    "velocity": row["velocity"],
                },
                sample_size=row["count"],
            ))

        return results

    # =========================================================================
    # Move Speed Analysis
    # =========================================================================

    def move_speed_profile(self, max_gain: float = 50000) -> list[QueryResult]:
        """Analyze characteristics by move speed."""
        query = """
            SELECT
                CASE
                    WHEN days_to_peak < 30 THEN 'fast'
                    WHEN days_to_peak < 90 THEN 'medium'
                    WHEN days_to_peak < 180 THEN 'moderate'
                    WHEN days_to_peak < 365 THEN 'slow'
                    ELSE 'very_slow'
                END as speed,
                COUNT(*) as count,
                ROUND(AVG(gain_pct), 0) as avg_gain,
                ROUND(AVG(drawdown), 2) as avg_drawdown,
                ROUND(AVG(vol_ratio), 2) as avg_vol_ratio
            FROM neumann_scores
            WHERE gain_pct < ? AND days_to_peak IS NOT NULL
            GROUP BY speed
            ORDER BY MIN(days_to_peak)
        """

        conn = self._connect()
        rows = conn.execute(query, (max_gain,)).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(QueryResult(
                finding_type="move_speed",
                finding_key=row["speed"],
                metrics={
                    "avg_gain": row["avg_gain"],
                    "avg_drawdown": row["avg_drawdown"],
                    "avg_vol_ratio": row["avg_vol_ratio"],
                },
                sample_size=row["count"],
            ))

        return results

    # =========================================================================
    # Summary Statistics
    # =========================================================================

    def summary_stats(self, max_gain: float = 50000) -> list[QueryResult]:
        """Get overall summary statistics."""
        query = """
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT ticker) as unique_tickers,
                ROUND(AVG(gain_pct), 0) as avg_gain,
                ROUND(AVG(days_to_peak), 0) as avg_days,
                ROUND(AVG(score), 1) as avg_score,
                MIN(gain_pct) as min_gain,
                MAX(gain_pct) as max_gain
            FROM neumann_scores
            WHERE gain_pct < ?
        """

        conn = self._connect()
        row = conn.execute(query, (max_gain,)).fetchone()
        conn.close()

        return [QueryResult(
            finding_type="summary",
            finding_key="overall",
            metrics={
                "unique_tickers": row["unique_tickers"],
                "avg_gain": row["avg_gain"],
                "avg_days": row["avg_days"],
                "avg_score": row["avg_score"],
                "min_gain": row["min_gain"],
                "max_gain": row["max_gain"],
            },
            sample_size=row["total_records"],
        )]
