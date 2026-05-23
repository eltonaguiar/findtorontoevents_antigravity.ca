# Diagnosis: Zero Active Picks in Commodities/Futures/ETFs/Bonds & Low WR/PF in Forex/Equities

**Date:** 2026-04-19  
**Author:** Kimi Agent  
**Status:** Investigation Complete — No Fixes Applied  
**Scope:** 
- **Zero picks:** Commodities, Futures, ETFs, Bonds  
- **Low performance:** Forex (28-34% WR, negative PnL) and Equities (0-32% WR, catastrophic PnL)

---

## Executive Summary

Four asset classes (Commodity, Futures, ETF, Bond) have **zero** active picks on the dashboard. Two others (Forex, Equity) are active but show **poor forward performance**. The root causes are **not** a single bug — they are **layered suppression mechanisms** (hard blocks, score penalties, conservative thresholds, missing supply pipelines, and toxic strategies) that compound to create a "defense-in-death" situation for non-crypto assets.

| Asset Class | Active Picks | Primary Blocker | Forward WR (closed) |
|-------------|-------------|-----------------|---------------------|
| CRYPTO | 30-49 | None | 48.4% (n=3,854) |
| FOREX | 8-11 | Soft gates + tight TP/SL | 28.6% (n=7-767*) |
| EQUITY | 6-10 | **Hard block in production_scanner.py** | 0-32% (n=92-771) |
| COMMODITY | **0** | **Hard block in production_scanner.py** | 19% (n=16-424) |
| FUTURES | **0** | Recently unblocked; no strategies firing yet | N/A (thin history) |
| ETF | **0** | Recently unblocked; no strategies firing yet | N/A (thin history) |
| BOND | **0** | Recently unblocked; no strategies firing yet | N/A (thin history) |

*\* Wide variance in sample sizes depending on which closed-book JSON is queried (universal_resolver vs. dashboard_payload).*

---

## Part 1: Why Commodities, Futures, ETFs, and Bonds Have Zero Active Picks

### 1.1 Layer 1 — Upstream Hard Block in `production_scanner.py` (Commodity + Equity)

**File:** `alpha_engine/production_scanner.py` ~lines 2074-2080  
**Code:**
```python
# Gate 0: Non-crypto asset class block (Updated 2026-04-18)
# Equity = 0% WR on 92 picks, Commodity = 19% WR on 16 picks.
# Forex is EXEMPT (75% WR on 8 trades — small but promising).
_BLOCKED_CATEGORIES = {"equity", "stock", "commodity"}
if category in _BLOCKED_CATEGORIES:
    reject_reason = (f"[NON-CRYPTO BLOCK] {category} picks disabled — "
                     f"0-19% forward WR. Crypto-only mode active.")
```

**Impact:** This is an **absolute upstream block**. No commodity or equity pick can ever reach the dashboard, regardless of score, confidence, or strategy quality. The production scanner runs this gate **before** any enrichment, TP/SL capping, or quality scoring. Even if a brilliant commodity strategy existed, it would be killed here silently.

**Note on Equity vs. Stock:** The code normalizes `category == "stock"` to `"equity"` (line 2050-2051), so both labels are caught in the same block.

### 1.2 Layer 2 — Historical Hard Bans Now Removed (Futures + ETF + Bond)

**File:** `audit_trail/quality_gates.py`  
- `BLOCKED_ASSET_CLASSES` previously contained `{"FUTURES"}` with a **-60 score penalty** (removed 2026-04-16).
- `passes_active_gate` previously had an **ETF hard ban** (`return False` for `asset_class == "ETF"`) (removed 2026-04-19).

**File:** `alpha_engine/production_scanner.py` ~lines 2074-2080  
- `_BLOCKED_CATEGORIES` previously included `{"futures", "etf", "bond"}` but was **narrowed on 2026-04-18** to only `{"equity", "stock", "commodity"}`.

**Impact:** Futures, ETF, and Bond are now **technically unblocked** in both the production scanner and the audit dashboard gates. However, the dashboard payload (generated 2026-04-16 19:45 UTC) still shows **0 active picks** for these classes. This indicates that unblocking the gates was necessary but **not sufficient** — the underlying strategies are not yet producing visible picks.

### 1.3 Layer 3 — No Active Supply Pipeline

**Observation:** The production scanner does **not** appear to invoke `scanner.py` with `strategy_filter="all"`. Instead, it:
1. Loads existing `active_picks.json` and `closed_picks.json`
2. Runs `run_full_cycle()` (which validates existing picks, not generating new non-crypto ones)
3. Enriches non-crypto picks with yfinance prices via `_enrich_non_crypto_picks()`
4. Applies quality gates

**Critical gap:** `_enrich_non_crypto_picks()` only adds live prices to picks that **already exist**. It does **not generate** new commodity, futures, ETF, or bond signals. The `scanner.py` module has dedicated strategy filters for these asset classes (`COMMODITY_STRATEGIES`, `FUTURES_STRATEGIES`, `ETF_STRATEGIES`, `BOND_STRATEGIES`), but they are only loaded when `strategy_filter in ("all", "<class>")`. If the CI/production invocation passes `strategy_filter="crypto"` (the default), these dicts are **never loaded** and no signals are generated.

**Evidence:** `alpha_engine/scanner.py` lines 1979-1989 show the conditional loading:
```python
if strategy_filter in ("all", "commodity") and COMMODITY_STRATEGIES:
    strategies.update(COMMODITY_STRATEGIES)
if strategy_filter in ("all", "futures") and FUTURES_STRATEGIES:
    strategies.update(FUTURES_STRATEGIES)
if strategy_filter in ("all", "etf") and ETF_STRATEGIES:
    strategies.update(ETF_STRATEGIES)
if strategy_filter in ("all", "bond") and BOND_STRATEGIES:
    strategies.update(BOND_STRATEGIES)
```

Without an explicit `strategy_filter="all"` or dedicated non-crypto scan step, the supply pipeline is effectively **dry**.

### 1.4 Layer 4 — Conservative Strategy Thresholds (Probation Mode)

Even for the recently unblocked futures/ETF/bond classes, the underlying strategies use **academic-grade thresholds** that rarely fire in current market conditions. A dedicated unblock effort on 2026-04-18 relaxed several thresholds:

| Strategy | Old Threshold | New Threshold |
|----------|--------------|---------------|
| `etf_dual_momentum` | 255 bars | 130 bars |
| `futures_tsmom` | 260 bars | 130 bars |
| `futures_connors_rsi2` | RSI2 < 5 | RSI2 < 15 |
| `bond_yield_momentum` | R:R ≥ 1.20 | R:R ≥ 1.0 |
| `bond_mean_reversion` | volume ≥ 1.2x | volume ≥ 0.9x |

However, these strategies are still marked as **probationary** (`allow_without_forward=True`) with low confidence caps. They also receive a **0.03 confidence penalty** in `production_scanner.py` (lines 2064-2072), which pushes them closer to the Gate 1 floor (0.55).

### 1.5 Layer 5 — Killed Strategies Eliminated the Only Producers

Several permanently killed strategies were the **only** historical producers for these asset classes:

| Strategy | Killed Date | Classes Affected | Evidence |
|----------|------------|------------------|----------|
| `futures_ema_stack_momentum` | 2026-04-02 | FUTURES | 0/4 = 0% WR |
| `futures_mean_reversion` | 2026-04-11 | FUTURES | n=2, -88.8% tail risk |
| `extreme_oversold_bounce` | 2026-04-12 | ETF + FUTURES | ETF: 0%; FUTURES: 0% |
| `vix_reversal` | 2026-04-12 | ETF + FUTURES | ETF: 33%; FUTURES: 0% |

**Impact:** Killing these strategies removed the **entire supply pipeline**, not just the bad output. The replacement strategies (added 2026-04-07/18) have not yet accumulated enough forward history to prove they can fire reliably.

---

## Part 2: Why Forex and Equities Have Low Win Rate / Profit Factor

### 2.1 Forex: Tight TP/SL Caps + Small Sample + Probationary Strategies

**File:** `alpha_engine/non_crypto_policy.py` lines 182-188  
```python
"forex":     (0.005, 0.004),   # 0.5% TP, 0.4% SL
```

**Diagnosis:** The TP/SL caps for forex are **extremely tight**. The code comment explains why:
> "TP > 0.5% never gets hit on forex daily; SL > 0.5% = catastrophic drawdown. 23 closed trades at wider levels showed 4.3% WR: 22L hit SL, only 1W."

This creates a **negative expectancy trap**: take-profit is rarely reached, but stop-loss is hit frequently due to normal intraday noise. Even a strategy with good directional accuracy will show a low WR because the R:R asymmetry is structurally unfavorable.

**Additional issues:**
- **Gate failures:** `tools/_hc_noncrypto_diagnostic.py` shows forex picks failing `Gate1_score_lt_40` and `Gate2_compound_score_trust`.
- **Probationary strategies:** `alpha_engine/non_crypto_quality_gate.py` lists most forex strategies (`carry_trade_momentum`, `asian_range_breakout`, `forex_rsi2_mean_reversion`, etc.) as unvalidated probation strategies.
- **Confidence caps:** Unvalidated forex strategies are capped at **0.58** confidence to avoid the anti-predictive 0.6-0.7 band (which showed 23.3% WR in closed-trade analysis).
- **Macro gate blocks:** `forex_macro_gate()` blocks signals when 20d realized vol > 2.0x 60d baseline, which is common during macro volatility.

**Performance data (conflicting samples):**
- `analyze_asset_classes.py`: FOREX n=7, WR 28.57%, Avg PnL -0.42%
- `non_crypto_quality_gate.py` docstring: FOREX PF 0.53, WR 33.9%, -18.17% PnL on 131 trades
- `production_scanner.py` comment: "Forex is EXEMPT (75% WR on 8 trades)"

The variance is due to different JSON sources and time windows, but the consistent pattern is **sub-40% WR and negative PnL**.

### 2.2 Equities: Upstream Hard Block + Toxic Strategies + Macro Gates

**Primary blocker:** Equities are in `_BLOCKED_CATEGORIES` in `production_scanner.py` (see 1.1). This is the single biggest reason there are so few equity actives and why the ones that do exist perform poorly — **only the lowest-quality equity picks were slipping through before the block was added**, creating a survivorship bias of terrible performance.

When equity picks *do* make it through (e.g., from copy-trader merges or prior active_picks.json), they hit multiple downstream filters:

**1. Macro gate bear-market protection:**
- `equity_macro_gate()` blocks ALL equity LONGs when:
  - SPY < 200d SMA (bear market)
  - SPY 5d return < -7% (crash protection)
  - SPY SMA20 < SMA50 (intermediate downtrend)
- This is **correct** for capital preservation, but it means ~30-50% of calendar days will produce zero equity longs.

**2. VIX hard-block:**
- `vix_hard_block_gate()` blocks non-contrarian LONGs when VIX > 30.
- `vix_confidence_adj()` reduces confidence by 40-80% when VIX > 25.

**3. Toxic strategies with 0% WR:**
- `yahoo_analyst_consensus`: 0/5 = 0% WR (12-month analyst targets are unreachable in a 10-day trading window).
- `claude_gainer_ml` / `claude_gainer_ml_perf`: 11.1% WR, -27.10% PnL.

**4. Quality gate failures:**
- `tools/_hc_noncrypto_diagnostic.py` shows equity picks failing `Gate2_compound_score_trust` (score < 50 and trust < 8) and `Gate1_score_lt_40`.
- Example: GOOGL `super_signals` has score=45, trust=7, but fails compound gate.

**5. Asset-class bonus starvation:**
- `ASSET_CLASS_BONUSES` in `quality_gates.py` sets EQUITY to **0** (was +8, reversed due to poor performance). This makes it harder for equity picks to climb above the raw-score floor of 55.

---

## Part 3: Suggested Fix Plan

### Phase 1: Remove the Upstream Hard Blocks (Immediate)

1. **`alpha_engine/production_scanner.py` — Remove `commodity` from `_BLOCKED_CATEGORIES`**
   - The block cites 19% WR on 16 picks, but this is a **thin sample** from killed strategies. Blocking the entire asset class prevents new strategies from building forward history.
   - **Suggested change:** Reduce `_BLOCKED_CATEGORIES` to `{}` (empty) or move the block to a **probation flag** that allows dashboard display with a "PROBATION" badge.

2. **`alpha_engine/production_scanner.py` — Remove `equity` and `stock` from `_BLOCKED_CATEGORIES`**
   - The 0% WR on 92 picks was driven by toxic strategies (`yahoo_analyst_consensus`, `claude_gainer_ml`) and bear-market conditions, not by the entire equity asset class.
   - **Suggested change:** Unblock equity, but apply the existing macro gates (SPY > SMA200, VIX, crash detection) **before** picks are generated, not after. This filters bad timing without killing the asset class entirely.

### Phase 2: Fix the Supply Pipeline (Short-Term)

3. **Add a dedicated non-crypto scan step to the CI/production pipeline**
   - The production scanner must invoke `scanner.py` with `strategy_filter="all"` (or at least `"commodity", "futures", "etf", "bond", "forex", "equity"`) so that the non-crypto strategy dicts are loaded and executed.
   - **Alternative:** Create a separate `run_non_crypto_scan.py` script that runs nightly and appends its output to `active_picks.json`.

4. **Verify non-crypto strategy dictionaries are populated**
   - Check `alpha_engine/commodities_strategies.py`, `futures_strategies.py`, `etf_strategies.py`, `bond_strategies.py` to ensure they contain actual strategy callables and are not empty.

### Phase 3: Fix Forex Structural Edge (Short-Term)

5. **Re-evaluate forex TP/SL caps**
   - 0.5% TP / 0.4% SL is too tight for most forex strategies. Consider:
     - Increasing TP cap to **1.0-1.5%** for swing strategies.
     - OR: Switching to **time-based exits** (e.g., 48-72h) instead of tight SL for mean-reversion strategies.
     - OR: Using **ATR-based dynamic TP/SL** rather than fixed percentage caps.

6. **Promote or kill probationary forex strategies**
   - `forex_rsi2_mean_reversion` requires 50 forward trades at ≥45% WR. If it cannot meet this after a reasonable window, it should be killed or inverted.
   - `carry_trade_momentum` is allowed without forward data (`allow_without_forward=True`) — this is fine for building history, but cap its position sizing to 0.25x until validated.

### Phase 4: Fix Equity Strategy Quality (Medium-Term)

7. **Kill or invert confirmed toxic equity strategies**
   - Hard-kill `yahoo_analyst_consensus` (0% WR on 5+ trades, structurally flawed 12-month horizon).
   - Invert or retrain `claude_gainer_ml` (11% WR, -27% PnL).

8. **Lower the non-crypto raw score floor temporarily**
   - `ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE = 55` is too high for thin-sample asset classes.
   - **Suggested:** Create a **probation mode** with floor=40 for BOND/COMMODITY/FUTURES/ETF, and floor=45 for EQUITY/FOREX, until each class has ≥50 closed picks.

9. **Add a "PROBATION" badge to the dashboard**
   - Picks from asset classes with <50 closed picks should be visible on the dashboard but clearly tagged as "BUILDING HISTORY". This solves the data-starvation catch-22.

### Phase 5: Cross-Asset Edge Discovery (Long-Term)

10. **Wire `cross_asset_edge_discovery.py` into the scanner**
    - This module already has preferred pairs with pre-validated edges. Use it as a **seed generator** for commodity and futures picks instead of relying solely on generic mean-reversion strategies.

11. **Establish forward-validation loops for non-crypto**
    - Once picks are flowing, run `forward_validator.py` and `walkforward_validator.py` on a **weekly** basis for each non-crypto asset class. Use the results to promote strategies out of probation or kill them.

---

## Files Referenced

| File | Relevance |
|------|-----------|
| `alpha_engine/production_scanner.py` | Gate 0 hard blocks on equity/commodity; confidence penalties for futures/etf/bond |
| `audit_trail/quality_gates.py` | Recently removed ETF hard ban and FUTURES -60 penalty; sets ASSET_CLASS_BONUSES=0 for equity/forex |
| `alpha_engine/non_crypto_policy.py` | TP/SL caps (0.5%/0.4% for forex), strategy policy definitions |
| `alpha_engine/non_crypto_quality_gate.py` | Macro gates, VIX blocks, probation/killed strategy lists, confidence caps |
| `alpha_engine/scanner.py` | Strategy filter gating — non-crypto dicts only load with `strategy_filter="all"` |
| `tools/_hc_noncrypto_diagnostic.py` | Live gate failure analysis: forex/equity fail score_lt_40 and compound_score_trust |
| `tools/_nc_last_activity_snapshot.py` | Confirms 0 active for COMMODITY/FUTURES/BOND/ETF in dashboard payload |
| `analyze_asset_classes.py` | Closed-trade WR/PF by asset class (CRYPTO 48.4%, FOREX 28.6%, NON-CRYPTO 40.8%) |

---

## Conclusion

The zero-pick problem is **not a data bug** — it is the **intended outcome of multiple defensive layers** that have become overly aggressive. The most severe issue is the **upstream hard block in `production_scanner.py`** on `equity` and `commodity`, which makes it impossible for any pick in those classes to exist. Futures, ETFs, and Bonds were recently unblocked but still show zero actives because the **supply pipeline (scanner.py strategy_filter) is not wired to generate them** and the **replacement strategies are too conservative** to fire in current markets.

Forex and Equities suffer from **structural edge problems**: forex has impossibly tight TP/SL caps that guarantee low WR, while equities are dominated by toxic strategies and aggressive macro gates that filter out all but the worst survivors.

**Recommended immediate action:** Remove the hard blocks, add a dedicated non-crypto scan step, and create a **probation display mode** so the system can build forward history without misleading users about quality.
