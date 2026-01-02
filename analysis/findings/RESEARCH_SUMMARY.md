# Stock Finder Research Summary

*Comprehensive Analysis of 3,177 Stocks with 300%+ Gains (2018-2025)*

---

## Executive Summary

We analyzed 6,006 stock moves across 3,177 unique tickers that achieved 300%+ gains. The goal: identify predictive patterns for entry timing and position sizing.

### Key Findings

1. **Only 2 of 8 Neumann criteria matter significantly** - Drawdown (1.86x lift) and Extended Decline (1.61x lift) are the key predictors. Below SMA200 is nearly useless (1.06x lift).

2. **The optimal setup is simple**: Down 85%+ from high + Volume ratio < 0.75x = **2,542% avg gain in 246 days**

3. **Stocks pump in themes, not randomly** - Themed stocks (Crypto, Meme, Nuclear, etc.) return 3-5x more than unthemed stocks.

4. **Themes ignite and peak together** - The Jan-Feb 2021 super-peak saw 4 themes top within 3 weeks.

5. **Smaller corrections beat major crashes** - Oct 2022/2023 corrections produced faster, bigger moves than COVID crash.

---

## Part 1: What Predicts Bigger Gains?

### Criteria Effectiveness (Lift Analysis)

| Criteria | Lift | Verdict |
|----------|------|---------|
| Drawdown ≥50% | **1.86x** | **Essential** |
| Extended Decline 90d+ | **1.61x** | **Important** |
| Near Lows | 1.29x | Moderate |
| Volume Exhaustion | 1.27x | Moderate |
| Below SMA50 | 1.12x | Weak |
| Below SMA200 | 1.06x | **Remove** |

### Optimal Setup Profile

| Criteria | Threshold | Impact |
|----------|-----------|--------|
| Drawdown | ≥85% from high | **Required** - adds ~1,300% to avg gain |
| Volume Ratio | < 0.75x average | **Important** - adds ~500% to avg gain |
| Decline Length | ≥12 months | Optional - marginal improvement |

### Setup Quality Tiers

| Setup | Count | Avg Gain | Avg Days |
|-------|-------|----------|----------|
| Deep + Low Vol | 248 | **2,542%** | **246 days** |
| Deep + Long + Low Vol | 538 | 2,418% | 294 days |
| Deep + Long | 1,200 | 2,053% | 475 days |
| Deep Only | 506 | 1,772% | 468 days |
| Weak (no deep drawdown) | 3,020 | 1,005% | 906 days |

**Bottom line:** Deep drawdown + low volume is the best combination. Adding extended decline doesn't improve returns.

---

## Part 2: Timing Patterns

### When Stocks Ignite

**56% of all big moves started during 4 identifiable market events:**

| Event | Ignitions | Avg Gain | Velocity |
|-------|-----------|----------|----------|
| COVID Crash (Mar 2020) | 2,343 | 1,225% | 1.38%/day |
| Dec 2018 Selloff | 468 | 1,734% | 1.59%/day |
| Oct-Dec 2022 Bottom | 277 | 2,365% | **4.62%/day** |
| Oct-Nov 2023 Dip | 242 | 1,764% | **5.53%/day** |

**Key insight:** Smaller corrections produce faster, higher-returning moves than major crashes.

### Seasonal Patterns

**Best ignition months:** October-December (Q4 selloffs create setups)
- November ignitions: 2,688% avg gain
- December ignitions: 2,072% avg gain

**Best peak months:** January-February, October-November

### Move Duration

| Duration | Count | Avg Gain | Gain/Day |
|----------|-------|----------|----------|
| < 1 month | 346 | 1,746% | **143.7%/day** |
| 1-3 months | 466 | 1,217% | 20.9%/day |
| 3-6 months | 496 | 1,392% | 10.5%/day |
| 6-12 months | 1,112 | 1,624% | 6.2%/day |
| 1-2 years | 1,338 | **1,876%** | 3.6%/day |
| 2+ years | 2,224 | 1,267% | 1.0%/day |

**Surprising:** Bigger gains don't take longer. 5000%+ moves average 569 days - faster than 300-500% moves (693 days).

---

## Part 3: Thematic Clustering

### Theme Performance

| Theme | Stocks | Avg Gain | Avg Days | Top Performer |
|-------|--------|----------|----------|---------------|
| **Uranium/Nuclear** | 9 | 5,472% | 985 | LEU: 25,699% |
| **Crypto/Bitcoin** | 14 | 6,118% | 427 | MARA: 18,922% |
| **Meme Stocks** | 8 | 5,309% | 195 | GME: 12,311% |
| **Clean Energy/EV** | 13 | 4,056% | 402 | FCEL: 17,375% |
| **COVID Plays** | 8 | 4,050% | 266 | NVAX: 8,570% |
| **Space/Aerospace** | 13 | 1,711% | 533 | ASTS: 4,661% |
| Other | 3,108 | 1,433% | 658 | Various |

**Themed stocks return 3-5x more than unthemed stocks.**

### Theme Seasons

| Theme | Ignition Window | Peak Window | Duration |
|-------|-----------------|-------------|----------|
| Meme | Mar '20 - Jan '21 | Jan - Jun '21 | 15 months |
| COVID | Jun '19 - Aug '20 | Feb - Aug '21 | 20 months |
| Clean Energy | Dec '18 - Mar '20 | Jan - Feb '21 | 18 months |
| Crypto W1 | Mar '20 | Jan - Nov '21 | 20 months |
| Crypto W2 | Dec '22 | Nov '25 | 36 months |
| Space | Dec '22 + Apr '24 | Oct - Dec '25 | 18-34 months |
| Nuclear | Mar '20 + 2024 | Oct '25 | 5-7 years |

### Super-Peak Events

**Jan-Feb 2021:** Meme, Clean Energy, Crypto W1, COVID all peaked within 3 weeks

**Oct 2025:** Nuclear (all 9 stocks) + Space (8 stocks) peaked within 3 weeks

---

## Part 4: Recommended Scoring Model

### Current vs Proposed

| Model | Criteria | Max Score | Correlation |
|-------|----------|-----------|-------------|
| Original Neumann | 8 equal-weight | 8 | Moderate |
| **Proposed** | 3 weighted | 7 | Strong monotonic |

### Proposed Scoring Formula

```
Score = Drawdown (0-3) + Decline Length (0-2) + Low Volume (0-2)

Drawdown:
  - ≥85% down: 3 points
  - 50-85% down: 2 points
  - <50% down: 0 points

Decline Length:
  - ≥12 months: 2 points
  - 6-12 months: 1 point
  - <6 months: 0 points

Volume Ratio:
  - <0.75x: 2 points
  - ≥0.75x: 0 points
```

### Proposed Score Performance

| Score | Count | Avg Gain | Avg Days |
|-------|-------|----------|----------|
| 7 | 538 | **2,418%** | 294 |
| 6 | 331 | 2,267% | 506 |
| 5 | 1,387 | 2,037% | 482 |
| 4 | 1,552 | 1,204% | 759 |
| 3 | 537 | 1,184% | 731 |
| 2 | 809 | 831% | 999 |
| 1 | 59 | 769% | 1,147 |
| 0 | 291 | 739% | 1,105 |

**Clear monotonic relationship:** Higher score = bigger gains, faster moves.

---

## Part 5: Entry Signal Hypothesis

### Volume Dynamics

| Setup Volume | Count | Avg Gain | Velocity |
|--------------|-------|----------|----------|
| Very Low (<0.5x) | 748 | 2,352% | **5.85%/day** |
| Low (0.5-0.75x) | 559 | 1,658% | 2.84%/day |
| Below Avg (0.75-1x) | 599 | 1,095% | 1.51%/day |
| Normal+ (1x+) | 3,598 | 1,382% | 1.84%/day |

**Hypothesis:** Low setup volume predicts magnitude. Volume *spike* triggers the move.

### Proposed Entry Strategy

1. **Identify setup:** Score 5+ (deep drawdown + low volume)
2. **Wait for trigger:** 2x+ volume spike from 20-day average
3. **Enter on confirmation:** Price breaks above 10-day high
4. **Position size:** Based on score (higher score = larger position)

*Note: This hypothesis requires backtesting (Issue #11)*

---

## Part 6: Actionable Recommendations

### For Stock Selection

| Priority | Action |
|----------|--------|
| 1 | Require 85%+ drawdown (non-negotiable) |
| 2 | Prefer volume ratio < 0.75x |
| 3 | Identify theme membership (3-5x better returns) |
| 4 | Use proposed 7-point scoring model |

### For Timing

| Priority | Action |
|----------|--------|
| 1 | Watch for setups during Q4 corrections |
| 2 | Smaller corrections (5-15%) > major crashes |
| 3 | When one theme stock moves, watch entire theme |
| 4 | Expect 12-18 month holding period for best results |

### For Risk Management

| Insight | Implication |
|---------|-------------|
| Themes peak together | When leaders top, exit laggards |
| Meme stocks fastest (195 days) | Tighter stops, quicker exits |
| Nuclear slowest (5-7 years) | Patience required, size smaller |
| 5000%+ gains take ~569 days | Don't sell too early |

---

## Appendix: Data Quality Notes

### Coverage
- 3,177 unique tickers
- 6,006 scored records
- Date range: Dec 2018 - Dec 2025

### Field Completeness
| Field | Complete |
|-------|----------|
| Drawdown | 92.0% |
| Days Since High | 92.0% |
| Volume Ratio | 91.9% |
| SMA50 | 92.0% |
| SMA200 | 87.2% |
| Market Cap | 0.8% (unusable) |

### Known Issues
- Score 0 stocks: 94% have NULL technical data (missing data, not failed criteria)
- Market cap data nearly empty - cannot analyze size factor
- Some duplicate records from multiple scan runs

---

## Files Generated

```
analysis/
├── findings/
│   ├── phase1_data_inventory.md      # Data scope and distributions
│   ├── phase2_single_variable.md     # Individual factor analysis
│   ├── phase3_multi_variable.md      # Factor interactions
│   ├── theme_timeline.md             # Theme seasons and timing
│   └── RESEARCH_SUMMARY.md           # This document
└── scripts/
    ├── phase1_data_inventory.py      # Repeatable data inventory
    ├── phase2_single_variable.py     # Single variable analysis
    └── phase3_multi_variable.py      # Multi-variable analysis
```

---

## Next Steps

| Priority | Task | Status |
|----------|------|--------|
| 1 | Implement weighted scoring model | Done (Issue #8) |
| 2 | Build forward-looking scanner | Open (Issue #9) |
| 3 | Backtest entry signal hypothesis | Open (Issue #11) |
| 4 | Add theme auto-classification | Not started |
| 5 | Build watchlist/alerts | Open (Issue #10) |

---

*Research conducted Dec 2025 using Stock Finder CLI tool*
*Data source: Yahoo Finance historical prices*
