# Phase 2: Single Variable Analysis

*Generated: 2025-12-30 23:28:17*

## 2.1 Score 0 Investigation

**Question:** Why do Score 0 stocks have high gains (1,383%) and fast moves (375 days)?

### Comparison: Score 0 vs Score 6+

| Metric | Score 0 | Score 6+ | Interpretation |
| --- | --- | --- | --- |
| Count | 500 | 1372 | |
| Avg Drawdown | -0.24 | -0.87 | Lower = less beaten down |
| Avg Days Since High | 60.0 | 399.0 | Lower = shorter decline |
| Avg Range Position | 0.64 | -0.01 | Higher = not near lows |
| Avg % from SMA50 | -0.06 | -0.4 | Higher = above SMA |
| Avg Vol Ratio | 1.38 | 0.55 | Higher = more volume |

### Score 0 Data Completeness

| Field | NULL Count | % NULL |
| --- | --- | --- |
| drawdown | 478 | 94.1% |
| days_since_high | 478 | 94.1% |
| range_position | 478 | 94.1% |

## 2.2 Fast Movers Analysis

**Question:** What drives fast movers (< 1 month to peak)?

### Fast vs Medium vs Slow Movers

| speed | count | avg_gain | avg_score | avg_drawdown | avg_vol_ratio | avg_days_decline |
| --- | --- | --- | --- | --- | --- | --- |
| Fast (< 1mo) | 270 | 1942.0 | 5.1 | -0.92 | 2.69 | 328.0 |
| Medium (1-6mo) | 792 | 1386.0 | 5.3 | -0.91 | 2.28 | 368.0 |
| Slow (6mo+) | 4450 | 1507.0 | 4.8 | -0.69 | 1.98 | 315.0 |

### Fast Mover Characteristics

Fast movers (< 1 month to peak):
- Average drawdown: -0.92 (range: -1.0 to 0.0)
- Average volume ratio: 2.69
- Average days in decline: 328.0
- Average range position: 0.02

## 2.3 Volume Ratio Analysis

**Question:** Is vol_ratio (volume exhaustion) correlated with speed/gain?

### Volume Ratio vs Outcomes

| vol_bucket | count | avg_gain | avg_days_to_peak | avg_score |
| --- | --- | --- | --- | --- |
| < 0.5 (very low) | 748 | 2352.0 | 402.0 | 5.5 |
| 0.5-0.75 (low) | 559 | 1658.0 | 584.0 | 5.3 |
| 0.75-1.0 (below avg) | 599 | 1095.0 | 726.0 | 5.3 |
| 1.0-1.5 (above avg) | 1272 | 1323.0 | 790.0 | 4.6 |
| 1.5+ (high) | 2326 | 1414.0 | 728.0 | 4.7 |

### Volume Exhaustion Hypothesis

*Theory: Low volume at ignition = sellers exhausted = bigger bounce*

- Low volume (< 0.75) avg gain: 2055%
- High volume (>= 1.0) avg gain: 1382%
- **Lift: 1.49x**

## 2.4 Drawdown Analysis

**Question:** Do certain drawdown levels predict better outcomes?

### Drawdown Level vs Outcomes

| drawdown_bucket | count | avg_gain | avg_days_to_peak | avg_score |
| --- | --- | --- | --- | --- |
| < 30% down | 185 | 759.0 | 1045.0 | 1.9 |
| 30-50% down | 364 | 901.0 | 1104.0 | 3.2 |
| 50-70% down | 1063 | 965.0 | 985.0 | 4.8 |
| 70-85% down | 1408 | 1094.0 | 777.0 | 5.1 |
| 85%+ down | 2492 | 2123.0 | 412.0 | 5.3 |

### Drawdown Sweet Spot

| category | count | avg_gain | avg_days |
| --- | --- | --- | --- |
| Less beaten (< 50%) | 549 | 853.0 | 1084.0 |
| Sweet spot (50-70%) | 1063 | 965.0 | 985.0 |
| Crushed (70%+) | 3900 | 1752.0 | 543.0 |

## 2.5 Extended Decline Analysis

**Question:** Does length of decline predict outcomes?

### Decline Period vs Outcomes

| decline_period | count | avg_gain | avg_days_to_peak |
| --- | --- | --- | --- |
| < 1 month | 285 | 1218.0 | 932.0 |
| 1-3 months | 600 | 895.0 | 953.0 |
| 3-6 months | 484 | 1033.0 | 788.0 |
| 6-12 months | 1103 | 1545.0 | 611.0 |
| 12+ months | 3040 | 1723.0 | 615.0 |

## 2.6 Emerging Patterns

### Drawdown + Volume Combinations

| pattern | count | avg_gain | avg_days |
| --- | --- | --- | --- |
| Deep + Low Vol | 1154 | 2193.0 | 413.0 |
| Deep + Normal Vol | 3803 | 1398.0 | 707.0 |
| Shallow + Low Vol | 153 | 1015.0 | 989.0 |
| Shallow + Normal Vol | 394 | 792.0 | 1125.0 |

## Summary & Key Findings

### Confirmed Patterns

1. **Volume exhaustion works**: Low volume (< 0.75) produces 1.49x more gains than high volume. Very low volume (< 0.5) averages 2,352% gain.
2. **Deeper drawdown = bigger bounce**: Stocks down 85%+ average 2,123% gain vs 853% for stocks down < 50%.
3. **Longer decline = faster/bigger moves**: 12+ month declines average 1,723% gain in 615 days vs 1,218% gain in 932 days for < 1 month declines.
4. **Deep + Low Volume is optimal**: This combination averages 2,193% gain in just 413 days - the best of all patterns tested.

### Surprising Findings

1. **Score 0 mystery solved**: 94.1% of Score 0 stocks have NULL data (missing technicals), not failed criteria. The high gains (1,383%) are from data-incomplete stocks that happened to perform well.
2. **Fast movers have HIGH volume (2.69x)**: Counter-intuitive - fastest moves happen with elevated volume, not exhausted volume. Volume exhaustion may predict *magnitude*, not *speed*.
3. **No "sweet spot" for drawdown**: Expected 50-70% to be optimal, but data shows "more beaten = better" with no diminishing returns up to 85%+.

### Hypotheses for Phase 3

1. **Volume dynamics differ by timeframe**: Low volume may predict total gain, while volume *spike* triggers the move. Need to separate "setup" volume from "ignition" volume.
2. **Drawdown + Decline interaction**: Test if 85%+ drawdown AND 12+ month decline together outperforms either alone.
3. **Speed predictor**: What predicts < 1 month moves? Current data suggests deep drawdown + high volume at ignition. Need to test.
