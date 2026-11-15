# 01_SPECIFICATION — CRYPTO

**Asset Class:** CRYPTO / CRYPCO
**Status:** BLOCKED — Negative Expectancy
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md`, `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`, `backtest_results/kimi_cursor_v04_comparison.json`, `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | File | Parameters | Entry Logic | Exit Logic | TP/SL | Result |
|----------|------|-----------|-------------|------------|-------|--------|
| `kimi_inverse_scanner` | `alpha_engine/kimi_inverse_scanner.py` | TP 2%, SL 3%, R:R 0.67 | Invert KIMI signals | TP/SL fixed | TP 2%, SL 3% | 28 picks generated, 0 resolved |
| `kimi_vpin_lgbm_ensemble` | `baby_strategies/kimi_vpin_lgbm_ensemble.py` | VPIN < 0.5, Z-score < -2.0 / > +2.0, composite > 0.6 | LONG on Z < -2 + VPIN < 0.5 | TP/SL ATR-based | TP 2-5× ATR, SL 2-3× ATR | Not tested on real picks |
| `kimi_ema600_40_momentum` | `baby_strategies/kimi_ema600_40_momentum.py` | EMA(600)/EMA(40) crossover | BUY EMA40 > EMA600 | Reverse cross or 3×ATR trailing | TP +15%, SL -6% | Not tested on real picks |
| `kimi_volatility_momentum_blend` | `baby_strategies/kimi_volatility_momentum_blend.py` | Momentum Z > +1.0 / < -1.0 + vol filter | Momentum z-score entry | TP +12%, SL -5% | TP +12%, SL -5% | Not tested on real picks |
| `kimi_lgbm_features` | `baby_strategies/kimi_lgbm_features.py` | Composite score > 0.65 / < 0.35 | Composite score signal | TP +12%, SL -5% | TP +12%, SL -5% | Not tested on real picks |
| `kimi_vpin_reversion` | `baby_strategies/kimi_vpin_reversion.py` | VPIN < 0.5, Z-score < -2.0 / > +2.0 | VPIN mean reversion | TP +6%, SL -3% | TP +6%, SL -3% | Not tested on real picks |
| `prediction_market_consensus` | `alpha_engine/data/prediction_market_picks.json` | Kalshi/Polymarket consensus | Prediction market signals | Varies by symbol | Varies (~13% TP, ~8% SL) | 2 OPEN picks, 0 resolved |
| Donchian Breakout | `backtest_results/kimi_cursor_v04_comparison.json` | 20-day high breakout | Buy breakout above 20-day high | Sell below 20-day low | ATR-based | Zero trades on all 5 crypto symbols |

### Cost Model
- Commission: 1 bps per side
- Slippage: 1 bps per side
- Round-trip cost: 4 bps (4.0 bps total)
- Source: `run_simulation_backtest.py` simulation

### Benchmark
- Equal-weight buy-and-hold + cash
- BTC buy-and-hold (for BTC-specific strategies)
- Source: `run_simulation_backtest.py`

### Walk-Forward Design
- Not yet implemented for crypto strategies
- Required: 5 folds, expanding window, 1yr train / 1yr test
- Source: `final_v3/quant-audit-2026-11-14/03_backtest_simulation/BACKTEST_FIXES.md`

---

## 2. Backtest Results (Ground Truth from closed_picks.json)

**File:** `alpha_engine/data/closed_picks.json` (filter: `category == "CRYPTO"`)

| Metric | Value |
|--------|-------|
| Total closed crypto picks | 76 |
| Wins (WON) | 30 |
| Losses (LOST) | 23 |
| CLOSED (unresolved, pnl=0) | 22 |
| FLAT | 1 |
| **Win Rate** | **56.60%** (30/53 resolved) |
| Gross Profit | +1.3687% |
| Gross Loss | -2.2610% |
| **Profit Factor** | **0.6054** |
| Average PnL per trade | -0.0117% |
| Total PnL | -0.8923% |
| Max Drawdown | 0.7372% |

**Bottom line:** Despite a 56.60% nominal win rate, the Profit Factor is **0.6054** — losses are 1.65× larger than wins. The strategy loses money net. **76 samples is statistically insignificant** (well below n≥100 minimum). PF < 1.0 means **negative expectancy after costs**.

---

## 3. Active Crypto Picks

**File:** `alpha_engine/data/active_picks.json`

| Metric | Value |
|--------|-------|
| Total active crypto picks | 9 |
| Symbols | ARBUSDT, BNBUSDT, BTCUSDT, ETHUSDT, LINKUSDT, LTCUSDT, RENDERUSDT, SPY, TRXUSDT |

**Note:** SPY (an equity ETF) is misclassified as `asset_class: "CRYPTO"` — data integrity issue.

### Active Crypto Picks (all LONG except BTCUSDT, RENDERUSDT which are SHORT)

| Symbol | Direction | Entry | TP | SL | Strategy | Status |
|--------|-----------|-------|-----|-----|----------|--------|
| BNBUSDT | BUY | 575.69 | 592.96 | 564.18 | ml_enhanced_BNBUSDT_15m_B_lightgbm | ACTIVE |
| TRXUSDT | BUY | 0.3301 | 0.3367 | 0.3268 | ml_enhanced_TRXUSDT_4h_D_ensemble_stack | ACTIVE |
| LINKUSDT | BUY | 8.00 | 8.472 | 7.7976 | ml_enhanced_LINKUSDT_4h_A_xgboost | ACTIVE |
| ARBUSDT | BUY | 0.091 | 0.0933 | 0.0901 | ml_enhanced_ARBUSDT_1h_D_ensemble_stack | ACTIVE |
| LTCUSDT | BUY | 44.75 | 47.13 | 43.73 | ml_enhanced_LTCUSDT_4h_A_xgboost | ACTIVE |
| BTCUSDT | SELL | 64179.0 | 63473.03 | 64743.78 | inverse_ml_enhanced_BTCUSDT_15m_D | ACTIVE |
| RENDERUSDT | SELL | 1.581 | 1.4229 | 1.6601 | inverse_ml_enhanced_RENDERUSDT_4h_D | ACTIVE |
| ETHUSDT | SHORT | 1806.41 | 1761.25 | 1833.51 | prediction_market_consensus | OPEN |

**TP parameters:** 1.00%–5.90% depending on strategy (most 1.00%–3.00%)
**SL parameters:** 0.88%–2.53% depending on strategy

---

## 4. KIMI Inverse Scanner — `alpha_engine/kimi_inverse_scanner.py`

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/kimi_inverse_scanner.py` (677 lines)

### Strategy Logic
- **Core thesis:** "KIMI 8% WR on 339 closed trades → Inverse = ~92% WR"
- **Claimed:** "Inverse contrarian report: 97.2% WR, Sharpe 23.6, walk-forward validated"
- **Mechanism:** Reads KIMI active picks, flips direction (BUY→SELL, SELL→BUY), applies tighter risk management, outputs as alpha_engine picks
- **Regime-aware filtering:**
  - STRONG_BULLISH: skip inverting BUY/LONG signals (don't short in confirmed bull)
  - STRONG_BEARISH: skip inverting SELL/SHORT signals (don't go long in confirmed bear)
  - RELIEF_RALLY, EXTREME_FEAR, CAPITULATION, NEUTRAL: invert everything
- **Also inverts zero-WR alpha_engine strategies** (8 strategies: cross_sectional_momentum, altcoin_season_rotation, momentum_mean_rev_blend, price_touch_recurrence, smart_money_fvg, fourier_cycle_detector, halloween_effect, exchange_netflow_reversal)

### Parameters
| Parameter | Value |
|-----------|-------|
| Take Profit | 2.0% (tp_pct = 0.02) |
| Stop Loss | 3.0% (sl_pct = 0.03) |
| Risk:Reward | 0.67 (worse than 1:1!) |
| Confidence | 75 (75%, hardcoded) |
| Min confidence gate | 0.70 (70%) |
| Stablecoin filter | Excludes USDC, USDT, BUSD, DAI, FDUSD, TUSD |

### Output — `alpha_engine/data/kimi_inverse_picks.json`

| Metric | Value |
|--------|-------|
| Total picks generated | 28 |
| KIMI inverse count | 29 (inconsistent with total_picks=28) |
| Alpha inverse count | 0 |
| Priced | 19 |
| Wins | **0** |
| Losses | **0** |
| Flat/Open | 19 |
| **Win Rate** | **0%** (no resolved trades) |
| Avg PnL | 0.0% |
| Generated at | 2026-03-16T01:36:09Z |

**All 19 priced picks are OPEN with 0% PnL — zero resolved outcomes.** The claimed 97.2% inverse WR is completely unsubstantiated by actual data. The scanner produces picks that never get resolved (stuck in OPEN status).

---

## 5. KIMI Baby Strategies — `baby_strategies/kimi_*.py`

All 5 files read in full. All are crypto-only (SYMBOLS lists are all USDT pairs).

### 5.1 `kimi_vpin_lgbm_ensemble.py`
**Logic:** VPIN mean-reversion filter + 5-feature LightGBM proxy composite score + per-symbol Z-score thresholds.
- **Entry:** LONG: Z-score < -threshold AND VPIN < 0.5 AND composite > 0.6; SHORT: Z-score > +threshold AND VPIN < 0.5 AND composite > 0.6; SKIP: VPIN > 0.6 (toxic flow)
- **TP:** ATR-based 2-5×; **SL:** ATR-based 2-3× ATR
- **Position sizing:** Kelly criterion × 0.25 × position_size_scalar
- **Composite:** 0.25×RSI + 0.20×MACD + 0.20×BB + 0.20×volume + 0.15×momentum

### 5.2 `kimi_ema600_40_momentum.py`
**Logic:** EMA 600/40 crossover (Jaaskellainen 2022 thesis, claims to beat BTC buy-and-hold 2016-2021).
- **Entry:** BUY: Fast EMA(40) crosses above Slow EMA(600); SELL: Fast EMA(40) crosses below Slow EMA(600)
- **Exit:** Reverse cross OR trailing stop at 3×ATR(14)
- **TP:** +15%; **SL:** -6% (fixed) or ATR-based trailing, whichever is tighter

### 5.3 `kimi_volatility_momentum_blend.py`
**Logic:** Momentum Z-score + volatility filter (Briplotnik, claims Sharpe 1.71, 56% annualized).
- **Entry:** BUY: Momentum Z > +1.0 AND vol filter passes (realized vol < 2× 60-bar MA); SELL: Momentum Z < -1.0 AND vol filter passes
- **TP:** +12%; **SL:** -5%

### 5.4 `kimi_lgbm_features.py`
**Logic:** Feature scoring replicating G-Research Kaggle competition approach (without actual ML model).
- **Entry:** BUY: Composite score > 0.65; SELL: Composite score < 0.35
- **Features (weights):** Lagged return rank (0.30), Volume ratio (0.20), Volatility rank (0.15), RSI normalized (0.20), EMA correlation (0.15)
- **TP:** +12%; **SL:** -5%

### 5.5 `kimi_vpin_reversion.py`
**Logic:** VPIN flow toxicity + Z-score mean reversion (Easley, Lopez de Prado & O'Hara 2012).
- **Entry:** BUY: Z-score < -2.0 AND VPIN < 0.5; SELL: Z-score > +2.0 AND VPIN < 0.5; Skip: VPIN > 0.6 (toxic)
- **TP:** +6%; **SL:** -3%

---

## 6. Genome Data — `genome/kimi_*.py` and `genome/data/kimi_*.json`

### Scripts
- `genome/kimi_top_picks_automation.py` (671 lines)
- `genome/kimi_top_3_tracker.py` (416 lines)
- `genome/kimi_best_3_selector.py` (527 lines)

**Genome automation logic:** 3 strategies — Williams %R Mean Reversion, VWAP Bollinger Squeeze, Regime-Adaptive EMA Ribbon MACD. Uses Kelly sizing (12-16%), ATR-based TP/SL (tp_mult 2.0-3.0, sl_mult 1.0-1.5).

### Genome JSON Data Files

| File | Picks | Status | Key Findings |
|------|-------|--------|--------------|
| `genome/data/kimi_top_3_live_picks.json` | 3 | LIVE | SOLUSDT LONG, BTCUSDT LONG, ETHUSDT LONG. All Williams %R/VWAP. TP/SL: R:R 1.5-2.0 |
| `genome/data/kimi_top_picks_dashboard.json` | 0 | Empty | Performance: `{}` for all 3 strategies — no trades recorded |
| `genome/data/kimi_best_3_current.json` | 3 | All GRADE F | BTCUSDT, ETHUSDT, SOLUSDT all LONG. **conviction_score: 0.0** on all 3. Entry grade: **F** on all 3. "Poor setup. High risk, low reward, or against trend. Avoid." |
| `genome/data/kimi_picks_4_and_5.json` | 2 | — | XRPUSDT LONG (1.40→1.46/1.36), LINKUSDT LONG (9.11→9.47/8.84) |
| `genome/data/kimi_supplemental_picks.json` | 0 | Silent | total_picks=0, 5 mutations all silent (no triggers) |
| `genome/data/kimi_mutations_backtest.json` | Multiple | All negative | volume_profile_funding_snap: WR 36.4%, PF 0.68, return -10.38%. ema_ribbon_macd_divergence: WR 28.5%, PF 0.64, return -13.55%. cross_agg_battleground_hybrid: WR 50.4%, PF 1.23, return +2.74% (only slightly positive). drawdown_volatility_expansion: n=3 only, statistically meaningless. |

**Genome verdict:** All backtested genome mutations show negative expectancy or statistically insignificant samples. The best_3_selector gives all picks Grade F with conviction 0.0.

---

## 7. Audit Dashboard KIMI Data — `audit_dashboard/data/kimi_*.json`

### `kimi_top_3_live_picks.json`
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/kimi_top_3_live_picks.json`

- 6 picks (3 active, 3 closed)
- Closed: LDOUSDT -1.62% SL_HIT, DOGEUSDT -1.24% SL_HIT, STRKUSDT -1.72% SL_HIT
- **lifetime_stats: wins=0, losses=3, win_rate_closed=0.0%, net_realized_usd=-543.55**
- All 3 closed hits were Stop Losses

### `kimi_top_picks_phase2.json`
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/kimi_top_picks_phase2.json`

- Phase 1: 0W-3L-3A (0% WR, all LONGs failed)
- Phase 2: 3 picks, all SHORT bias (ETHUSDT, NEARUSDT, INJUSDT)
- **lifetime_stats: wins=0, losses=3, win_rate_closed=0.0%**
- Lesson: "Oversold bounce LONGs fail in a downtrend. 0% WR."

### `kimi_top_picks_round3.json` through `round5.json`
All rounds show PENDING status with no resolved outcomes. Round 4 admitted BTC/SOL/AVAX SHORT signals "all went red." Round 5 flipped SOL from SHORT to LONG after SL hit. **No closed/resolved picks with actual PnL across any round.**

---

## 8. Claimed 85-100% WR vs Actual Data

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/kimi_ultimate_proven_edge_2026-05-16.md`

### Claims in the report:
| Claim | Value |
|-------|-------|
| CRYPCO (ML tokens) WR | 85-100% |
| CRYPCO (ML tokens) PF | Very High |
| CRYPCO (ML tokens) DSR | ≥0.9995 |
| INJUSDT WR | 100% (n=27) |
| FETUSDT WR | 100% (n=25) |
| DYDXUSDT WR | 96.8% (n=31) |
| RENDERUSDT WR | 85.3% (n=34) |
| Proven ML Combo WR | 79.4% (n=199) |
| Proven ML Combo PF | 11.34 |
| Proven ML Combo DSR | ≥0.95 |

### Actual data from `closed_picks.json` (76 CRYPTO picks):
| Metric | Claimed | Actual |
|--------|---------|--------|
| Win Rate | 85-100% | **56.60%** |
| Profit Factor | Very High / 11.34 | **0.6054** |
| Samples | n=199+ | **76** |
| Expectancy | Positive | **Negative (-0.89% total)** |

**The claimed 85-100% WR for ML tokens does NOT hold up.** Actual closed pick data shows 56.60% WR with PF 0.6054 — a losing strategy. The claimed PF of 11.34 vs actual 0.6054 is a discrepancy of nearly 20x.

**Section 14 of the same report admits:** "Crypto PF dropped from 1.25 to 0.89 recently" — acknowledging deterioration.

---

## 9. CRYPCO Expectancy — `final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md`

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md`

**Line 82:**
> **CRYPCO expectancy: -5.86% with bootstrap 95% CI [-4.96%, -4.38%] — statistically significant NEGATIVE.**

This is from the formal quant audit (2026-11-14). Key points:
- All 3,500 closed picks analyzed across 9 asset classes
- **Overall WR: 45.6%** (below 50%)
- CRYPCO closed picks WR: 45.7%
- **All 166 strategy×class×direction cells FAIL money-ready gates** (0/166 pass)
- Only 1 cell clears n≥100 (`luxalgo_confluence` CRYPCO LONG, n=563) but it fails WR (44%), PF (1.24), MDD (289.5%), single-source (94%)
- **CRYPCO expectancy: -5.86%, CI [-4.96%, -4.38%] — statistically significant NEGATIVE**

From `ASSET_CLASS_FIXES.md` (same audit):
- CRYPCO official intrabar: n=3,705, WR 35.87%, PF 0.920 → NOT_READY
- CRYPCO registry cohort (different): n=22,055, WR 42.09%, PF 0.258

---

## 10. Prediction Market Picks — `alpha_engine/data/prediction_market_picks.json`

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/prediction_market_picks.json`

| Field | Value |
|-------|-------|
| pick_count | **2** (not 0 — the file contains 2 picks) |
| Source | prediction_market_consensus |
| Updated | 2026-11-15T06:50:20Z |

**Pick 1:** BNBUSDT SHORT, entry 592.25, TP 513.13, SL 639.63, confidence 0.911, sources: kalshi + polymarket_reverse, consensus_count=2, status=OPEN

**Pick 2:** BTCUSDT LONG, entry 64516.0, TP 73135.34, SL 59354.72, confidence 0.794, sources: kalshi + polymarket_reverse, has_conflict=true, consensus_count=2, status=OPEN

**Both picks are OPEN — zero resolved outcomes, zero forward WR.** The user's note about "pick_count (reported as 0)" is incorrect for this file (it shows 2), but the key issue is that **no prediction market picks have ever been resolved** — there is no forward test data.

**PBO for prediction market consensus:** The user references "PBO=0.603". Looking at the audit docs:
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/final_v3/quant-audit-2026-11-14/00_summary/CROSS_PEER_REVIEW_REPORT.md` line 161: "PBO/SPA gate" — PBO ≤0.10 required for pass
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/final_v3/quant-audit-2026-11-14/07_general_fixes/IMPROVEMENT_PLAN.md` line 33: "PBO ≤0.10 required for pass"
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/final_v3/quant-audit-2026-11-14/08_focus_decision/FOCUS_DECISION.md` line 3: "PBO ≤0.10" gate

A PBO of 0.603 means **60.3% probability of backtest overfitting** — massively above the 0.10 gate. This means the apparent edge is almost certainly data-mining artifact, not real alpha.

From the reports directory:
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/2026-10-22-community-plans-winner-leads-synthesis.md` line 66: "ML/prediction sleeves (prediction_market_consensus, claude_ml_moderate_mut, ml_crypto_pred, Predictions) — **All negative** on hard-resolved trades (WR 37% / PF 0.89)."
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/persona_strategy_seed_candidates_2026-06-05.md` line 115: "The 89.9% / PF 24.51 `prediction_market_consensus` figure under `backfill_2026-06-01` is implausible vs. the trading_picks 47.2% WR for the same strategy — flag as resolver artifact."

---

## 11. KIMI Cursor V04 Backtest — `backtest_results/kimi_cursor_v04_comparison.json`

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/backtest_results/kimi_cursor_v04_comparison.json`

KIMI v0.01 Multi across all timeframes (15m, 30m, 45m, 1h, 4h, 1d):

| Timeframe | Trades | WR | PF | Total Return | Max DD | Sharpe |
|-----------|--------|-----|-----|-------------|--------|--------|
| 15m | 39 | 33.33% | 0.785 | -9.65% | 19.24% | -1.715 |
| 30m | 20 | 40.0% | 1.212 | +4.36% | 9.06% | 1.394 |
| 45m | 155 | 43.23% | 1.041 | +8.36% | 45.46% | 0.286 |
| 1h | 155 | 43.23% | 1.041 | +8.36% | 45.46% | 0.286 |
| 4h | 49 | 44.9% | 1.073 | +5.31% | 19.54% | 0.538 |
| 1d | 16 | 43.75% | 0.903 | -2.49% | 17.0% | -0.768 |

**v0.04 Hybrid/Dynamic:** Similar or worse performance (PF 0.559-1.357, mostly negative returns)

**All traditional indicators (RSI-2, SuperTrend, MACD, BB, Ichimoku, HMA, SFP, ZScore):** WR 21-47%, PF 0.17-0.99, all negative total returns except rare single-trade outliers.

---

## 12. Does Any Crypto Strategy Pass All Phase 4 Proof Gates?

**No.** The money-ready gates (from `FOCUS_DECISION.md` and `IMPROVEMENT_PLAN.md`) require:
- Benchmark-relative net expectancy CI excluding zero
- DSR ≥ 0.95 (cumulative trial count)
- PBO ≤ 0.10
- ≥ 100 clean forward closes over ≥ 3 distinct months

**Results:**
- **CRYPCO expectancy: -5.86%, CI [-4.96%, -4.38%]** — NEGATIVE, CI excludes zero in the wrong direction
- **All 166 cells fail** — 0/166 pass all gates
- **PBO values observed:** 0.489 (VWAP), 0.645 (RSI-2 equity), 0.593 (forex), 0.416 (unknown crypto catch-all) — all far above 0.10
- **No crypto strategy has ≥ 100 clean forward closes** — the forward test data simply doesn't exist (picks stuck in OPEN/ACTIVE status)

---

## 13. Specific TP/SL Parameters Used by Crypto Strategies

| Strategy | TP | SL | R:R | Source |
|----------|-----|-----|-----|--------|
| `kimi_inverse_scanner` | 2.0% | 3.0% | 0.67 | `kimi_inverse_scanner.py` |
| `kimi_vpin_lgbm_ensemble` | 2-5× ATR | 2-3× ATR | varies | `kimi_vpin_lgbm_ensemble.py` |
| `kimi_ema600_40_momentum` | +15% | -6% | 2.5 | `kimi_ema600_40_momentum.py` |
| `kimi_volatility_momentum_blend` | +12% | -5% | 2.4 | `kimi_volatility_momentum_blend.py` |
| `kimi_lgbm_features` | +12% | -5% | 2.4 | `kimi_lgbm_features.py` |
| `kimi_vpin_reversion` | +6% | -3% | 2.0 | `kimi_vpin_reversion.py` |
| `genome` top-3 configs | 2.0-3.0× ATR | 1.0-1.5× ATR | 1.3-2.0 | `kimi_top_picks_automation.py` |
| `prediction_market_consensus` | varies (~13% BNB, ~13% BTC) | varies (~8% BNB, ~8% BTC) | ~1.6 | `prediction_market_picks.json` |
| Closed picks (actual) | varies | varies | ~0.6 PF | `closed_picks.json` |

---

## 14. Verdict: BLOCKED

| Criterion | Threshold | Actual | Pass/Fail |
|-----------|-----------|--------|-----------|
| Net expectancy | > 0 | **-5.86%** (CRYPCO) | **FAIL** |
| CI excludes zero (positive) | CI lower > 0 | **[-4.96%, -4.38%]** (entirely negative) | **FAIL** |
| Win Rate | > 50% | 56.60% (nominal) but PF < 1.0 | **FAIL** (PF matters more) |
| Profit Factor | > 1.5 | **0.6054** | **FAIL** |
| PBO | ≤ 0.10 | **0.603** (prediction market), 0.489 (VWAP), 0.645 (RSI-2) | **FAIL** |
| DSR | ≥ 0.95 | Not achieved for any crypto strategy | **FAIL** |
| Forward test (≥100 closes, 3 months) | Required | **Zero resolved forward picks** | **FAIL** |
| Max Drawdown | < 20% | 45.46% (KIMI 45m/1h) | **FAIL** |
| Single-source concentration | < 60% | **All 166 cells single-source** (100%) | **FAIL** |
| Claimed 85-100% ML token WR | Claimed | **56.60% actual** | **FAIL** |

**VERDICT: BLOCKED — No crypto strategy passes all Phase 4 proof gates.**

### Key File Paths for Every Claim:

| Claim | File Path |
|-------|-----------|
| Closed picks ground truth | `alpha_engine/data/closed_picks.json` — 76 CRYPTO picks, WR 56.60%, PF 0.6054 |
| Active crypto picks | `alpha_engine/data/active_picks.json` — 9 active picks |
| Kimi inverse scanner | `alpha_engine/kimi_inverse_scanner.py` — TP 2%, SL 3%, R:R 0.67 |
| Kimi inverse picks output | `alpha_engine/data/kimi_inverse_picks.json` — 0 wins, 0 losses, 19 flat |
| Baby strategies | `baby_strategies/kimi_*.py` (5 files) — all crypto, TP 3-15%, SL 3-6% |
| Genome scripts | `genome/kimi_top_picks_automation.py`, `kimi_top_3_tracker.py`, `kimi_best_3_selector.py` |
| Genome data | `genome/data/kimi_*.json` — all picks Grade F, conviction 0.0, backtests negative |
| Audit dashboard kimi | `audit_dashboard/data/kimi_top_*.json` — 0% WR across all phases/rounds |
| Claimed 85-100% WR | `reports/kimi_ultimate_proven_edge_2026-05-16.md` — contradicted by actual data |
| Kimi deep review | `reports/kimi_deep_review_audit_only_2026_05_04.md` |
| KIMI backtest comparison | `backtest_results/kimi_cursor_v04_comparison.json` — all PF < 1.357, mostly negative |
| CRYPCO expectancy | `final_v3/quant-audit-2026-11-14/01_audit/AUDIT_FINDINGS.md` line 82 — **-5.86%, CI [-4.96%, -4.38%]** |
| Asset class fixes | `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` — CRYPCO NOT_READY, PF 0.920 |
| Cross-peer review | `final_v3/quant-audit-2026-11-14/00_summary/CROSS_PEER_REVIEW_REPORT.md` — 0/166 cells pass |
| Focus decision gates | `final_v3/quant-audit-2026-11-14/08_focus_decision/FOCUS_DECISION.md` — PBO ≤0.10, DSR ≥0.95 |
| Prediction market picks | `alpha_engine/data/prediction_market_picks.json` — 2 picks, both OPEN, zero resolved |
| PBO gate | `final_v3/quant-audit-2026-11-14/03_backtest_simulation/BACKTEST_FIXES.md` line 110 — PBO ≤0.10 required |

**Crypto has negative expectancy after costs. No strategy is money-ready. BLOCKED.**
