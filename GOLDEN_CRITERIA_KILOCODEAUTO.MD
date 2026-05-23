# GOLDEN CRITERIA — Crypto Picks Pattern Analysis
**Generated:** 2026-03-27 | **Data:** 1,011 closed picks + 54 active picks + winner_analysis.json

---

## TL;DR — What Actually Predicts Wins?

| Rank | Metric | Spearman | IC | Q1→Q4 WR Spread | Verdict |
|------|--------|----------|-----|------------------|---------|
| 1 | strategy_fwd_wr (forward win rate) | +0.253 | +0.239 | 19.1% → 56.2% (+37.1%) | **STRONGEST PREDICTOR** |
| 2 | sb_strategy_track_record | +0.108 | +0.171 | 1.8% → 98.8% (+97.0%) | **MASSIVE spread** |
| 3 | sb_forward_wr | +0.117 | +0.163 | 1.8% → 97.0% (+95.2%) | **MASSIVE spread** |
| 4 | sb_technical_alignment | +0.076 | +0.144 | 12.6% → 81.4% (+68.8%) | Strong Q4 lift |
| 5 | technical_buy_tfs | +0.087 | +0.183 | 12.7% → 86.1% (+73.4%) | Strong but binary |
| 6 | sb_ml_score | -0.084 | -0.152 | 3.4% → 47.0% (+43.6%) | Inverted! High ML = risky |
| 7 | confidence | -0.042 | -0.105 | 4.0% → 42.8% (+38.8%) | Slightly inverted |
| 8 | elite_score (overall) | +0.106 | — | 26.6% → 38.2% | **Weak but positive** |

---

## 1. ELITE SCORE — Does It Predict PnL?

**Correlation: r = +0.106 (WEAK positive)**

| Score Range | n | Win Rate | Avg PnL | Median PnL |
|-------------|---|----------|---------|------------|
| 0-19 | 199 | 26.6% | -0.218% | -0.052% |
| 20-39 | 195 | 12.8% | -0.167% | -0.150% |
| 40-59 | 549 | 30.6% | -0.123% | -0.127% |
| 60-79 | 55 | 38.2% | -0.043% | -0.003% |
| 80-100 | 0 | — | — | — |

**Verdict:** Elite score has a weak positive correlation. 60+ scores show ~38% WR vs ~27% for low scores. But the spread is modest — elite score alone is NOT sufficient. The **sub-components** matter more than the aggregate.

### Elite Breakdown — Which Sub-Scores Matter?

| Component | Win Avg | Loss Avg | Correlation w/ PnL |
|-----------|---------|----------|-------------------|
| forward_wr | 3.9 | 3.9 | +0.055 |
| _strategy_top_symbol_pnl_pct | 26.0 | 22.8 | +0.102 |
| regime_match | 0.2 | 0.1 | +0.041 |
| ml_score | 15.0 | 15.4 | +0.062 |
| strategy_concentration_penalty | -0.9 | -0.5 | -0.113 |

---

## 2. TRACK RECORD — "track" Field Analysis

**Active picks:** 53/54 have `track_record = None` (empty). Only 1 pick has "2t 0%" (2 trades, 0% WR).

**From winner_analysis.json:** `sb_strategy_track_record` is ranked **#18** with the **largest Q1→Q4 spread of +97.0%** (Q1 WR: 1.8%, Q4 WR: 98.8%).

**This is critical:** When track_record data EXISTS and is strong, it's the single biggest differentiator between winners and losers. But most picks have it EMPTY.

**The "??" icons:** These appear when `track_record`, `strong_signal`, or `htf_confirmation` are `null`/`None`. The dashboard renders "?" for missing data. This is **metadata incompleteness** — the system generates picks before these fields are populated.

---

## 3. STRONG SIGNAL — "strong" Field Analysis

**Active picks:** 53/54 have `strong_signal = None`. 1 has `False`.

**No statistical sample** available for strong_signal=True in closed picks. This field is essentially **unpopulated** across the dataset.

**Recommendation:** This field needs to be computed and populated. If it correlates with forward-validated strategies, it could be a powerful filter.

---

## 4. HTF CONFIRMATION — Does Higher Timeframe Alignment Help?

**Active picks:** 8/54 have `htf_confirmation = "neutral"`, 46/54 have `None`.

**From winner_analysis.json:**
- `technical_buy_tfs` ranked **#2** (Spearman +0.087, IC +0.183)
- Q1→Q4 spread: **+73.4%** (12.7% → 86.1%)
- `sb_technical_alignment` ranked **#3** (Spearman +0.076, IC +0.144)
- Q1→Q4 spread: **+68.8%** (12.6% → 81.4%)

**Verdict:** HTF/technical alignment is the **2nd strongest predictor** after forward WR. When buy signals align across multiple timeframes, WR jumps from ~13% to ~81-86%.

**Multi-timeframe (MTF) in smart_picks:**
- `mtf_aligned: True` with `mtf_agreement_ratio: 2/3` shows moderate alignment
- Picks with MTF alignment score higher in smart_score

---

## 5. A-VIABLE STRATEGY — Does `_A_` in Strategy Name Help?

**Only 3 closed picks** had `_A_` in strategy name:
- `ml_enhanced_LTCUSDT_4h_A_xgboost`: LOST (-0.024%)
- `ml_enhanced_APTUSDT_4h_A_xgboost`: LOST (-0.035%)
- `ml_enhanced_AVAXUSDT_4h_A_xgboost`: LOST (-0.039%)

**WR: 0% (0/3)** — but sample size is too small to conclude.

**Active picks with A-viable:** LINKUSDT, SUIUSDT, ONDOUSDT (via enhanced_ml_A_xgboost) are currently active.

**Verdict:** Insufficient data. The `_A_` variant (likely "Variant A" of an xgboost model) needs more closed trades to evaluate. Monitor current active picks.

---

## 6. MULTI-AGREE (Confluence Count) — More Strategies = Better?

| # Strategies | n | Win Rate | Avg PnL |
|-------------|---|----------|---------|
| 1 | 1 | 100% | +0.050% |
| 2 | 127 | 27.6% | -0.210% |
| 3 | 452 | 14.6% | -0.163% |
| 4 | 190 | 37.4% | -0.172% |
| 5 | 132 | 44.7% | -0.077% |
| 6 | 41 | 31.7% | -0.076% |
| 7 | 3 | 66.7% | +0.113% |

**Verdict:** YES — more strategies agreeing = higher WR. The jump from 3 strategies (14.6%) to 5 strategies (44.7%) is dramatic. **5+ strategies agreeing = golden zone.** But 7-strategy agreement has only 3 samples.

**From winner_analysis.json:** `agreement_count` ranked #19 with Q1→Q4 spread of **+84.8%** (0% → 84.8%).

---

## 7. TRADING MODE — What Works?

| Mode | n | Win Rate | Avg PnL |
|------|---|----------|---------|
| SWING | 78 | 44.9% | +0.013% |
| (empty) | 65 | 46.2% | -0.031% |
| POSITION | 13 | 0.0% | -0.038% |
| SCALP | 855 | 24.8% | -0.171% |

**Verdict:** SWING mode is the only profitable mode (+0.013% avg PnL, 44.9% WR). SCALP dominates volume (855 trades) but loses money (24.8% WR, -0.171% avg). **Avoid scalps, favor swings.**

---

## 8. SOURCE SYSTEM — Which Systems Win?

| Source | n | Win Rate | Avg PnL |
|--------|---|----------|---------|
| multi_asset_copytrader | 21 | 57.1% | +0.026% |
| copy_trader_binance | 9 | 55.6% | +0.011% |
| rapid_fire | 13 | 76.9% | -0.174% |
| quan_engine | 946 | 26.1% | -0.154% |

**Verdict:** Copy trader systems are the only profitable sources. The main `quan_engine` has 26.1% WR. **Copy trading = real edge.**

---

## 9. EXIT REASON — What Kills Trades?

| Exit | n | WR | Avg PnL |
|------|---|-----|---------|
| TP | 163 | 100% | +0.286% |
| TP_HIT | 23 | 100% | +0.046% |
| FORCE_CLOSED_TOXIC | 15 | 100% | +0.050% |
| TIME_EXIT | 326 | 19.6% | -0.067% |
| SL | 437 | 0% | -0.393% |
| SL_HIT | 23 | 0% | -0.129% |

**437 trades (43%) hit stop loss** — avg loss -0.393%. This is the primary PnL drain.

---

## 10. CONFIDENCE — Does Higher Confidence Help?

| Confidence | n | Win Rate | Avg PnL |
|-----------|---|----------|---------|
| 0.5-0.6 | 300 | 35.7% | -0.175% |
| 0.6-0.7 | 624 | 21.5% | -0.139% |
| 0.7-0.8 | 71 | 35.2% | -0.088% |
| 0.8+ | 2 | 50.0% | -0.001% |

**Verdict:** Slightly INVERTED. Higher confidence doesn't strongly predict wins. 0.7-0.8 range performs similarly to 0.5-0.6.

---

## 11. HEALTH AT ENTRY

| Health | n | Win Rate | Avg PnL |
|--------|---|----------|---------|
| warning | 2 | 50.0% | +0.018% |
| unknown | 65 | 46.2% | -0.031% |
| caution | 55 | 60.0% | -0.044% |
| panic | 889 | 24.0% | -0.162% |

**Verdict:** "caution" health = 60% WR (best). "panic" = 24% WR (worst). **Don't trade during panic regimes.**

---

## THE GOLDEN CRITERIA — A Composite Filter

Based on all analysis, the **highest-probability picks** should meet ALL of:

### Tier 1 (Must Have)
1. **Strategy forward WR ≥ 50%** — #1 predictor (Q4 WR: 56.2%)
2. **5+ strategies agreeing (multi-agree)** — WR jumps to 44.7%+ 
3. **SWING mode** — Only profitable mode (+0.013% avg PnL)
4. **Health ≠ "panic"** — Panic regime = 24% WR killer

### Tier 2 (Strong Indicators)
5. **Technical alignment score high** — Q4 = 81.4% WR
6. **HTF confirmation ≠ neutral/empty** — Multi-TF alignment = 73-86% WR
7. **Elite score ≥ 60** — 38.2% WR vs 27% for low scores
8. **Track record exists and is positive** — Largest Q1→Q4 spread (+97%)

### Tier 3 (Nice to Have)
9. **Copy trader source** — 55-57% WR, only profitable sources
10. **Confidence 0.7-0.8** — Slightly better than 0.5-0.7
11. **Strategy has _A_ or proven variant** — Monitor, insufficient data

---

## METADATA GAPS — What's Missing?

| Field | Populated % | Impact |
|-------|------------|--------|
| track_record | 2% (1/54 active) | **HUGE** if populated — largest Q1→Q4 spread |
| strong_signal | 2% (1/54 active) | Unknown — needs computation |
| htf_confirmation | 15% (8/54 active) | **Strong predictor** — needs population |
| elite_score | 98% | Good coverage |
| confidence | 100% | Good coverage |
| strategy_fwd_wr | 95% | Good coverage |

**The "??" icons appear because track_record, strong_signal, and htf_confirmation are NULL for most picks.** The dashboard renders "?" for missing data.

---

## ACTIONABLE RECOMMENDATIONS

1. **Populate track_record** for all strategies — it has the largest predictive spread (+97% Q1→Q4)
2. **Compute strong_signal** from forward WR + technical alignment
3. **Populate htf_confirmation** for all picks — 2nd strongest predictor category
4. **Filter out SCALP mode** — 24.8% WR, -0.171% avg PnL
5. **Filter out "panic" health** — 24% WR vs 60% for caution
6. **Require 5+ multi-agree** — WR jumps from 15% to 45%
7. **Focus on SWING mode** — only profitable mode
8. **Prioritize copy trader strategies** — only profitable source systems
9. **Current active "A-viable" picks** (LINK, SUI, ONDO) — track closely, insufficient historical data
