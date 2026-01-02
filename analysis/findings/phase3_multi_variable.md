# Phase 3: Multi-Variable Analysis

*Generated: 2025-12-30 23:30:05*

## 3.1 Drawdown x Decline Length Interaction

**Hypothesis:** Deep drawdown (85%+) AND extended decline (12mo+) outperforms either alone.

### Full Interaction Matrix

| drawdown_cat | decline_cat | count | avg_gain | avg_days | gain_per_day |
| --- | --- | --- | --- | --- | --- |
| Deep (85%+) | Long (12mo+) | 1738 | 2166.0 | 419.0 | 5.17 |
| Deep (85%+) | Medium (6-12mo) | 535 | 2041.0 | 386.0 | 5.28 |
| Deep (85%+) | Short (<6mo) | 219 | 1987.0 | 417.0 | 4.76 |
| Shallow (<50%) | Long (12mo+) | 56 | 1404.0 | 1135.0 | 1.24 |
| Moderate (50-85%) | Medium (6-12mo) | 471 | 1135.0 | 766.0 | 1.48 |
| Moderate (50-85%) | Long (12mo+) | 1246 | 1120.0 | 865.0 | 1.29 |
| Moderate (50-85%) | Short (<6mo) | 754 | 844.0 | 932.0 | 0.91 |
| Shallow (<50%) | Medium (6-12mo) | 97 | 797.0 | 1099.0 | 0.73 |
| Shallow (<50%) | Short (<6mo) | 396 | 789.0 | 1074.0 | 0.74 |

### Top 3 Combinations by Avg Gain

1. **Deep (85%+) + Long (12mo+)**: 2166.0% gain in 419.0 days (n=1738)
2. **Deep (85%+) + Medium (6-12mo)**: 2041.0% gain in 386.0 days (n=535)
3. **Deep (85%+) + Short (<6mo)**: 1987.0% gain in 417.0 days (n=219)

## 3.2 Volume Dynamics by Move Speed

**Hypothesis:** Fast moves have different volume characteristics than slow moves.

### Volume x Speed Matrix

| speed | vol_level | count | avg_gain | avg_drawdown |
| --- | --- | --- | --- | --- |
| Fast (<1mo) | Low (<0.75) | 120 | 2692.0 | -0.93 |
| Fast (<1mo) | Normal (0.75-1.5) | 43 | 1134.0 | -0.88 |
| Fast (<1mo) | High (1.5+) | 103 | 1449.0 | -0.92 |
| Medium (1-6mo) | High (1.5+) | 262 | 1564.0 | -0.91 |
| Medium (1-6mo) | Low (<0.75) | 310 | 1532.0 | -0.93 |
| Medium (1-6mo) | Normal (0.75-1.5) | 220 | 966.0 | -0.89 |
| Slow (6mo+) | Low (<0.75) | 877 | 2153.0 | -0.73 |
| Slow (6mo+) | Normal (0.75-1.5) | 1608 | 1292.0 | -0.71 |
| Slow (6mo+) | High (1.5+) | 1961 | 1392.0 | -0.65 |

### Fast Mover Profile (< 1 month)

- Count: 266
- Avg Volume Ratio: 2.69 (range: 0.0 to 39.13)
- Avg Drawdown: -0.92

## 3.3 Fast Mover Predictors

**Question:** What characteristics predict fast moves (< 1 month)?
*Goal: Identify setups likely to move quickly for better timing.*

### Fast vs Slow Comparison

| category | count | avg_drawdown | avg_days_decline | avg_vol_ratio | avg_range_pos | avg_gain |
| --- | --- | --- | --- | --- | --- | --- |
| Fast (<1mo) | 270 | -0.92 | 328.0 | 2.69 | 0.02 | 1942.0 |
| Slow (6mo+) | 4450 | -0.69 | 315.0 | 1.98 | 0.08 | 1507.0 |

### Distinguishing Characteristics

| Metric | Fast | Slow | Difference |
| --- | --- | --- | --- |
| Drawdown | -0.92 | -0.69 | Fast are deeper |
| Days Declining | 328.0 | 315.0 | Similar |
| Volume Ratio | 2.69 | 1.98 | Fast higher |
| Range Position | 0.02 | 0.08 | Similar |

## 3.4 Optimal Setup Profile

**Goal:** Define the ideal setup based on all variables.

### Setup Quality Tiers

| setup_quality | count | avg_gain | avg_days | min_gain | max_gain |
| --- | --- | --- | --- | --- | --- |
| Good (deep+low_vol) | 248 | 2542.0 | 246.0 | 300.0 | 49850.0 |
| Ideal (deep+long+low_vol) | 538 | 2418.0 | 294.0 | 300.0 | 41900.0 |
| Good (deep+long) | 1200 | 2053.0 | 475.0 | 302.0 | 42710.0 |
| Moderate (deep only) | 506 | 1772.0 | 468.0 | 301.0 | 35406.0 |
| Weak | 3020 | 1005.0 | 906.0 | 300.0 | 25699.0 |

## 3.5 Score Recalibration Check

**Question:** How would a recalibrated score compare to current scoring?

### Current vs Simulated Score Distribution

*Simulated score: drawdown (0-3) + decline length (0-2) + low volume (0-2) = max 7*

| current_score | simulated_score | count | avg_gain | avg_days |
| --- | --- | --- | --- | --- |
| 6 | 7 | 530 | 2420.0 | 295.0 |
| 5 | 7 | 8 | 2263.0 | 209.0 |
| 7 | 6 | 1 | 12608.0 | 742.0 |
| 6 | 6 | 307 | 2242.0 | 487.0 |
| 5 | 6 | 17 | 2601.0 | 758.0 |
| 4 | 6 | 4 | 538.0 | 873.0 |
| 3 | 6 | 2 | 1607.0 | 531.0 |
| 7 | 5 | 2 | 13899.0 | 552.0 |
| 6 | 5 | 244 | 1680.0 | 539.0 |
| 5 | 5 | 1107 | 2081.0 | 475.0 |
| 4 | 5 | 38 | 2300.0 | 254.0 |
| 6 | 4 | 215 | 1131.0 | 742.0 |
| 5 | 4 | 1273 | 1179.0 | 773.0 |
| 4 | 4 | 52 | 1702.0 | 398.0 |
| 3 | 4 | 10 | 4172.0 | 793.0 |

### Simulated Score Performance

| simulated_score | count | avg_gain | avg_days |
| --- | --- | --- | --- |
| 7 | 538 | 2418.0 | 294.0 |
| 6 | 331 | 2267.0 | 506.0 |
| 5 | 1387 | 2037.0 | 482.0 |
| 4 | 1552 | 1204.0 | 759.0 |
| 3 | 537 | 1184.0 | 731.0 |
| 2 | 809 | 831.0 | 999.0 |
| 1 | 59 | 769.0 | 1147.0 |
| 0 | 291 | 739.0 | 1105.0 |

## 3.6 Entry Signal Candidates

**Identifying potential entry signals for Phase 4 testing.**

### Volume Profile Hypothesis

*If low setup volume predicts bigger moves, can we use volume spike as entry trigger?*

| setup_vol | count | avg_gain | avg_days | gain_velocity |
| --- | --- | --- | --- | --- |
| Very Low Setup Vol | 748 | 2352.0 | 402.0 | 5.85 |
| Low Setup Vol | 559 | 1658.0 | 584.0 | 2.84 |
| Below Avg Setup Vol | 599 | 1095.0 | 726.0 | 1.51 |
| Normal+ Setup Vol | 3598 | 1382.0 | 750.0 | 1.84 |

*Entry signal hypothesis: Buy when a low-setup-volume stock sees 2x+ volume spike.*

## Summary & Key Findings

### Confirmed Interactions

1. **Deep drawdown dominates**: When drawdown >= 85%, decline length adds minimal value. All three combinations average ~2,000%+ gains.
2. **Volume clarification**: Phase 2's "fast movers have high volume" was misleading. When properly segmented, fast movers WITH LOW VOLUME average 2,692% vs 1,449% with high volume.
3. **Best combination is Deep + Low Vol**: 2,542% avg gain in just 246 days - beats the triple combo (deep+long+low_vol: 2,418% in 294 days).

### Optimal Setup Definition

**Primary criteria (required):**
- Drawdown >= 85% from high

**Secondary criteria (enhance returns):**
- Volume ratio < 0.75 (adds +400-500% to avg gain)
- Extended decline >= 12 months (marginal improvement when deep drawdown present)

**Optimal setup profile:**
- Down 85%+ from high
- Low volume (< 0.75x average)
- Expected: ~2,500% gain in ~250 days

### Simulated Scoring Validation

New score formula (max 7): drawdown(0-3) + decline(0-2) + low_vol(0-2)

| Score | Avg Gain | Speed | Count |
|-------|----------|-------|-------|
| 7 | 2,418% | 294 days | 538 |
| 5-6 | 2,000-2,300% | 480-500 days | 1,700+ |
| 0-2 | 740-830% | 1,000+ days | 1,100+ |

**Conclusion:** Simulated score shows clear monotonic relationship. Consider implementing.

### Entry Signal Candidates for Phase 4

1. **Volume spike trigger**: Low-setup-volume stocks have 5.85% gain/day velocity. Hypothesis: buy when 2x+ volume spike occurs.
2. **Deep drawdown immediate entry**: Deep + Low Vol averages 246 days to peak. Could enter on any pullback after setup confirmed.
3. **Range position confirmation**: Not yet analyzed. May add value for timing within setup.
