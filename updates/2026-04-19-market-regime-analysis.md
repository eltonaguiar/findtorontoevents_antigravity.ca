# Market Regime Analysis: Pick Performance by `health_at_entry`

**Date:** 2026-04-19  
**Dataset:** `alpha_engine/data/closed_picks.json` (4,503 total records)  
**Analysis cohort:** 3,931 records with `health_at_entry` (`panic`, `caution`, or `warning`)

---

## Executive Summary

- **All regime-tagged records come from `quan_engine`** (`quan_engine_scalp`, `quan_engine_swing`, `quan_engine_position`).
- **All are crypto** (USDT perpetual pairs: BTC, ETH, SOL, ADA, etc.).
- **The book is 99.6% LONG** (3,917 LONG vs 14 SHORT). There is virtually no short exposure to compare.
- **No regime is consistently profitable** on average, but **panic (trending/bear) performs slightly better than caution (choppy)**.
- **`quan_engine_swing` is the regime-robust standout**: nearly breakeven in choppy markets and slightly profitable in panic markets.
- **`forward_wr` is remarkably well-calibrated** in `panic` and `caution`.

---

## 1. Overall Performance by `health_at_entry`

| Regime     | Count | WR    | PF   | Avg PnL | Total PnL |
|------------|-------|-------|------|---------|-----------|
| `panic`    | 3,087 | 29.2% | 0.99 | -0.160% | -494.1%   |
| `caution`  | 837   | 28.0% | 0.86 | -0.186% | -155.7%   |
| `warning`  | 7     | 14.3% | 0.16 | -0.250% | -1.8%     |

**Key finding:** None of the regimes are profitable on average. `panic` is the "least bad" environment—WR is 1.2 pp higher and average loss per trade is 0.026 pp smaller than in `caution`. `warning` is too sparse (7 trades) to draw conclusions.

---

## 2. Trending vs Choppy Markets

- **Trending proxy:** `panic` (bear/high-stress, directional down).
- **Choppy proxy:** `caution` (neutral/uncertain, low directional conviction).

| Market Type | Count | WR    | Avg PnL |
|-------------|-------|-------|---------|
| Trending    | 3,087 | 29.2% | -0.160% |
| Choppy      | 837   | 28.0% | -0.186% |

**Answer:** We perform slightly better in **trending (panic/bear)** markets than in **choppy (caution)** markets. The win rate is marginally higher and the per-trade bleed is smaller when the market is in a clear directional regime, even if that direction is down.

> **Caveat:** Because the book is almost entirely LONG, "better in panic" really means "our LONG picks bleed slightly less during bearish trending conditions than during choppy conditions." This may reflect that choppy markets generate more false breakouts and stop-outs.

---

## 3. LONG vs SHORT Performance by Regime

| Regime    | Direction | Count | WR    | Avg PnL |
|-----------|-----------|-------|-------|---------|
| `panic`   | LONG      | 3,087 | 29.2% | -0.160% |
| `panic`   | SHORT     | 0     | —     | —       |
| `caution` | LONG      | 823   | 27.7% | -0.188% |
| `caution` | SHORT     | 14    | 42.9% | -0.053% |
| `warning` | LONG      | 7     | 14.3% | -0.250% |
| `warning` | SHORT     | 0     | —     | —       |

**Findings:**
- **LONGs work marginally better in `panic` than in `caution`** (29.2% vs 27.7% WR).
- **The tiny SHORT sample in `caution` (14 trades)** shows a higher WR (42.9%) but still negative average PnL (-0.053%). It is far too small to claim SHORTs thrive in any regime.
- There are **zero SHORTs in `panic`**, so we cannot test the hypothesis that SHORTs thrive in bear/trending-down markets.

---

## 4. Crypto vs Non-Crypto by Regime

**Finding:** Every record with `health_at_entry` is a crypto pair (all symbols end in `USDT`: BTC, ETH, SOL, ADA, etc.).

There are **572 records without `health_at_entry`** (older `alpha_engine` picks), some of which are non-crypto, but they carry no regime tag. Consequently, **a crypto-vs-non-crypto split by regime is not possible with this dataset.**

If regime tagging is extended to the broader portfolio in the future, this comparison should be re-run.

---

## 5. Strategy-Level Regime Analysis

### Performance Summary

| Strategy              | Regime    | Count | WR    | Avg PnL |
|-----------------------|-----------|-------|-------|---------|
| `quan_engine_swing`   | `caution` | 37    | 18.9% | -0.008% |
| `quan_engine_swing`   | `panic`   | 62    | 35.5% | +0.007% |
| `quan_engine_scalp`   | `caution` | 787   | 28.8% | -0.197% |
| `quan_engine_scalp`   | `panic`   | 3,012 | 29.2% | -0.164% |
| `quan_engine_position`| `caution` | 13    | 38.5% | -0.254% |
| `quan_engine_position`| `panic`   | 13    | 30.8% | -0.215% |

### Best in Choppy (`caution`)
1. **`quan_engine_swing`** — nearly breakeven (-0.008% avg, 37 trades).
2. **`quan_engine_scalp`** — -0.197% avg, 787 trades.
3. **`quan_engine_position`** — -0.254% avg, 13 trades.

### Best in Panic (`panic`)
1. **`quan_engine_swing`** — actually profitable (+0.007% avg, 62 trades).
2. **`quan_engine_scalp`** — -0.164% avg, 3,012 trades.
3. **`quan_engine_position`** — -0.215% avg, 13 trades.

### Strategies Profitable Across Both Regimes

**None of the three strategies are profitable in both regimes.**

However, **`quan_engine_swing` is the closest to a regime-robust strategy:**
- It is **nearly breakeven in choppy markets** (-0.008%).
- It is **slightly profitable in panic markets** (+0.007%).
- Its win rate improves dramatically from caution (18.9%) to panic (35.5%), suggesting it benefits from clearer directional moves.

> **Answer to "Do we have certain strategies that thrive even in choppy market?"**
> 
> No strategy is outright profitable in choppy (`caution`) conditions, but **`quan_engine_swing` holds up best**—it loses virtually nothing on average (-0.008%) compared to the scalping and position variants which bleed ~0.20% per trade. If the goal is to reduce choppy-market drawdowns, swing trades are the preferred vehicle.

---

## 6. Exit Reason by Regime

| Regime    | TP Hit  | SL Hit  | Time Exit | Other |
|-----------|---------|---------|-----------|-------|
| `panic`   | 24.3%   | 45.4%   | 30.3%     | 0.0%  |
| `caution` | 22.1%   | 47.2%   | 30.7%     | 0.0%  |
| `warning` | 14.3%   | 42.9%   | 42.9%     | 0.0%  |

*("Other" = `TIME_EXIT` in this dataset.)*

**Findings:**
- **SLs are hit slightly more often in `caution` (47.2%) than in `panic` (45.4%)**.
- **TPs are hit slightly more often in `panic` (24.3%) than in `caution` (22.1%)**.
- Time exits are stable at ~30% across the two main regimes.

This aligns with the overall result: in choppy markets, picks are slightly more likely to get stopped out before reaching target, whereas in trending panic markets, directional follow-through is marginally better.

---

## 7. `forward_wr` Calibration by Regime

`forward_wr` is drawn from `elite_breakdown._forward_wr_raw` (already on a 0–1 scale, converted to %).

| Regime    | Count | Predicted WR | Actual WR | Diff (Actual − Predicted) |
|-----------|-------|--------------|-----------|---------------------------|
| `panic`   | 3,087 | 29.0%        | 29.2%     | +0.2 pp                   |
| `caution` | 837   | 28.8%        | 28.0%     | −0.8 pp                   |
| `warning` | 7     | 29.3%        | 14.3%     | −15.0 pp                  |

**Findings:**
- **`panic`:** Calibration is excellent. The model predicts 29.0% and the realized WR is 29.2%.
- **`caution`:** Slightly over-optimistic by 0.8 percentage points.
- **`warning`:** Severely over-optimistic, but the sample is only 7 trades.

**Conclusion:** `forward_wr` is neither systematically over-optimistic nor pessimistic in the two large regimes. It is a reliable prior for expected win rate in both `panic` and `caution` environments.

---

## Bottom-Line Answers

### Do we perform better on trending markets? bear? bull? choppy?
- **Trending (panic/bear) > choppy (caution).** Our LONG picks have a slightly higher win rate and smaller average loss in panic than in caution.
- There is no "bull" regime tag in this dataset, so we cannot compare bull vs bear directly.

### Do we have certain strategies that thrive even in choppy market?
- **No strategy is profitable in choppy (`caution`) conditions.**
- **`quan_engine_swing` is the most resilient:** it is essentially breakeven (-0.008% average PnL) in choppy markets and turns profitable (+0.007%) when the market enters panic. It is the clear choice for regime-robust exposure.

---

## Data Limitations

1. **Source concentration:** All 3,931 regime-tagged records are from `quan_engine`. Conclusions may not generalize to `alpha_engine` or other pick generators.
2. **Directional skew:** 99.6% of trades are LONG. SHORT-side conclusions are impossible.
3. **Asset-class concentration:** 100% of regime-tagged picks are crypto. Non-crypto regime performance is unknown.
4. **Strategy diversity:** Only three strategies (`quan_engine_scalp`, `quan_engine_swing`, `quan_engine_position`) appear in the tagged set.
5. **`warning` sample:** Only 7 trades—treated as illustrative only.
