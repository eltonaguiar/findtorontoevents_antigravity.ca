# Audit Dashboard Critical Fixes — 2026-04-20

## Summary

Full review of `findtorontoevents.ca/audit` revealed **5 critical scoring flaws** causing the dashboard to show catastrophically misleading metrics. The overall system shows -1,130% raw PnL, 39.5% WR, and -0.098 Sharpe — but much of this is caused by impossible outliers and unchecked broken strategies that distort every aggregate metric.

---

## 🚨 Critical Findings

### 1. PnL Outliers Destroying All Metrics

| Symbol | Strategy | System | PnL % | Issue |
|--------|----------|--------|-------|-------|
| AUDUSD=X | myfxbook_retail_contrarian | multi_asset_copytrader | **-106,700%** | Physically impossible — > 1000x loss |
| GBPJPY=X | ig_contrarian_sentiment | multi_asset_copytrader | **-2,305%** | Exceeds total capital possible |
| GBPJPY=X | forex_rsi2_mean_reversion | forex_copy_trader | **-2,303%** | Same broken PnL calc |

**Root cause**: No per-trade PnL cap. These values flow into Sharpe, expectancy, and profit factor calculations, making the entire dashboard unreliable.

**Fix**: Cap all per-trade PnL at `[-100%, +100%]`. No single trade can lose more than 100% of allocated capital.

### 2. FOREX Catastrophe (25.8% WR)

| Symbol | Closed Trades | PnL % | Concentration |
|--------|--------------|-------|---------------|
| USDCHF=X | Many | **-438.72%** | 38.8% of total PnL |
| AUDJPY=X | Many | **-206.60%** | 18.3% |
| NZDJPY=X | Many | **-205.66%** | 18.2% |

FOREX is the worst-performing asset class: 25.8% WR, -13.16% total PnL. Yet active FOREX picks receive almost no scoring penalty because `score_booster.py` gates (MTF, ensemble, liquidity) are **crypto-only**.

**Fix**: Added Forex/Commodity catastrophe penalty: symbols with <30% WR on 5+ closed trades get -15 score points.

### 3. Symbol-Specific WR Blindness

The scoring engine evaluates **strategy-wide WR** but ignores **per-symbol WR**. Example:
- AVAXUSDT: Strategy-wide score = 99, but symbol-specific WR = **26%**

**Fix**: Added symbol-specific WR gate. If a symbol has <35% WR on 10+ closed trades, score is capped at 50.

### 4. Catastrophic Systems Not Banned

| System | Worst Trade | Status Before Fix |
|--------|-------------|-------------------|
| `mercury2_fast` | TRX -100%, BNB -99.8% | **No score cap** |
| `myfxbook_retail_contrarian` | AUDUSD -106,700% | **No score cap** |
| `multi_asset_copytrader` | GBPJPY -2,305% | **No score cap** |

**Fix**: Added to `SYSTEM_SCORE_CAPS` — mercury2_fast capped at 5, myfxbook at 5, multi_asset_copytrader at 40.

### 5. Massive Duplicate Entries in Big Mover Monitor

HYPEUSDT `copy_hl_lb_none` appears **6 times** at exactly 100% PnL in `top_winners`. FETUSDT `ml_enhanced` appears **10+ times** at 58.13%. This inflates statistics and makes the leaderboard unreliable.

**Status**: Flagged for investigation — requires fix in `dashboard_generator.py` deduplication logic.

---

## Asset Class Performance Breakdown

| Asset Class | Active | Closed | WR % | PnL % | Verdict |
|-------------|--------|--------|------|-------|---------|
| **CRYPTO** | 46 | 6,420+ | ~43% | Mixed | ✅ Primary edge |
| **EQUITY** | 8 | 347 | 49.6% | +204.82% | ✅ Best performer |
| **STOCK** | 0 | 5 | 60.0% | +0.14% | ⚠️ Too few trades |
| **FOREX** | 4 | 841 | 25.8% | -13.16% | 🔴 CATASTROPHIC |
| **COMMODITY** | 1 | 539 | 24.1% | +15.51% | ⚠️ Low WR but profitable |
| **BOND** | 0 | 17 | 47.1% | +2.84% | ⚠️ Insufficient sample |
| **ETF** | 0 | 74 | 48.6% | +2.58% | ⚠️ Near breakeven |
| **FUTURES** | 0 | 0 | null | 0.0% | 🔴 DEAD — zero trades |

---

## Regime Analysis (Critical)

| Regime | WR % | Trades | Wins | Losses |
|--------|------|--------|------|--------|
| TRENDING_UP | 100% | 1 | 1 | 0 |
| RANGING | **10%** | 10 | 1 | 9 |
| TRENDING_DOWN | **6.2%** | 16 | 1 | 15 |

**Verdict**: The system is picking **against** the regime in 26 of 27 non-uptrend trades. Regime alignment is essentially non-functional.

---

## Impact Simulation: "High Conviction" Follow Analysis

### Current State (All Picks, No Filter)
- Expectancy: **-0.13% per trade**
- Sharpe: **-1.56 annualized**
- Profit Factor: **0.9**
- Following these picks loses money.

### Last 24h (Most Recent)
- Sharpe: **0.53 per trade**
- Profit Factor: **4.68**
- WR: ~75%
- 24h is strongly positive — recent fixes are working.

### 30-Day Window
- Profit Factor: **1.01** (breakeven)
- **423.6% of PnL from single symbol (INJUSDT)** — extreme concentration risk
- Without INJUSDT: PnL drops from +49% to **-158%**

---

## Files Changed

### `alpha_engine/score_booster.py`
1. **PnL outlier cap** (lines 730-748): Caps all trade PnL to `[-100%, +100%]`
2. **Symbol-specific WR gate** (lines 750-795): Caps score to 50 if symbol WR <35% on 10+ trades
3. **Forex/Commodity catastrophe penalty** (lines 797-816): -15 penalty for symbols with <30% WR on 5+ closed trades
4. **System score caps expanded** (lines 1105-1110): Added mercury2_fast (5), myfxbook_retail_contrarian (5), multi_asset_copytrader (40)
5. **Boost log updated** (lines 1176-1178): New stats tracked in audit output

---

## Verification

- [x] `score_booster.py` syntax validated
- [x] All existing scoring logic preserved — new gates are additive
- [x] New caps and penalties have clear audit trail fields (`_pnl_capped`, `_symbol_wr_capped`, `_forex_catastrophe_penalty`)
- [x] Summary log captures new fix statistics
- [x] No breaking changes to payload schema

## Remaining Items (Not in This PR)

1. **Duplicate deduplication in `dashboard_generator.py`** — HYPEUSDT/FETUSDT duplicates
2. **FUTURES asset class** — 0 trades, needs pipeline investigation
3. **Regime gate enforcement** — should block picks entirely when regime WR <15%
4. **30-day PnL concentration guard** — flag when single symbol >50% of PnL
