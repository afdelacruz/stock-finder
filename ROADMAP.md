# Stock Finder Roadmap

*Last updated: 2026-01-01*

## Vision

A **data-driven, feedback-loop system** to identify high-potential stocks before they move.

**Key Principle:** Criteria are **derived from statistical analysis**, not hardcoded assumptions.

---

## The Feedback Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│    │ ANALYZE  │────►│ DERIVE   │────►│  SCAN    │────►│CANDIDATES│        │
│    │any period│     │ criteria │     │  daily   │     │ pipeline │        │
│    └──────────┘     └──────────┘     └──────────┘     └────┬─────┘        │
│          ▲                                                  │              │
│          │                                                  ▼              │
│          │          ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│          └──────────│MEASURE   │◄────│ OUTCOME  │◄────│WATCHLIST │        │
│           feedback  │performance│    │ tracking │     │ + alerts │        │
│                     └──────────┘     └──────────┘     └──────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Issue Tracker

### Closed (Done)
| # | Title | Status |
|---|-------|--------|
| #1 | FMP Data Provider | ✅ Done |
| #2 | Retroactive Neumann Scoring | ✅ Done |
| #3 | Trendline Analysis | ✅ Done |
| #4 | Parallel Processing | ✅ Done |
| #5 | Disk Caching | ✅ Done |
| #8 | Simplify Scoring Model | ✅ Done |
| #10 | Watchlist and Alerts | ✅ Closed (duplicate of #18) |
| #13 | Database Schema | ✅ Done |
| #14 | Theme Population | ✅ Done |
| #15 | Research Module | ✅ Done |
| #16 | CLI Commands | ✅ Done |

### Open (To Do)
| # | Title | Phase | Priority | Blocked By |
|---|-------|-------|----------|------------|
| #20 | Statistical Analysis Framework | 1 | **P0** | None |
| #21 | Distribution & Criteria Derivation | 1 | **P0** | #20 |
| #9 | Forward-Looking Scanner | 2 | P1 | #21 |
| #18 | Watchlist & Tracking | 2 | P1 | #9 |
| #22 | Outcome Tracking | 3 | P1 | #18 |
| #11 | Backtest Validation | 4 | P2 | #22 |
| #17 | Dashboard | - | P2 | None (V1 on branch) |
| #19 | Expand Historical Data | 5 | P3 | #11 |

---

## Phases

### PHASE 1: Analysis Foundation
*Build the statistical engine that drives everything*

```
┌─────────────────────────────────────────────────────────────────┐
│  #20 Statistical Analysis Framework                             │
│  ═══════════════════════════════════                            │
│                                                                 │
│  • Analyze ANY time period (2018-2020, 2020-2022, etc.)        │
│  • Analyze ANY ticker universe (NASDAQ, NYSE, custom)          │
│  • Calculate statistics for each variable:                     │
│      - Mean, median, std dev                                   │
│      - Percentiles (p10, p25, p75, p90)                       │
│      - Lift (winners vs all stocks)                           │
│  • Store results for comparison                                │
│                                                                 │
│  CLI: stock-finder analyze run --start 2018-01-01 --end 2022   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  #21 Distribution Analysis & Criteria Derivation                │
│  ═══════════════════════════════════════════════                │
│                                                                 │
│  • Generate distributions (histograms) per variable            │
│  • Compare winners vs all stocks                               │
│  • Derive optimal thresholds from data:                        │
│      "What drawdown threshold captures 70% of winners?"        │
│  • Check stability across time periods:                        │
│      "Do patterns persist or change?"                          │
│  • Output: Data-derived criteria, not guesses                  │
│                                                                 │
│  CLI: stock-finder analyze derive-criteria --capture-rate 0.70 │
└─────────────────────────────────────────────────────────────────┘
```

**Outcome:** Criteria thresholds backed by statistical analysis.

---

### PHASE 2: Scanning Pipeline
*Apply derived criteria to find current opportunities*

```
┌─────────────────────────────────────────────────────────────────┐
│  #9 Forward-Looking Scanner                                     │
│  ═══════════════════════════                                    │
│                                                                 │
│  • Scan current market (NASDAQ, NYSE, or custom)               │
│  • Apply DERIVED criteria (from Phase 1)                       │
│  • Score and rank candidates                                   │
│  • Save to database with criteria version link                 │
│                                                                 │
│  CLI: stock-finder scan-live --universe nasdaq                 │
│                                                                 │
│  Output:                                                        │
│  ┌────────┬───────────┬───────────┬───────┬──────────────┐     │
│  │ Ticker │ Drawdown  │ Vol Ratio │ Score │ Criteria     │     │
│  ├────────┼───────────┼───────────┼───────┼──────────────┤     │
│  │ XYZ    │ -89%      │ 0.42x     │ 7     │ v1-derived   │     │
│  │ ABC    │ -86%      │ 0.68x     │ 6     │ v1-derived   │     │
│  └────────┴───────────┴───────────┴───────┴──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  #18 Watchlist & Tracking                                       │
│  ════════════════════════                                       │
│                                                                 │
│  • Add candidates to watchlist                                 │
│  • Monitor for triggers:                                       │
│      - Volume spike (>2x average)                              │
│      - Price breakout (>10-day high)                           │
│      - Theme peer moving                                       │
│  • Status workflow: new → watching → triggered → closed        │
│                                                                 │
│  CLI: stock-finder watchlist check                             │
│                                                                 │
│  Output:                                                        │
│  ⚡ ASTS: Volume spike 2.8x (TRIGGERED)                        │
│  ⚡ SMR: Broke 10-day high (TRIGGERED)                         │
└─────────────────────────────────────────────────────────────────┘
```

**Outcome:** Current candidates identified and monitored.

---

### PHASE 3: Outcome Tracking
*Record what actually happens for feedback*

```
┌─────────────────────────────────────────────────────────────────┐
│  #22 Outcome Tracking                                           │
│  ════════════════════                                           │
│                                                                 │
│  • Record entry when trigger fires                             │
│  • Track peak price reached                                    │
│  • Calculate actual gain/loss when closed                      │
│  • Link to criteria version (for comparison)                   │
│                                                                 │
│  CLI: stock-finder outcome record ASTS --entry-price 4.50      │
│       stock-finder outcome close ASTS --exit-price 12.30       │
│                                                                 │
│  Enables:                                                       │
│  • "Criteria v1 had 68% win rate"                              │
│  • "Nuclear theme outperformed Space"                          │
│  • "Volume spike trigger > price breakout trigger"             │
└─────────────────────────────────────────────────────────────────┘
```

**Outcome:** Real performance data for feedback loop.

---

### PHASE 4: Performance & Feedback
*Measure results and improve the system*

```
┌─────────────────────────────────────────────────────────────────┐
│  #11 Backtest & Performance                                     │
│  ══════════════════════════                                     │
│                                                                 │
│  • Calculate: win rate, avg gain, expectancy                   │
│  • Compare criteria versions                                   │
│  • Compare to benchmark (SPY)                                  │
│  • Generate performance reports                                │
│                                                                 │
│  CLI: stock-finder performance report                          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ CRITERIA COMPARISON                                     │    │
│  ├──────────────┬──────────┬──────────┬─────────────────┤    │
│  │ Version      │ Win Rate │ Avg Gain │ Expectancy      │    │
│  ├──────────────┼──────────┼──────────┼─────────────────┤    │
│  │ v1-strict    │ 68%      │ +245%    │ +156%           │    │
│  │ v2-relaxed   │ 52%      │ +180%    │ +78%            │    │
│  │ random       │ 31%      │ +95%     │ -12%            │    │
│  └──────────────┴──────────┴──────────┴─────────────────┘    │
│                                                                 │
│  FEEDBACK: v1-strict outperforms → keep using                  │
│            Consider tightening further?                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ FEEDBACK LOOP   │
                     │                 │
                     │ Performance     │
                     │ informs next    │
                     │ analysis run    │──────► Back to Phase 1
                     │                 │
                     └─────────────────┘
```

**Outcome:** Continuous improvement based on real results.

---

### PHASE 5: Expansion
*More data, automation*

```
┌─────────────────────────────────────────────────────────────────┐
│  #19 Expand Historical Data                                     │
│  ══════════════════════════                                     │
│                                                                 │
│  • Scan more years (2010-2018)                                 │
│  • More data = more robust statistics                          │
│  • Validate criteria across longer time spans                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Future: Automation                                             │
│  ══════════════════                                             │
│                                                                 │
│  • Scheduled scans (cron: daily/weekly)                        │
│  • Email/SMS alerts on triggers                                │
│  • Auto-update dashboard                                       │
│  • Auto-refresh prices for outcome tracking                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependency Graph

```
                         PHASE 1
                    ┌──────────────┐
                    │     #20      │
                    │  Analysis    │
                    │  Framework   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │     #21      │
                    │ Distribution │
                    │ & Criteria   │
                    └──────┬───────┘
                           │
              ─────────────┴─────────────
             │                           │
             ▼                           │
      PHASE 2                            │
┌──────────────┐                         │
│     #9       │                         │
│   Scanner    │                         │
└──────┬───────┘                         │
       │                                 │
       ▼                                 │
┌──────────────┐                         │
│     #18      │                         │
│  Watchlist   │                         │
└──────┬───────┘                         │
       │                                 │
       ▼                                 │
      PHASE 3                            │
┌──────────────┐                         │
│     #22      │                         │
│  Outcomes    │                         │
└──────┬───────┘                         │
       │                                 │
       ▼                                 │
      PHASE 4                            │
┌──────────────┐                         │
│     #11      │                         │
│ Performance  │                         │
└──────┬───────┘                         │
       │                                 │
       └─────────────────────────────────┘
                    FEEDBACK
```

---

## Success Metrics

When complete, you can:

```bash
# 1. Analyze any period statistically
$ stock-finder analyze run --start 2020-01-01 --end 2024-12-31
Analyzed 3,456 winners. Results saved.

# 2. Derive criteria from data
$ stock-finder analyze derive-criteria --capture-rate 0.70
Derived criteria:
  Drawdown:  <= -82% (captures 71% of winners)
  Vol Ratio: <= 0.72 (captures 69% of winners)
Saved as: criteria-v2-derived

# 3. Check pattern stability
$ stock-finder analyze stability --variable drawdown
Stability score: 0.91 (HIGH) - pattern likely to persist

# 4. Scan current market
$ stock-finder scan-live --universe nasdaq
Found 34 candidates matching criteria-v2-derived

# 5. Monitor watchlist
$ stock-finder watchlist check
⚡ ASTS: Volume spike 2.8x (TRIGGERED!)

# 6. Track outcomes
$ stock-finder outcome performance
Criteria v2: 72% win rate, +198% avg gain, +134% expectancy

# 7. Feedback: Criteria working? Keep or adjust.
```

---

## Quick Reference

| Phase | Issue | What | CLI |
|-------|-------|------|-----|
| 1 | #20 | Analyze any period | `analyze run` |
| 1 | #21 | Derive criteria | `analyze derive-criteria` |
| 2 | #9 | Scan current market | `scan-live` |
| 2 | #18 | Track watchlist | `watchlist check` |
| 3 | #22 | Record outcomes | `outcome record` |
| 4 | #11 | Measure performance | `performance report` |
