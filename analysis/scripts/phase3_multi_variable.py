#!/usr/bin/env python3
"""
Phase 3: Multi-Variable Analysis
=================================
Test interactions between variables identified in Phase 2.

Hypotheses to test:
1. Deep drawdown (85%+) AND extended decline (12mo+) outperforms either alone
2. Volume dynamics: setup volume vs ignition volume differences
3. What predicts fast moves (< 1 month)?
4. Optimal combination of all factors

Run: python analysis/scripts/phase3_multi_variable.py
Output: analysis/findings/phase3_multi_variable.md
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = "data/stock_finder.db"
OUTPUT_PATH = "analysis/findings/phase3_multi_variable.md"


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

    findings.append("# Phase 3: Multi-Variable Analysis")
    findings.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # =========================================================================
    # 3.1 Drawdown x Decline Interaction
    # =========================================================================
    findings.append("## 3.1 Drawdown x Decline Length Interaction\n")
    findings.append("**Hypothesis:** Deep drawdown (85%+) AND extended decline (12mo+) outperforms either alone.\n")

    interaction = run_query(conn, """
        SELECT
            CASE
                WHEN drawdown <= -0.85 THEN 'Deep (85%+)'
                WHEN drawdown <= -0.50 THEN 'Moderate (50-85%)'
                ELSE 'Shallow (<50%)'
            END as drawdown_cat,
            CASE
                WHEN days_since_high >= 365 THEN 'Long (12mo+)'
                WHEN days_since_high >= 180 THEN 'Medium (6-12mo)'
                ELSE 'Short (<6mo)'
            END as decline_cat,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days,
            ROUND(AVG(gain_pct) / NULLIF(AVG(days_to_peak), 0), 2) as gain_per_day
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL AND days_since_high IS NOT NULL
        GROUP BY drawdown_cat, decline_cat
        ORDER BY AVG(gain_pct) DESC
    """)

    findings.append("### Full Interaction Matrix\n")
    findings.append(format_table(interaction))
    findings.append("")

    # Best combinations
    findings.append("### Top 3 Combinations by Avg Gain\n")
    for i, row in enumerate(interaction[:3], 1):
        findings.append(f"{i}. **{row['drawdown_cat']} + {row['decline_cat']}**: {row['avg_gain']}% gain in {row['avg_days']} days (n={row['count']})")
    findings.append("")

    # =========================================================================
    # 3.2 Volume Dynamics by Speed
    # =========================================================================
    findings.append("## 3.2 Volume Dynamics by Move Speed\n")
    findings.append("**Hypothesis:** Fast moves have different volume characteristics than slow moves.\n")

    vol_by_speed = run_query(conn, """
        SELECT
            CASE
                WHEN days_to_peak < 30 THEN 'Fast (<1mo)'
                WHEN days_to_peak < 180 THEN 'Medium (1-6mo)'
                ELSE 'Slow (6mo+)'
            END as speed,
            CASE
                WHEN vol_ratio < 0.75 THEN 'Low (<0.75)'
                WHEN vol_ratio < 1.5 THEN 'Normal (0.75-1.5)'
                ELSE 'High (1.5+)'
            END as vol_level,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(drawdown), 2) as avg_drawdown
        FROM neumann_scores
        WHERE gain_pct < 50000 AND vol_ratio IS NOT NULL AND days_to_peak IS NOT NULL
        GROUP BY speed, vol_level
        ORDER BY MIN(days_to_peak), MIN(vol_ratio)
    """)

    findings.append("### Volume x Speed Matrix\n")
    findings.append(format_table(vol_by_speed))
    findings.append("")

    # Fast mover volume profile
    fast_vol_profile = run_query(conn, """
        SELECT
            ROUND(AVG(vol_ratio), 2) as avg_vol,
            ROUND(MIN(vol_ratio), 2) as min_vol,
            ROUND(MAX(vol_ratio), 2) as max_vol,
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            COUNT(*) as count
        FROM neumann_scores
        WHERE days_to_peak < 30 AND gain_pct < 50000 AND vol_ratio IS NOT NULL
    """)[0]

    findings.append(f"### Fast Mover Profile (< 1 month)\n")
    findings.append(f"- Count: {fast_vol_profile['count']}")
    findings.append(f"- Avg Volume Ratio: {fast_vol_profile['avg_vol']} (range: {fast_vol_profile['min_vol']} to {fast_vol_profile['max_vol']})")
    findings.append(f"- Avg Drawdown: {fast_vol_profile['avg_drawdown']}")
    findings.append("")

    # =========================================================================
    # 3.3 Fast Mover Predictors
    # =========================================================================
    findings.append("## 3.3 Fast Mover Predictors\n")
    findings.append("**Question:** What characteristics predict fast moves (< 1 month)?")
    findings.append("*Goal: Identify setups likely to move quickly for better timing.*\n")

    # Compare fast vs slow on all dimensions
    fast_vs_slow = run_query(conn, """
        SELECT
            'Fast (<1mo)' as category,
            COUNT(*) as count,
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            ROUND(AVG(days_since_high), 0) as avg_days_decline,
            ROUND(AVG(vol_ratio), 2) as avg_vol_ratio,
            ROUND(AVG(range_position), 2) as avg_range_pos,
            ROUND(AVG(gain_pct), 0) as avg_gain
        FROM neumann_scores
        WHERE days_to_peak < 30 AND gain_pct < 50000 AND drawdown IS NOT NULL
        UNION ALL
        SELECT
            'Slow (6mo+)' as category,
            COUNT(*) as count,
            ROUND(AVG(drawdown), 2) as avg_drawdown,
            ROUND(AVG(days_since_high), 0) as avg_days_decline,
            ROUND(AVG(vol_ratio), 2) as avg_vol_ratio,
            ROUND(AVG(range_position), 2) as avg_range_pos,
            ROUND(AVG(gain_pct), 0) as avg_gain
        FROM neumann_scores
        WHERE days_to_peak >= 180 AND gain_pct < 50000 AND drawdown IS NOT NULL
    """)

    findings.append("### Fast vs Slow Comparison\n")
    findings.append(format_table(fast_vs_slow))
    findings.append("")

    # What makes fast movers different?
    findings.append("### Distinguishing Characteristics\n")
    if len(fast_vs_slow) >= 2:
        fast = fast_vs_slow[0]
        slow = fast_vs_slow[1]
        findings.append(f"| Metric | Fast | Slow | Difference |")
        findings.append(f"| --- | --- | --- | --- |")
        findings.append(f"| Drawdown | {fast['avg_drawdown']} | {slow['avg_drawdown']} | Fast are deeper |")
        findings.append(f"| Days Declining | {fast['avg_days_decline']} | {slow['avg_days_decline']} | {'Similar' if abs(fast['avg_days_decline'] - slow['avg_days_decline']) < 50 else 'Fast shorter'} |")
        findings.append(f"| Volume Ratio | {fast['avg_vol_ratio']} | {slow['avg_vol_ratio']} | Fast higher |")
        findings.append(f"| Range Position | {fast['avg_range_pos']} | {slow['avg_range_pos']} | {'Similar' if abs(fast['avg_range_pos'] - slow['avg_range_pos']) < 0.1 else 'Different'} |")
    findings.append("")

    # =========================================================================
    # 3.4 Optimal Setup Profile
    # =========================================================================
    findings.append("## 3.4 Optimal Setup Profile\n")
    findings.append("**Goal:** Define the ideal setup based on all variables.\n")

    # Create a "quality score" combining best factors
    optimal_profiles = run_query(conn, """
        SELECT
            CASE
                WHEN drawdown <= -0.85 AND days_since_high >= 365 AND vol_ratio < 0.75 THEN 'Ideal (deep+long+low_vol)'
                WHEN drawdown <= -0.85 AND days_since_high >= 365 THEN 'Good (deep+long)'
                WHEN drawdown <= -0.85 AND vol_ratio < 0.75 THEN 'Good (deep+low_vol)'
                WHEN drawdown <= -0.85 THEN 'Moderate (deep only)'
                ELSE 'Weak'
            END as setup_quality,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days,
            ROUND(MIN(gain_pct), 0) as min_gain,
            ROUND(MAX(gain_pct), 0) as max_gain
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL
        GROUP BY setup_quality
        ORDER BY AVG(gain_pct) DESC
    """)

    findings.append("### Setup Quality Tiers\n")
    findings.append(format_table(optimal_profiles))
    findings.append("")

    # =========================================================================
    # 3.5 Score Recalibration Analysis
    # =========================================================================
    findings.append("## 3.5 Score Recalibration Check\n")
    findings.append("**Question:** How would a recalibrated score compare to current scoring?\n")

    # Simulate a "better" score based on findings
    recalibrated = run_query(conn, """
        SELECT
            -- Current score for comparison
            score as current_score,
            -- Simulated new score based on Phase 2 findings
            (CASE WHEN drawdown <= -0.85 THEN 3 WHEN drawdown <= -0.50 THEN 2 ELSE 0 END) +
            (CASE WHEN days_since_high >= 365 THEN 2 WHEN days_since_high >= 180 THEN 1 ELSE 0 END) +
            (CASE WHEN vol_ratio < 0.75 THEN 2 ELSE 0 END) as simulated_score,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL
        GROUP BY current_score, simulated_score
        ORDER BY simulated_score DESC, current_score DESC
    """)

    findings.append("### Current vs Simulated Score Distribution\n")
    findings.append("*Simulated score: drawdown (0-3) + decline length (0-2) + low volume (0-2) = max 7*\n")
    findings.append(format_table(recalibrated[:15]))  # Top 15 combinations
    findings.append("")

    # Best simulated scores
    best_simulated = run_query(conn, """
        SELECT
            (CASE WHEN drawdown <= -0.85 THEN 3 WHEN drawdown <= -0.50 THEN 2 ELSE 0 END) +
            (CASE WHEN days_since_high >= 365 THEN 2 WHEN days_since_high >= 180 THEN 1 ELSE 0 END) +
            (CASE WHEN vol_ratio < 0.75 THEN 2 ELSE 0 END) as simulated_score,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days
        FROM neumann_scores
        WHERE gain_pct < 50000 AND drawdown IS NOT NULL AND vol_ratio IS NOT NULL
        GROUP BY simulated_score
        ORDER BY simulated_score DESC
    """)

    findings.append("### Simulated Score Performance\n")
    findings.append(format_table(best_simulated))
    findings.append("")

    # =========================================================================
    # 3.6 Entry Signal Candidates
    # =========================================================================
    findings.append("## 3.6 Entry Signal Candidates\n")
    findings.append("**Identifying potential entry signals for Phase 4 testing.**\n")

    # Volume spike analysis - what happens when low-volume stocks get volume?
    findings.append("### Volume Profile Hypothesis\n")
    findings.append("*If low setup volume predicts bigger moves, can we use volume spike as entry trigger?*\n")

    vol_spike_potential = run_query(conn, """
        SELECT
            CASE
                WHEN vol_ratio < 0.5 THEN 'Very Low Setup Vol'
                WHEN vol_ratio < 0.75 THEN 'Low Setup Vol'
                WHEN vol_ratio < 1.0 THEN 'Below Avg Setup Vol'
                ELSE 'Normal+ Setup Vol'
            END as setup_vol,
            COUNT(*) as count,
            ROUND(AVG(gain_pct), 0) as avg_gain,
            ROUND(AVG(days_to_peak), 0) as avg_days,
            ROUND(AVG(gain_pct) / NULLIF(AVG(days_to_peak), 0), 2) as gain_velocity
        FROM neumann_scores
        WHERE gain_pct < 50000 AND vol_ratio IS NOT NULL
        GROUP BY setup_vol
        ORDER BY MIN(vol_ratio)
    """)

    findings.append(format_table(vol_spike_potential))
    findings.append("")
    findings.append("*Entry signal hypothesis: Buy when a low-setup-volume stock sees 2x+ volume spike.*\n")

    # =========================================================================
    # Summary
    # =========================================================================
    findings.append("## Summary & Key Findings\n")
    findings.append("### Confirmed Interactions\n")
    findings.append("1. [To be filled after review]")
    findings.append("2. [To be filled after review]")
    findings.append("")
    findings.append("### Optimal Setup Definition\n")
    findings.append("1. [To be filled after review]")
    findings.append("")
    findings.append("### Entry Signal Candidates for Phase 4\n")
    findings.append("1. [To be filled after review]")
    findings.append("2. [To be filled after review]")
    findings.append("")

    # Write output
    output_path = Path(OUTPUT_PATH)
    output_path.write_text("\n".join(findings))
    print(f"Phase 3 analysis complete. Output: {OUTPUT_PATH}")

    conn.close()

    # Also print to stdout
    print("\n" + "="*60)
    print("\n".join(findings))


if __name__ == "__main__":
    main()
