# System Investigation: WHY Do Some Systems Have So Few Picks?
**Date:** 2026-03-13 ~21:00 UTC
**Investigator:** Claude (Opus) — 7-Agent Parallel Investigation (2 waves)
**Dashboard:** https://findtorontoevents.ca/audit/
**Scope:** All 93 tracked systems — deep code-level root cause analysis

---

## Executive Summary

Investigated every low-pick-count system by reading the actual signal generation code, workflow configs, and pipeline architecture. Found **5 distinct root causes** for why systems produce few or zero picks:

| Root Cause | Systems Affected | Fixable? |
|------------|-----------------|----------|
| **1. ALPHA_LONG_ENABLED = False** (all longs blocked) | All Alpha Engine strategies | Yes — flip flag |
| **2. Binance API geo-blocked (HTTP 451)** from GitHub Actions | 3 strategies + crypto_signal_engine | Yes — proxy/alt API |
| **3. Overly restrictive signal conditions** (2σ+ thresholds) | 8 strategies | By design |
| **4. Closure pipeline never built or never wired** | goldmine_stocks, rl_agent, kimi_live_signals | Yes — build/wire it |
| **5. MAX_OPEN_PICKS = 45, currently at 42** (3 slots left) | All Alpha Engine strategies | Yes — raise cap |

---

## ROOT CAUSE #1: The Long Kill Switch (BIGGEST FINDING)

**File:** `alpha_engine/forward_validator.py` line 863
```python
ALPHA_LONG_ENABLED = False  # Flip to True when long WR > 45%
```

**Every single LONG/BUY signal is rejected in the production path.** This is hardcoded to `False`. Any strategy that primarily generates BUY signals (which is most of them in a bear market recovery) will produce ZERO picks through the production pipeline.

This single flag likely explains why ~100+ strategies across the Alpha Engine have zero or near-zero picks. Only SHORT/SELL signals pass through.

**Impact:** Massive. This is the #1 reason for low pick counts system-wide.

**Fix:** Flip to `True` or make it dynamic based on rolling win rate.

---

## ROOT CAUSE #2: Binance API Geo-Blocking (HTTP 451)

GitHub Actions runners are US-based. Binance primary API returns HTTP 451 (Unavailable For Legal Reasons) from US IPs. Three Alpha Engine strategies depend on live Binance data that fails silently:

| Strategy | What It Needs | Failover Result |
|----------|--------------|-----------------|
| **spot_perp_basis_arb** | Spot + futures mark price | Falls back to Binance US/Bybit/OKX — partial data, often None |
| **funding_term_structure** | Funding rate history (4+ data points) | Funding API blocked, silent skip |
| **order_book_imbalance** | Live L2 order book (10 levels) | Order book API blocked, silent skip |

Also affects **crypto_signal_engine** — its XGBoost model produces sub-threshold confidence (avg 0.4565 vs required 0.55) partly because degraded Binance data reduces model accuracy. Result: 1 pick in entire lifetime.

**Impact:** 3-4 strategies permanently starved of data on every scan cycle.

**Fix:** Add a Binance proxy, use Bybit/OKX as primary, or run these strategies on a self-hosted runner.

---

## ROOT CAUSE #3: Overly Restrictive Signal Conditions

These strategies are designed for rare events. Their low pick count is **by design**, not a bug — but the conditions are so extreme they may never reach statistical significance:

| Strategy | Picks | Primary Bottleneck | How Rare |
|----------|-------|--------------------|----------|
| **proven_vwap_mean_reversion** | 1 | Price must be ≥ 2σ from VWAP + RSI < 35 | ~0.5% of observations |
| **lw_vwap_mean_reversion** | 1 | 2σ from volume²-weighted VWAP + RSI < 40 | ~1% of observations |
| **autocorrelation_exploiter** | 1 | 95% confidence threshold for serial autocorrelation | Efficient markets rarely show persistent AC |
| **entropy_regime_breakout** | 1 | Shannon entropy must drop 1.5σ below its SMA | ~6% theoretical, lower in practice |
| **swing_failure_pattern** | 1 | Requires exact candlestick anatomy: wick below 20-bar low, close above, 30% wick depth, bullish close | Few times/month across 35 symbols |
| **proven_triple_ema_pullback** | 2 | Price must be within 1.5% of EMA21 (extremely tight on daily crypto) | Transient window, 30-min scan misses most |
| **proven_propfirm_conservative** | 1 | 5 simultaneous conditions: ADX>20 + RSI 40-65 + EMA alignment + volume + R:R≥1.5 | Joint probability ~1-2% |
| **seasonal_factor_rotation** | 3 | Price must deviate >2% from 252-day SMA + 7d momentum alignment | Only during strong trend inflections |

### Special Cases

- **profit_taking_reentry** (1 pick): This is a **second-order strategy** — it doesn't scan the market at all. It reads existing active picks looking for ones in profit that have pulled back 0.3-0.5x ATR. Depends entirely on other strategies producing winners in exactly the right window.

- **quality_value_composite** (1 pick): Only scans **10 stock symbols** (8 large-cap + 2 ETFs). Ranks top 25% (2-3 stocks), then filters. Tiny universe = tiny output.

- **adaptive_vr_confluence** (4 picks): Variance ratio must be >1.15 or <0.80 (extreme), plus 2-of-3 confirmations. Broadest symbol universe (~80) saves it from total silence.

**Impact:** These strategies will take months to reach 15+ trades for statistical validation.

**Fix:** Consider relaxing thresholds slightly (e.g., 1.5σ → 1.2σ for entropy, 2σ → 1.5σ for VWAP) or adding intraday scanning.

---

## ROOT CAUSE #4: Closure Pipelines That Don't Exist or Aren't Wired

| System | Active Picks | What's Broken | Detail |
|--------|-------------|---------------|--------|
| **goldmine_stocks** | 53 active, 0 closed | `track_closed_trades.py` exists but **NO workflow calls it** | Script uses snapshot-diffing, but `closed_trades.json` and `pick_snapshots.json` don't exist on disk. Never wired to CI. |
| **rl_agent** | 2 active, 0 closed | **No closure code at all** | `train.py` overwrites `active_picks.json` each cycle. Old picks simply vanish. No TP/SL tracking. |
| **kimi_live_signals** | 33 active, 0 closed | **Architecture mismatch** — closures go to SQLite, dashboard reads JSON | `signal_tracker.py` writes to `signal_tracker.db`, but dashboard reads `live_signals_now.json`. Also: KIMI scanner is now DISABLED (23.5% WR). |
| **regime_terminal** | 7 active, 0 closed | **Not a pick system** — it's a regime classifier | Outputs regime states (Bull/Bear/Accumulation), not actionable picks. No TP/SL/entry price. Dashboard misrepresents it as a pick system. |
| **rapid_fire** | 338 active, 0 closed | No outcome tracking | Signals generated but never tracked to closure |
| **claude_gainer_st** | 9 active, 391 closed | 391 closed picks with **ZERO win/loss attribution** | Picks are closed but PnL never calculated |
| **ml_crypto_predictor** | 159 active, 364 closed | 364 closed picks with **ZERO win/loss attribution** | Same as above — closure happens but outcomes not recorded |

**Impact:** ~1,200+ picks across these systems with no accountability. We literally don't know if they're profitable or not.

**Fix:** Wire `goldmine_stocks/track_closed_trades.py` into `kimi-goldmine-collector.yml`. Build TP/SL tracking for `rl_agent`. Remove `regime_terminal` from the pick dashboard (or add a "regime signals" category). Add PnL calculation to `claude_gainer_st` and `ml_crypto_predictor` closure pipelines.

---

## ROOT CAUSE #5: Global Pick Cap Nearly Full

**File:** `alpha_engine/config.py`
```
MAX_OPEN_PICKS = 45  (currently 42 active → only 3 slots remain)
MAX_PICKS_PER_STRATEGY = 3
MAX_PICKS_PER_SYMBOL = 3
MAX_SAME_DIRECTION_CRYPTO = 6
```

When the portfolio is at 42/45 capacity, only 3 new picks can open regardless of signal quality. This creates a **queue starvation problem** where:
- Established strategies with existing picks keep their slots
- New/rare strategies that finally fire a signal find no available slots
- The R:R ≥ 1.5 filter (double-enforced in both `scanner.py` and `forward_validator.py`) kills picks before they even compete for slots

Additionally: `insider_filing_scanner` holds 13 active picks (all with $0.00 entry/TP/SL — informational signals) but bypasses the per-strategy limit of 3. These phantom picks consume 13 of 45 slots.

**Impact:** ~29% of capacity (13/45) consumed by non-tradeable informational signals.

**Fix:** Either exclude `insider_filing_scanner` from the pick cap, raise MAX_OPEN_PICKS, or implement a quality-weighted slot allocation.

---

## Systems That Are Working Correctly (Low Volume by Design)

| System | Closed | Status | Why Low Volume Is OK |
|--------|--------|--------|---------------------|
| **crypto_ml_edge** | 7 | Working correctly | LightGBM + strategy filters = genuinely selective. 100% WR on 7 closed. |
| **breakout_c_spike** | 4 | Working, strategy is bad | Spike-reversal in bear market = counter-trend longs hitting SL. 0% WR is real performance, not a bug. |
| **coinglass** | Active | Partially working | Closures go to SQLite (correctly read by dashboard for strategy metrics). Missing from main closed picks list due to JSON path being `None`. |

---

## Systems Correctly Disabled for Poor Performance

| System | When Disabled | Why | Final Stats |
|--------|--------------|-----|------------|
| **kimi_live_signals** | 2026-03-12 | 23.5% WR, -61.19% crypto PnL | Workflow comment: "Kill per Antigravity audit" |
| **ml_bg_system_c** | 2026-03-12 | 1.9% WR across 107 trades | "CATASTROPHIC. Kill per Antigravity audit" |

---

## Aggregate Numbers That Matter

| Metric | Value | Concern Level |
|--------|-------|---------------|
| Total systems tracked | 93 | — |
| Systems with 0 closed picks | ~15 | HIGH |
| Systems with broken tracking | 7 (1,200+ untracked picks) | CRITICAL |
| Alpha Engine avg picks/strategy | 2.0 (need 20-30) | HIGH |
| Portfolio aggregate WR | 44.4% | MODERATE |
| Portfolio total PnL | -1,034% | CRITICAL |
| Systems carrying the portfolio | 6 of 93 (6.5%) | HIGH concentration risk |
| Pick slots available | 3 of 45 | CRITICAL bottleneck |
| Phantom picks (insider_filing) | 13 of 45 slots | WASTE |

---

## Priority Action Plan

### P0 — Do Now
1. **Flip `ALPHA_LONG_ENABLED` to True** (or make dynamic) — unblocks all long strategies
2. **Remove insider_filing_scanner's 13 phantom picks** from the active count — frees 29% of capacity
3. **Raise MAX_OPEN_PICKS** from 45 to at least 60

### P1 — This Week
4. **Wire goldmine closure pipeline** — add `track_closed_trades.py` to workflow
5. **Build rl_agent TP/SL tracking** — picks currently vanish
6. **Fix Binance API** — add proxy or switch to Bybit/OKX primary for spot_perp_basis_arb, funding_term_structure, order_book_imbalance
7. **Add PnL attribution** to claude_gainer_st and ml_crypto_predictor closures

### P2 — Next 2 Weeks
8. **Relax signal thresholds** on proven_vwap (2σ→1.5σ), entropy_regime (1.5σ→1.2σ), proven_triple_ema (1.5%→2.5% proximity)
9. **Reclassify regime_terminal** as a regime indicator, not a pick system
10. **Add intraday scanning** for transient-window strategies (swing_failure_pattern, profit_taking_reentry)

---

## Files Referenced
- `alpha_engine/forward_validator.py:863` — ALPHA_LONG_ENABLED flag
- `alpha_engine/config.py` — MAX_OPEN_PICKS, all global limits
- `alpha_engine/scanner.py` — Strategy execution, ML filter, R:R gate
- `alpha_engine/production_scanner.py` — Production orchestrator
- `alpha_engine/proven_scanner_strategies.py` — VWAP, propfirm, triple EMA strategies
- `alpha_engine/mercury_ai_strategies.py` — Basis arb, funding term, LW-VWAP
- `alpha_engine/market_microstructure_strategies.py` — Order book imbalance
- `alpha_engine/statistical_strategies.py` — Autocorrelation exploiter
- `alpha_engine/crypto_strategies.py` — Swing failure pattern
- `alpha_engine/equity_strategies.py` — Quality value composite
- `alpha_engine/nextgen_strategies.py` — Profit taking reentry, seasonal rotation
- `alpha_engine/experimental_strategies.py` — Adaptive VR confluence
- `alpha_engine/tradingview_strategies_wave4.py` — Entropy regime breakout
- `data/goldmine/track_closed_trades.py` — Unwired closure script
- `KIMI_RISEOFTHECLAW/signal_tracker.py` — SQLite-only closure tracker
- `audit_trail/data/dashboard_payload.json` — Master aggregation
