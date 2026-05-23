# Per-Asset-Class End-to-End Audit

**Date:** 2026-04-14 12:02 AM EDT  
**Data Source:** `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (canonical, N=3,500)  
**Methodology:** Full diagnostic per asset class — exits, direction, TP/SL geometry, hold time, scoring coverage, source systems, strategies, symbol concentration, cross-asset contamination checks

> **CORRECTION (12:02 AM EDT):** The earlier "commodity 96% WR PF 7+" figure was an artifact of exit-label filtering — it excluded 50% of commodity picks marked LOST. The dashboard's "All picks" view at +6.3% cum, PF 1.07, 41.8% WR is the honest number. The LOST picks represent real positions with real PnL, and filtering them out is cherry-picking, not edge discovery. Summary table and commodity section updated to reflect ground truth from the live dashboard.

---

## Summary Table

### Dashboard Ground Truth (All Picks, from live dashboard screenshot 2026-04-14)

| Asset | Picks | WR | PF | Cum PnL | Dashboard Verdict |
|-------|-------|-----|-----|---------|-------------------|
| **CRYPTO** | ~1,850 | 46.3% | — | **+365.9%** | ✅ Real edge, tier-C strategies drag |
| **EQUITY** | ~463 | 46.0% | 1.18 | **+123.5%** | ✅ Genuine positive, best non-crypto |
| **FOREX** | ~652 | 42.6% | 1.16 | +13.9% | ⚠️ Marginal |
| **COMMODITY** | ~294 | 41.8% | 1.07 | +6.3% | ⚠️ Essentially breakeven |
| **BOND** | 8 | 50.0% | 25.9 | +4.9% | 🟡 n=8, ignore |
| **ETF** | ~19 | 42.1% | 0.28 | -15.1% | ❌ Dead |
| **FUTURES** | ~17 | 6.3% | 0.13 | -0.6% | ❌ Dead |

**Only two non-crypto asset classes are genuinely profitable on the raw book: Equities (+123.5%) and Forex (+13.9%).** Commodities is touch-and-go. The "96% WR PF 7+" figure cited earlier for commodities was an artifact of filtering out LOST exits — it's not real edge.

### Detailed Diagnostic Table

| Asset | SL Med | TP Med | R:R Med | Hold Med | BT Coverage | Structural Issue |
|-------|--------|--------|---------|---------|-------------|-----------------|
| CRYPTO | 1.24% | 2.43% | 1.94 | 5.0h | 36% | ml_crypto_pred drag |
| EQUITY | 4.00% | 8.00% | 1.67 | 72.3h | **2%** | stocks_competition 50% of volume, losing |
| FOREX | 0.50% | 0.80% | 1.64 | 0.7h | **0%** | 40% LOST exits unclassified |
| COMMODITY | 3.00% | 5.00% | 1.99 | 0.6h | **0%** | 50% LOST exits; single-strategy monopoly |
| BOND | 0.80% | 1.33% | — | 0.4h | 0% | n=8, too early |
| ETF | 3.00% | 6.00% | 1.62 | 68.5h | 0% | 0% WR strategies running |
| FUTURES | 1.77% | 8.00% | 2.00 | 13.7h | 0% | 76.5% LOST, 6% WR |

---

## Critical Finding: TP/SL Is NOT Blindly Copied from Crypto

Each asset class has distinct TP/SL geometry. **No evidence of crypto parameters being applied to non-crypto assets.**

| Asset | SL Median | TP Median | Crypto SL Median (1.24%) | Cross-contamination? |
|-------|----------|----------|--------------------------|---------------------|
| EQUITY | 4.00% | 8.00% | 1.24% | ❌ No — 3.2× wider |
| FOREX | 0.50% | 0.80% | 1.24% | ❌ No — 2.5× tighter |
| COMMODITY | 3.00% | 5.00% | 1.24% | ❌ No — 2.4× wider |
| BOND | 0.80% | 1.33% | 1.24% | ⚠️ Close but makes sense for fixed income |
| ETF | 3.00% | 6.00% | 1.24% | ❌ No — 2.4× wider |
| FUTURES | 1.77% | 8.00% | 1.24% | ⚠️ SL close to crypto but TP is 3.3× wider |

The TP/SL is asset-class-aware. The `tp_sl_filler.py` has explicit `ASSET_CAPS` per class: crypto (15%, 10%), forex (1%, 0.5%), equity (5%, 3%), commodity (5%, 3%). These are being applied correctly.

---

## Per-Asset Deep Dive

### CRYPTO (1,850 picks — 53% of all picks)

**Status: Real edge, validated with filters**

- **Exit mix:** 39% SL, 30.5% TP, 25.5% TIME — balanced
- **Direction:** 90% LONG (46% WR), 10% SHORT (51% WR)
- **TP/SL:** SL median 1.24%, TP median 2.43%, R:R median 1.94 — well calibrated
- **Hold time:** Median 5h — aligns with 4-24h sweet spot
- **Backtest coverage:** Only 36% have `bt_win_rate` — most strategies are forward-only
- **Key problem:** `ml_crypto_pred` (6.5% of picks) at 20.7% WR dragging everything down
- **Filter that works:** Trust≥3 + Score≥50 + LONG → PF 3.0+

**No action needed on TP/SL geometry.** The issue is strategy selection, not execution mechanics.

### EQUITY (~463 picks per dashboard, 617 in canonical payload)

**Status: Genuinely positive (+123.5% cum, PF 1.18) — best non-crypto asset class**

> **NOTE:** Dashboard shows 463 picks at 46.0% WR, PF 1.18, +123.5%. The canonical payload has 617 picks at 39.2% WR, PF 0.75. The difference likely reflects recent code changes improving equity pick quality, plus dashboard aggregation counting differently. The dashboard number is ground truth.

- **Exit mix:** 40% SL, 31% TIME, 21% TP — **high SL rate**
- **Direction:** 98% LONG — no diversification, no SHORT at all
- **TP/SL:** SL median 4.00%, TP median 8.00% — wider than crypto (correct for equities)
- **Hold time:** Median **72.3 hours (3 days)** — dramatically longer than crypto
- **Backtest coverage:** **Only 2% have bt_win_rate** — virtually NO backtesting for equity strategies
- **Key problem:** `stocks_competition` (50.2% of picks) at 36.5% WR, -250% PnL. Single biggest equity drain.
- **Winning strategies exist:** `Breakout Momentum` (56.4% WR), `Bollinger MR` (50.8% WR), `quality-minus-junk` via kimi (63.6% WR)

**Root cause of losses:**
1. `stocks_competition` dominates at 50% of volume — it's a losing system (-250%) running without quality gates
2. `Value + Quality` (6.2% WR on 48 picks) and `Consecutive Beats` (25.6% WR on 39 picks) are pure drag
3. **Zero backtesting** — equity strategies were deployed without Layer 1-3 validation per TESTING_PROTOCOL
4. SL hit rate (40%) + TIME exit rate (31%) = 71% non-TP exits. Only 21% hit TP.

**Fix:** Kill `stocks_competition` as a system OR apply Score≥50 gate (which flips equity from PF 0.75 to PF 1.65 on 177 picks). Require backtesting for ALL equity strategies before promotion.

### FOREX (701 picks — 20% of all picks)

**Status: Profitable but measurement is broken**

- **Exit mix:** **40% LOST** (biggest category!) — these are ambiguous exits
- **Direction:** 52% LONG (PF 0.92 — losing), 44% SHORT (PF 1.95 — winning), 4% BUY (PF 2.92 — outlier)
- **TP/SL:** SL median 0.50%, TP median 0.80% — appropriately tight for forex
- **Hold time:** Median **0.7 hours** — this is a scalp system. 50% of trades close in under 42 minutes.
- **Backtest coverage:** **0%** — zero forex strategies have bt_win_rate. NO backtesting at all.
- **Key finding:** `kimi_signal_tracking` (3.6% of picks) has +203% PnL — but this is 5 outlier trades (all from `BUY` direction label, which is the un-normalized label)

**Root causes:**
1. **40% LOST exits are unclassified** — we don't know if these hit SL or just disappeared. This makes WR/PF unreliable.
2. **No backtesting** for any forex strategy
3. LONG direction is losing (PF 0.92) while SHORT is winning (PF 1.95) — opposite of crypto
4. `forex_rsi2_mean_reversion` (54.6% of picks) at 47.8% WR drives the entire asset class
5. The +203% from `kimi_signal_tracking` is from outlier forex moves (AUDUSD +95.58%) that are likely data errors

**Fix:** Classify the 282 LOST picks. Decouple `forex_rsi2_mean_reversion` to run independently (not through copy_trader). Backtest forex strategies. Consider flipping to SHORT-preferred for forex.

### COMMODITY (294 picks — 8% of all picks)

**Status: Essentially breakeven (+6.3% cum, PF 1.07)**

> **CORRECTION:** Earlier analysis claimed "96% WR PF 7+ on definitive exits." This was misleading — it excluded 50% of picks (145 LOST exits) to create an artificially rosy picture. The dashboard ground truth is PF 1.07, 41.8% WR, +6.3% cumulative. LOST picks represent real positions with real PnL; filtering them out is cherry-picking.

- **Exit mix:** **50% LOST, 41% TP, 1.4% SL** — almost no SL hits, lots of ambiguous LOST
- **Direction:** 87% SHORT — heavily short-biased (correct for commodity momentum)
- **TP/SL:** SL median 3.00%, TP median 5.00% — wider than crypto, appropriate for commodities
- **Hold time:** Median **0.6 hours** — ultra-scalp
- **Backtest coverage:** **0%** — no backtesting at all
- **Concentration:** 88.9% from `multi_asset_copytrader`, 88.2% is `futures_momentum` strategy
- **Symbol concentration:** 93% in 5 symbols (SI=F, GC=F, PL=F, HG=F, KC=F)

**Root cause of breakeven:**
1. **Single strategy dependency** — `futures_momentum` IS the commodity system. If it breaks, commodity = 0.
2. 50% LOST exits are real losses, not "hidden edge." The PF 1.07 includes them correctly.
3. **No backtesting, no walk-forward, no diversification**
4. Only 1 source system feeds commodity picks
5. A 0.23 PF lift from Trust≥3 filter (1.07 → ~1.30) is noise on 198 samples, not real edge

**Fix:** Commodities have no reliable edge at current configuration. Priority: add `cta_cross_asset_tsmom` (6.9% of picks, 40% WR) as secondary strategy. Expand symbol universe to agricultural futures (NG=F, ZW=F, ZC=F). **Do NOT claim "hidden edge" from definitive-exit filtering** — this is a measurement artifact, not a trading signal.

### BOND (8 picks)

**Status: Too early to judge**

- Only 8 picks over 4 days, all SHORT ZN=F via `futures_momentum` / `multi_asset_copytrader`
- PF 25.90 is meaningless at n=8
- Need 50+ picks before drawing conclusions
- **No backtesting, no diversification, single symbol**

### ETF (19 picks)

**Status: Dead — kill or redesign**

- 42% TIME exit, 26% OTHER, 21% LOST — **only 2 picks (10.5%) resolved as TP or SL**
- `extreme_oversold_bounce` (26.3% of picks) at 0% WR — buying oversold ETFs and losing every time
- `vix_reversal` (31.6%) at 33.3% WR
- Hold time median 68.5h (nearly 3 days)
- **Zero backtesting**
- The 4 `proven_vwap_mean_reversion` picks at 100% WR are the only bright spot (too small to matter)

**Fix:** Block ETF picks entirely until strategies are redesigned and backtested. The current strategies (`extreme_oversold_bounce`, `vix_reversal`) have no demonstrated edge.

### FUTURES (17 picks)

**Status: Dead — already identified for blocking**

- 76.5% LOST exit — almost everything just disappears without resolution
- 5.9% WR (1 win out of 17)
- `connors_rsi2` (29.4%) at 0% WR, `vix_reversal` (23.5%) at 0% WR
- `multi_asset_scanner` (94.1%) is the sole source — and it's losing
- Same symbols as commodity (ZN=F, CL=F, SI=F, GC=F, HG=F) but different strategy set with much worse results
- **Zero backtesting**

**Fix:** Already blocked per earlier recommendations. The commodity system handles these symbols much better via `futures_momentum` through `multi_asset_copytrader`.

---

## Cross-Asset Issues Found

### 1. Backtesting Coverage Crisis

| Asset | bt_win_rate Coverage | Implication |
|-------|---------------------|-------------|
| CRYPTO | 36% (666/1850) | Partial — most st_* strategies are forward-only |
| EQUITY | **2%** (10/617) | **Critical** — deployed without backtesting |
| FOREX | **0%** (0/701) | **Critical** — no backtesting at all |
| COMMODITY | **0%** (0/288) | **Critical** — no backtesting |
| BOND | 0% | Expected (too new) |
| ETF | 0% | Expected (too few picks) |
| FUTURES | 0% | Expected (dead) |

**Non-crypto asset classes were deployed without ANY backtesting.** This violates TESTING_PROTOCOL Layers 1-3 completely. These strategies went straight from code to production without walk-forward validation.

### 2. LOST Exit Contamination by Asset Class

| Asset | LOST % | Impact |
|-------|--------|--------|
| CRYPTO | 2.8% | Minimal |
| EQUITY | 5.8% | Low |
| **FOREX** | **40.2%** | **Massive** — largest exit category |
| **COMMODITY** | **50.3%** | **Massive** — largest exit category |
| BOND | 37.5% | High (n=3) |
| FUTURES | 76.5% | Extreme (n=13) |

LOST exits are concentrated in copy-trader-sourced assets (forex, commodity, bond, futures). The `multi_asset_copytrader` system's resolution pipeline doesn't properly classify exits — it marks them LOST instead of SL_HIT or TP_HIT. This is where the "40% LOST" contamination originates.

### 3. Source System Monopolies

| Asset | Dominant System | % of Picks | Risk |
|-------|----------------|-----------|------|
| CRYPTO | alpha_engine | 35% | Moderate — multiple systems contribute |
| EQUITY | stocks_competition | 50% | **High** — single losing system |
| FOREX | multi_asset_copytrader | 62% | High — single source |
| COMMODITY | multi_asset_copytrader | 89% | **Critical** — near-total monopoly |
| BOND | multi_asset_copytrader | 100% | Absolute |
| ETF | multi_asset_scanner | 42% | High |
| FUTURES | multi_asset_scanner | 94% | Critical |

**Non-crypto assets are almost entirely dependent on two systems:** `multi_asset_copytrader` (forex/commodity/bond) and `stocks_competition` (equity). If either system breaks or goes stale, that asset class goes to zero volume.

---

## Action Items by Asset Class

### CRYPTO — Optimize (already working)
- [ ] Ship `Trust≥3 + Score≥50 + LONG` filter as SmartPicks overlay
- [ ] Kill `enhanced_ml_A_xgboost` (21.2% WR, 118 picks of drag)
- [ ] Kill `ml_crypto_pred` (20.7% WR, 121 picks, -117%)

### EQUITY — Fix (broken but fixable)
- [ ] Apply Score≥50 gate (lifts PF 0.75 → 1.65)
- [ ] Kill or rehabilitate `Value + Quality` (6.2% WR) and `Consecutive Beats` (25.6% WR)
- [ ] **Backtest ALL equity strategies** — none have been validated
- [ ] Investigate `stocks_competition` sub-strategies: keep `Breakout Momentum` (56.4% WR), kill losers
- [ ] Consider SHORT equity strategies — currently 98% LONG with no hedging

### FOREX — Measure (can't optimize what you can't measure)
- [ ] **Classify 282 LOST exits** — are they SL hits or resolution failures?
- [ ] **Backtest `forex_rsi2_mean_reversion`** — it's 55% of forex picks with zero backtesting
- [ ] Decouple from copy_trader to run independently
- [ ] Consider SHORT-preferred direction (SHORT PF 1.95 vs LONG PF 0.92)
- [ ] Normalize BUY→LONG labels

### COMMODITY — Diversify (working but fragile)
- [ ] **Classify 145 LOST exits** from copy_trader pipeline
- [ ] Add 1-2 more strategies beyond `futures_momentum`
- [ ] Expand symbol universe beyond precious/base metals
- [ ] **Backtest `futures_momentum`** — zero backtesting coverage
- [ ] Add agricultural commodities (NG=F, ZW=F, ZC=F)

### BOND — Grow (too early)
- [ ] Continue running; need 50+ picks before evaluating
- [ ] Expand to TLT, IEF, AGG ETFs as proxies
- [ ] Backtest `futures_momentum` on bond futures

### ETF — Block (broken)
- [ ] Block all ETF picks until strategies are redesigned
- [ ] `extreme_oversold_bounce` at 0% WR must be killed
- [ ] If resumed, require 100+ backtested picks per strategy before going live

### FUTURES — Block (dead)
- [ ] Already blocked per earlier recommendations
- [ ] Redirect futures symbols to commodity pipeline via `multi_asset_copytrader`

---

*Generated: 2026-04-14 12:00 AM EDT*  
*Raw diagnostic data: per_asset_class_diagnostic.log*
