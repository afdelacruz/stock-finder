#!/usr/bin/env python3
"""
Phase 1: Data Inventory Analysis
================================
Understand what data we have before analyzing patterns.

Run: python analysis/scripts/phase1_data_inventory.py
Output: analysis/findings/phase1_data_inventory.md
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = "data/stock_finder.db"
OUTPUT_PATH = "analysis/findings/phase1_data_inventory.md"


def run_query(conn, query: str) -> list[dict]:
    """Run a query and return results as list of dicts."""
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def run_single_value(conn, query: str):
    """Run a query that returns a single value."""
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchone()[0]


def format_table(rows: list[dict], headers: list[str] | None = None) -> str:
    """Format rows as markdown table."""
    if not rows:
        return "*No data*"

    headers = headers or list(rows[0].keys())
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        values = [str(row.get(h, "")) for h in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main():
    conn = sqlite3.connect(DB_PATH)
    findings = []

    findings.append("# Phase 1: Data Inventory")
    findings.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # =========================================================================
    # 1.1 Data Scope
    # =========================================================================
    findings.append("## 1.1 Data Scope\n")

    # Basic counts
    total_scan_results = run_single_value(conn, "SELECT COUNT(*) FROM scan_results")
    unique_tickers = run_single_value(conn, "SELECT COUNT(DISTINCT ticker) FROM scan_results")
    total_scores = run_single_value(conn, "SELECT COUNT(*) FROM neumann_scores")
    scored_tickers = run_single_value(conn, "SELECT COUNT(DISTINCT ticker) FROM neumann_scores")

    findings.append("### Record Counts\n")
    findings.append(f"| Metric | Count |")
    findings.append(f"| --- | --- |")
    findings.append(f"| Total scan results | {total_scan_results:,} |")
    findings.append(f"| Unique tickers (scan) | {unique_tickers:,} |")
    findings.append(f"| Total Neumann scores | {total_scores:,} |")
    findings.append(f"| Unique tickers (scored) | {scored_tickers:,} |")
    findings.append("")

    # Date range
    date_range = run_query(conn, """
        SELECT
            MIN(low_date) as earliest_low,
            MAX(low_date) as latest_low,
            MIN(high_date) as earliest_high,
            MAX(high_date) as latest_high
        FROM scan_results
    """)[0]

    findings.append("### Date Range\n")
    findings.append(f"| Metric | Date |")
    findings.append(f"| --- | --- |")
    findings.append(f"| Earliest ignition (low_date) | {date_range['earliest_low']} |")
    findings.append(f"| Latest ignition (low_date) | {date_range['latest_low']} |")
    findings.append(f"| Earliest peak (high_date) | {date_range['earliest_high']} |")
    findings.append(f"| Latest peak (high_date) | {date_range['latest_high']} |")
    findings.append("")

    # =========================================================================
    # 1.2 Gain Distribution
    # =========================================================================
    findings.append("## 1.2 Gain Distribution\n")

    gain_stats = run_query(conn, """
        SELECT
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 1) as avg_gain,
            ROUND(MIN(gain_pct), 1) as min_gain,
            ROUND(MAX(gain_pct), 1) as max_gain,
            ROUND(AVG(gain_pct), 1) as median_approx
        FROM neumann_scores
        WHERE gain_pct < 50000  -- Exclude extreme outliers
    """)[0]

    findings.append(f"*Note: Excluding extreme outliers (gain > 50,000%)*\n")
    findings.append(f"| Stat | Value |")
    findings.append(f"| --- | --- |")
    findings.append(f"| Count | {gain_stats['count']:,} |")
    findings.append(f"| Average gain | {gain_stats['avg_gain']:,.1f}% |")
    findings.append(f"| Min gain | {gain_stats['min_gain']:,.1f}% |")
    findings.append(f"| Max gain | {gain_stats['max_gain']:,.1f}% |")
    findings.append("")

    # Gain buckets
    gain_buckets = run_query(conn, """
        SELECT
            CASE
                WHEN gain_pct < 500 THEN '< 500%'
                WHEN gain_pct < 1000 THEN '500-1000%'
                WHEN gain_pct < 2000 THEN '1000-2000%'
                WHEN gain_pct < 5000 THEN '2000-5000%'
                ELSE '5000%+'
            END as gain_bucket,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain
        FROM neumann_scores
        WHERE gain_pct < 50000
        GROUP BY gain_bucket
        ORDER BY MIN(gain_pct)
    """)

    findings.append("### Gain Distribution by Bucket\n")
    findings.append(format_table(gain_buckets, ["gain_bucket", "count", "avg_gain"]))
    findings.append("")

    # =========================================================================
    # 1.3 Neumann Score Distribution
    # =========================================================================
    findings.append("## 1.3 Neumann Score Distribution\n")

    score_dist = run_query(conn, """
        SELECT
            score,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days_to_peak
        FROM neumann_scores
        WHERE gain_pct < 50000
        GROUP BY score
        ORDER BY score DESC
    """)

    findings.append(format_table(score_dist, ["score", "count", "avg_gain", "avg_days_to_peak"]))
    findings.append("")

    # =========================================================================
    # 1.4 Available Fields for Analysis
    # =========================================================================
    findings.append("## 1.4 Available Fields for Analysis\n")

    # Check data completeness in neumann_scores
    field_completeness = run_query(conn, """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN drawdown IS NOT NULL THEN 1 ELSE 0 END) as has_drawdown,
            SUM(CASE WHEN days_since_high IS NOT NULL THEN 1 ELSE 0 END) as has_days_since_high,
            SUM(CASE WHEN range_position IS NOT NULL THEN 1 ELSE 0 END) as has_range_position,
            SUM(CASE WHEN pct_from_sma50 IS NOT NULL THEN 1 ELSE 0 END) as has_sma50,
            SUM(CASE WHEN pct_from_sma200 IS NOT NULL THEN 1 ELSE 0 END) as has_sma200,
            SUM(CASE WHEN vol_ratio IS NOT NULL THEN 1 ELSE 0 END) as has_vol_ratio,
            SUM(CASE WHEN market_cap_estimate IS NOT NULL THEN 1 ELSE 0 END) as has_market_cap
        FROM neumann_scores
    """)[0]

    total = field_completeness['total']
    findings.append("### Field Completeness\n")
    findings.append("| Field | Records | % Complete |")
    findings.append("| --- | --- | --- |")
    for field in ['drawdown', 'days_since_high', 'range_position', 'sma50', 'sma200', 'vol_ratio', 'market_cap']:
        key = f'has_{field}'
        if key in field_completeness:
            count = field_completeness[key]
            pct = (count / total * 100) if total > 0 else 0
            findings.append(f"| {field} | {count:,} | {pct:.1f}% |")
    findings.append("")

    # =========================================================================
    # 1.5 Time to Peak Distribution
    # =========================================================================
    findings.append("## 1.5 Time to Peak Distribution\n")

    time_buckets = run_query(conn, """
        SELECT
            CASE
                WHEN days_to_peak < 30 THEN '< 1 month'
                WHEN days_to_peak < 90 THEN '1-3 months'
                WHEN days_to_peak < 180 THEN '3-6 months'
                WHEN days_to_peak < 365 THEN '6-12 months'
                ELSE '12+ months'
            END as time_bucket,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(score), 1) as avg_score
        FROM neumann_scores
        WHERE gain_pct < 50000
        GROUP BY time_bucket
        ORDER BY MIN(days_to_peak)
    """)

    findings.append(format_table(time_buckets, ["time_bucket", "count", "avg_gain", "avg_score"]))
    findings.append("")

    # =========================================================================
    # 1.6 Year Distribution
    # =========================================================================
    findings.append("## 1.6 Ignition Year Distribution\n")

    year_dist = run_query(conn, """
        SELECT
            SUBSTR(sr.low_date, 1, 4) as year,
            COUNT(*) as count,
            ROUND(AVG(ns.gain_pct), 0) as avg_gain,
            ROUND(AVG(ns.score), 1) as avg_score
        FROM neumann_scores ns
        JOIN scan_results sr ON ns.scan_result_id = sr.id
        WHERE ns.gain_pct < 50000
        GROUP BY year
        ORDER BY year
    """)

    findings.append(format_table(year_dist, ["year", "count", "avg_gain", "avg_score"]))
    findings.append("")

    # =========================================================================
    # Summary
    # =========================================================================
    findings.append("## Summary\n")
    findings.append("### Key Observations\n")
    findings.append("1. **Data scope:** [To be filled after review]")
    findings.append("2. **Gain distribution:** [To be filled after review]")
    findings.append("3. **Score correlation:** [To be filled after review]")
    findings.append("4. **Data quality:** [To be filled after review]")
    findings.append("")
    findings.append("### Questions for Phase 2\n")
    findings.append("1. [To be filled after review]")
    findings.append("2. [To be filled after review]")
    findings.append("")

    # Write output
    output_path = Path(OUTPUT_PATH)
    output_path.write_text("\n".join(findings))
    print(f"Phase 1 analysis complete. Output: {OUTPUT_PATH}")

    conn.close()

    # Also print to stdout for immediate viewing
    print("\n" + "="*60)
    print("\n".join(findings))


if __name__ == "__main__":
    main()
