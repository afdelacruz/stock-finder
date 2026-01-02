#!/usr/bin/env python3
"""
Phase 2: Single Variable Analysis
==================================
Investigate patterns in individual variables and answer Phase 1 questions.

Questions to answer:
1. Why do Score 0 stocks have high gains?
2. What drives fast movers (< 1 month)?
3. Is vol_ratio correlated with speed/gain?
4. Do certain drawdown levels predict better outcomes?

Run: python analysis/scripts/phase2_single_variable.py
Output: analysis/findings/phase2_single_variable.md
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = "data/stock_finder.db"
OUTPUT_PATH = "analysis/findings/phase2_single_variable.md"


def run_query(conn, query: str) -> list[dict]:
    """Run a query and return results as list of dicts."""
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


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

    findings.append("# Phase 2: Single Variable Analysis")
    findings.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # =========================================================================
    # 2.1 Score 0 Investigation
    # =========================================================================
    findings.append("## 2.1 Score 0 Investigation\n")
    findings.append("**Question:** Why do Score 0 stocks have high gains (1,383%) and fast moves (375 days)?\n")

    # What criteria are Score 0 stocks failing?
    score_0_criteria = run_query(conn, """
        SELECT
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            ROUND(AVG(days_since_high), 0) as avg_days_since_high,
            ROUND(AVG(range_position), 2) as avg_range_position,
            ROUND(AVG(pct_from_sma50), 2) as avg_pct_sma50,
            ROUND(AVG(pct_from_sma200), 2) as avg_pct_sma200,
            ROUND(AVG(vol_ratio), 2) as avg_vol_ratio,
            COUNT(*) as count
        FROM neumann_scores
        WHERE score = 0 AND gain_pct < 50000
    """)

    score_high_criteria = run_query(conn, """
        SELECT
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            ROUND(AVG(days_since_high), 0) as avg_days_since_high,
            ROUND(AVG(range_position), 2) as avg_range_position,
            ROUND(AVG(pct_from_sma50), 2) as avg_pct_sma50,
            ROUND(AVG(pct_from_sma200), 2) as avg_pct_sma200,
            ROUND(AVG(vol_ratio), 2) as avg_vol_ratio,
            COUNT(*) as count
        FROM neumann_scores
        WHERE score >= 6 AND gain_pct < 50000
    """)

    findings.append("### Comparison: Score 0 vs Score 6+\n")
    findings.append("| Metric | Score 0 | Score 6+ | Interpretation |")
    findings.append("| --- | --- | --- | --- |")

    s0 = score_0_criteria[0] if score_0_criteria else {}
    s6 = score_high_criteria[0] if score_high_criteria else {}

    findings.append(f"| Count | {s0.get('count', 'N/A')} | {s6.get('count', 'N/A')} | |")
    findings.append(f"| Avg Drawdown | {s0.get('avg_drawdown', 'N/A')} | {s6.get('avg_drawdown', 'N/A')} | Lower = less beaten down |")
    findings.append(f"| Avg Days Since High | {s0.get('avg_days_since_high', 'N/A')} | {s6.get('avg_days_since_high', 'N/A')} | Lower = shorter decline |")
    findings.append(f"| Avg Range Position | {s0.get('avg_range_position', 'N/A')} | {s6.get('avg_range_position', 'N/A')} | Higher = not near lows |")
    findings.append(f"| Avg % from SMA50 | {s0.get('avg_pct_sma50', 'N/A')} | {s6.get('avg_pct_sma50', 'N/A')} | Higher = above SMA |")
    findings.append(f"| Avg Vol Ratio | {s0.get('avg_vol_ratio', 'N/A')} | {s6.get('avg_vol_ratio', 'N/A')} | Higher = more volume |")
    findings.append("")

    # Check for NULL values in Score 0
    score_0_nulls = run_query(conn, """
        SELECT
            SUM(CASE WHEN drawdown IS NULL THEN 1 ELSE 0 END) as null_drawdown,
            SUM(CASE WHEN days_since_high IS NULL THEN 1 ELSE 0 END) as null_days,
            SUM(CASE WHEN range_position IS NULL THEN 1 ELSE 0 END) as null_range,
            COUNT(*) as total
        FROM neumann_scores
        WHERE score = 0
    """)[0]

    findings.append("### Score 0 Data Completeness\n")
    findings.append(f"| Field | NULL Count | % NULL |")
    findings.append(f"| --- | --- | --- |")
    total = score_0_nulls['total']
    findings.append(f"| drawdown | {score_0_nulls['null_drawdown']} | {score_0_nulls['null_drawdown']/total*100:.1f}% |")
    findings.append(f"| days_since_high | {score_0_nulls['null_days']} | {score_0_nulls['null_days']/total*100:.1f}% |")
    findings.append(f"| range_position | {score_0_nulls['null_range']} | {score_0_nulls['null_range']/total*100:.1f}% |")
    findings.append("")

    # =========================================================================
    # 2.2 Fast Movers Analysis
    # =========================================================================
    findings.append("## 2.2 Fast Movers Analysis\n")
    findings.append("**Question:** What drives fast movers (< 1 month to peak)?\n")

    fast_vs_slow = run_query(conn, """
        SELECT
            CASE
                WHEN days_to_peak < 30 THEN 'Fast (< 1mo)'
                WHEN days_to_peak < 180 THEN 'Medium (1-6mo)'
                ELSE 'Slow (6mo+)'
            END as speed,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(score), 1) as avg_score,
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            ROUND(AVG(vol_ratio), 2) as avg_vol_ratio,
            ROUND(AVG(days_since_high), 0) as avg_days_decline
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL
        GROUP BY speed
        ORDER BY MIN(days_to_peak)
    """)

    findings.append("### Fast vs Medium vs Slow Movers\n")
    findings.append(format_table(fast_vs_slow))
    findings.append("")

    # What do fast movers look like?
    findings.append("### Fast Mover Characteristics\n")
    fast_detail = run_query(conn, """
        SELECT
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            ROUND(MIN(drawdown), 2) as min_drawdown,
            ROUND(MAX(drawdown), 2) as max_drawdown,
            ROUND(AVG(vol_ratio), 2) as avg_vol_ratio,
            ROUND(AVG(days_since_high), 0) as avg_days_decline,
            ROUND(AVG(range_position), 2) as avg_range_pos
        FROM neumann_scores
        WHERE days_to_peak < 30 AND gain_pct < 50000 AND drawdown IS NOT NULL
    """)[0]

    findings.append(f"Fast movers (< 1 month to peak):")
    findings.append(f"- Average drawdown: {fast_detail['avg_drawdown']} (range: {fast_detail['min_drawdown']} to {fast_detail['max_drawdown']})")
    findings.append(f"- Average volume ratio: {fast_detail['avg_vol_ratio']}")
    findings.append(f"- Average days in decline: {fast_detail['avg_days_decline']}")
    findings.append(f"- Average range position: {fast_detail['avg_range_pos']}")
    findings.append("")

    # =========================================================================
    # 2.3 Volume Ratio Analysis
    # =========================================================================
    findings.append("## 2.3 Volume Ratio Analysis\n")
    findings.append("**Question:** Is vol_ratio (volume exhaustion) correlated with speed/gain?\n")

    vol_buckets = run_query(conn, """
        SELECT
            CASE
                WHEN vol_ratio < 0.5 THEN '< 0.5 (very low)'
                WHEN vol_ratio < 0.75 THEN '0.5-0.75 (low)'
                WHEN vol_ratio < 1.0 THEN '0.75-1.0 (below avg)'
                WHEN vol_ratio < 1.5 THEN '1.0-1.5 (above avg)'
                ELSE '1.5+ (high)'
            END as vol_bucket,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days_to_peak,
            ROUND(AVG(score), 1) as avg_score
        FROM neumann_scores
        WHERE gain_pct < 50000 AND vol_ratio IS NOT NULL
        GROUP BY vol_bucket
        ORDER BY MIN(vol_ratio)
    """)

    findings.append("### Volume Ratio vs Outcomes\n")
    findings.append(format_table(vol_buckets))
    findings.append("")

    # Volume exhaustion theory: does LOW volume predict bigger/faster moves?
    findings.append("### Volume Exhaustion Hypothesis\n")
    findings.append("*Theory: Low volume at ignition = sellers exhausted = bigger bounce*\n")

    vol_low = run_query(conn, "SELECT AVG(gain_pct) as gain FROM neumann_scores WHERE vol_ratio < 0.75 AND gain_pct < 50000")[0]
    vol_high = run_query(conn, "SELECT AVG(gain_pct) as gain FROM neumann_scores WHERE vol_ratio >= 1.0 AND gain_pct < 50000")[0]

    if vol_low['gain'] and vol_high['gain']:
        lift = vol_low['gain'] / vol_high['gain']
        findings.append(f"- Low volume (< 0.75) avg gain: {vol_low['gain']:.0f}%")
        findings.append(f"- High volume (>= 1.0) avg gain: {vol_high['gain']:.0f}%")
        findings.append(f"- **Lift: {lift:.2f}x**")
    findings.append("")

    # =========================================================================
    # 2.4 Drawdown Analysis
    # =========================================================================
    findings.append("## 2.4 Drawdown Analysis\n")
    findings.append("**Question:** Do certain drawdown levels predict better outcomes?\n")

    drawdown_buckets = run_query(conn, """
        SELECT
            CASE
                WHEN drawdown > -0.3 THEN '< 30% down'
                WHEN drawdown > -0.5 THEN '30-50% down'
                WHEN drawdown > -0.7 THEN '50-70% down'
                WHEN drawdown > -0.85 THEN '70-85% down'
                ELSE '85%+ down'
            END as drawdown_bucket,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days_to_peak,
            ROUND(AVG(score), 1) as avg_score
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL
        GROUP BY drawdown_bucket
        ORDER BY MAX(drawdown) DESC
    """)

    findings.append("### Drawdown Level vs Outcomes\n")
    findings.append(format_table(drawdown_buckets))
    findings.append("")

    # Sweet spot analysis
    findings.append("### Drawdown Sweet Spot\n")
    sweet_spot = run_query(conn, """
        SELECT
            CASE
                WHEN drawdown > -0.5 THEN 'Less beaten (< 50%)'
                WHEN drawdown > -0.7 THEN 'Sweet spot (50-70%)'
                ELSE 'Crushed (70%+)'
            END as category,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL
        GROUP BY category
        ORDER BY MAX(drawdown) DESC
    """)
    findings.append(format_table(sweet_spot))
    findings.append("")

    # =========================================================================
    # 2.5 Days Since High Analysis
    # =========================================================================
    findings.append("## 2.5 Extended Decline Analysis\n")
    findings.append("**Question:** Does length of decline predict outcomes?\n")

    decline_buckets = run_query(conn, """
        SELECT
            CASE
                WHEN days_since_high < 30 THEN '< 1 month'
                WHEN days_since_high < 90 THEN '1-3 months'
                WHEN days_since_high < 180 THEN '3-6 months'
                WHEN days_since_high < 365 THEN '6-12 months'
                ELSE '12+ months'
            END as decline_period,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days_to_peak
        FROM neumann_scores
        WHERE gain_pct < 50000 AND days_since_high IS NOT NULL
        GROUP BY decline_period
        ORDER BY MIN(days_since_high)
    """)

    findings.append("### Decline Period vs Outcomes\n")
    findings.append(format_table(decline_buckets))
    findings.append("")

    # =========================================================================
    # 2.6 Combined Patterns
    # =========================================================================
    findings.append("## 2.6 Emerging Patterns\n")

    # Best combination: deep drawdown + volume exhaustion
    combo = run_query(conn, """
        SELECT
            CASE
                WHEN drawdown <= -0.5 AND vol_ratio < 0.75 THEN 'Deep + Low Vol'
                WHEN drawdown <= -0.5 AND vol_ratio >= 0.75 THEN 'Deep + Normal Vol'
                WHEN drawdown > -0.5 AND vol_ratio < 0.75 THEN 'Shallow + Low Vol'
                ELSE 'Shallow + Normal Vol'
            END as pattern,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL AND vol_ratio IS NOT NULL
        GROUP BY pattern
        ORDER BY AVG(gain_pct) DESC
    """)

    findings.append("### Drawdown + Volume Combinations\n")
    findings.append(format_table(combo))
    findings.append("")

    # =========================================================================
    # Summary
    # =========================================================================
    findings.append("## Summary & Key Findings\n")
    findings.append("### Confirmed Patterns\n")
    findings.append("1. [To be filled after review]")
    findings.append("2. [To be filled after review]")
    findings.append("")
    findings.append("### Surprising Findings\n")
    findings.append("1. [To be filled after review]")
    findings.append("2. [To be filled after review]")
    findings.append("")
    findings.append("### Hypotheses for Phase 3\n")
    findings.append("1. [To be filled after review]")
    findings.append("2. [To be filled after review]")
    findings.append("")

    # Write output
    output_path = Path(OUTPUT_PATH)
    output_path.write_text("\n".join(findings))
    print(f"Phase 2 analysis complete. Output: {OUTPUT_PATH}")

    conn.close()

    # Also print to stdout
    print("\n" + "="*60)
    print("\n".join(findings))


if __name__ == "__main__":
    main()
