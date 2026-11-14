# COMMODITY + FUTURES Quick Wins

**Audit Date:** 2026-11-14  
**Auditor:** Quantitative Engineer  
**Scope:** COMMODITY and FUTURES prediction pipelines  
**Status:** COMMODITY frozen (4 zombie picks, ~156 days old); FUTURES class-blocked (0 live picks, 1 ghost YM=F)

---

## 1. TOP 3 QUICK WINS (< 1 day each)

### 1.1 Unblock FUTURES in `BLOCKED_ASSET_CLASSES`
- **What:** Remove `"FUTURES"` from `BLOCKED_ASSET_CLASSES` in `audit_trail/quality_gates.py` (line ~1724).
- **Why:** `alpha_engine/futures_strategies.py` contains 4 academically-backed strategies (TSMOM, ConnorsRSI2, Cross-Asset Momentum, Vol-Regime Breakout) with documented bug fixes (2026-04-07). They emit zero picks solely because the asset class is frozen at the quality-gate level.
- **Expected Impact:** Immediate eligibility for ES=F, NQ=F, YM=F, GC=F, SI=F, ZN=F signals. Expected 2-8 signals/week based on historical frequency of the 4 strategies.
- **Effort:** 5 minutes (config change) + 2 hours (verify no downstream test breakage in `tests/test_quality_gates.py`).
- **Risk Mitigation:** Keep `futures_momentum` in `BLOCKED_ASSET_STRATEGY_PAIRS` (H-005 escalation); do NOT unblock individual toxic strategies.

### 1.2 Force-Expire Zombie Picks + Regenerate Dashboard Payload
- **What:** Run `audit_trail/universal_pick_resolver.py` with a hard max-age cap of 30 days to expire:
  - 4 COMMODITY picks from June 2026
  - 1 YM=F ghost from October 19 (26 days stale in `dashboard_data.json`)
  Then regenerate `audit_dashboard/data/dashboard_data.json` via `audit_trail/dashboard_generator.py`.
- **Why:** Stale picks poison win-rate calculations, dashboard freshness metrics, and capital allocation models.
- **Expected Impact:** Clean active-pick panel; dashboard freshness score improves from STALE to FRESH.
- **Effort:** 2-4 hours (resolver run + validation + commit).
- **File/Location:** `audit_trail/universal_pick_resolver.py`, `audit_dashboard/data/dashboard_data.json`

### 1.3 Wire `commodity_signal_generator.py` into the Non-Crypto Emission Pipeline
- **What:** Add an ingestion hook in `non_crypto_agent/main.py` (or `alpha_engine/production_scanner.py`) that reads `alpha_engine/data/commodity_active_picks.json` and forwards signals through `forward_validator.run_validation()` and `audit_trail.quality_gates._is_valid_resolved_pick()` before emitting to the active-pick ledger.
- **Why:** The generator runs standalone and writes to a JSON file that is never consumed. COMMODITY has had zero emissions since June because there is no plumbing between signal generation and the live pipeline.
- **Expected Impact:** Restores COMMODITY emission flow; signals get validated, scored, and tracked like CRYPTO/EQUITY picks.
- **Effort:** 4-6 hours (import, loop, validation gate, error handling, log noise review).
- **File/Location:** `non_crypto_agent/main.py`, `alpha_engine/production_scanner.py`

---

## 2. MEDIUM FIXES (1-3 days)

### 2.1 Per-Symbol Daily Cap to Prevent COT Over-Emission (CT=F Artifact)
- **What:** Enforce a hard cap of **1 pick per (symbol, strategy, direction) per calendar day** in the emission path. The falsified CT=F DSR=1.0 claim (2026-05-13) was caused by 6.33x over-emission from `copy_trader_intel/multi_asset_copytrader_scraper.py` emitting 14 COT cotton signals/day.
- **Expected Impact:** Eliminates future over-emission artifacts; DSR calculations become trustworthy.
- **Effort:** 1-2 days.
- **File/Location:** `audit_trail/quality_gates.py` (add dedup gate) or `copy_trader_intel/multi_asset_copytrader_scraper.py` (source-side throttle).
- **Verification:** Run `tests/test_cot_paper_pilot_dedup.py` after implementation.

### 2.2 Data Freshness Guard for Futures yfinance Feeds
- **What:** In `alpha_engine/futures_strategies.py`, add a staleness check: if `df.index[-1]` is > 2 trading days old, skip the symbol and log a warning. The YM=F ghost originated from a 26-day-stale `dashboard_data.json` that was never invalidated.
- **Expected Impact:** Prevents ghost picks and false signals on stale OHLCV.
- **Effort:** 1 day.
- **File/Location:** `alpha_engine/futures_strategies.py` (inside each strategy function or in `_futures_tp_sl`).

### 2.3 Replace Crypto Proxies with Real Commodity Futures in `commodity_signal_generator.py`
- **What:** The current generator uses RNDRUSDT/ARBUSDT as "silver proxies" and XLMUSDT/DOTUSDT as "oil proxies." This is conceptually broken for a COMMODITY asset class. Rewrite `get_klines()` to pull real futures data (GC=F, SI=F, HG=F, CL=F) via yfinance, matching the pattern used in `alpha_engine/futures_strategies.py`.
- **Expected Impact:** COMMODITY signals actually represent commodities; correlation with CRYPTO drops; asset-class integrity is restored.
- **Effort:** 2-3 days.
- **File/Location:** `alpha_engine/commodity_signal_generator.py`

---

## 3. LONG-TERM FIXES (1-2 weeks)

### 3.1 Rebuild COMMODITY from Fundamental Non-Price Signals
- **What:** The COT path is permanently discredited (over-emission, look-ahead leakage). Build new signal modules using:
  - **Term structure:** backwardation/contango slope from continuous futures
  - **Inventory deltas:** EIA crude/gasoline/storage weekly deltas
  - **Weather overlays:** degree-day anomalies for natgas/grains
- **Expected Impact:** Orthogonal alpha uncorrelated with CRYPTO/EQUITY; credible edge for a restarted COMMODITY class.
- **Effort:** 1-2 weeks.
- **File/Location:** New modules `alpha_engine/commodity_term_structure.py`, `alpha_engine/commodity_inventory_report.py` (partially exists), `alpha_engine/commodity_weather_overlay.py`

### 3.2 30-Day Futures Paper-Trading Track Record
- **What:** Before any capital allocation, run the 4 unblocked futures strategies in paper-trading mode with full TP/SL/time-exit resolution. Log every pick to `paper_trading/ledger/futures_paper_ledger.json`.
- **Expected Impact:** Evidence-based go/no-go decision; satisfies the M-055 minimum-sample gate for live trading.
- **Effort:** 1 week (passive observation after setup).
- **File/Location:** `paper_trading/strategies/proven_winners.py` (already imports futures modules), new ledger file.

### 3.3 Unified Non-Crypto Scan in `production_scanner.py`
- **What:** FOREX, COMMODITY, FUTURES, and BOND are currently siloed in separate agents/scripts with no shared scheduling or data fetching. Create a single `non_crypto_scan()` coroutine in `production_scanner.py` that fetches yfinance data once, runs all non-crypto strategies, and applies统一的 (unified) quality gates.
- **Expected Impact:** Eliminates stale-data races, reduces maintenance burden, makes unblocking FOREX/BOND trivial later.
- **Effort:** 1-2 weeks.
- **File/Location:** `alpha_engine/production_scanner.py`

---

## 4. VERDICT: Retire or Restart?

### FUTURES — **RESTART (do not retire)**
- **Evidence:** The 4 strategies are academically sound (Moskowitz et al. 2012, Connors & Alvarez 2008, Gargano et al. 2019), code bugs were fixed in April 2026, and the asset class has zero live picks only because of a config flag (`BLOCKED_ASSET_CLASSES`).
- **Path forward:** Execute Quick Win 1.1 (unblock), 1.2 (purge ghost), and 2.2 (freshness guard). Begin Medium Fix 3.2 (paper track record) immediately.
- **Risk:** Low. The strategies are already vetted; we are removing an administrative kill switch, not launching unproven code.

### COMMODITY — **RETIRE THE COT PATH; RESTART ONLY AFTER GROUND-UP REBUILD**
- **Evidence:** The asset class has been clinically dead for 5 months. Its last signal source (COT/CT=F cotton) was falsified on 2026-05-13 via 6.33x over-emission. The replacement generator uses crypto proxies (RNDRUSDT for silver), which is nonsensical for a commodity product.
- **Path forward:**
  1. Permanently blacklist all COT-derived commodity strategies in `BLOCKED_ASSET_STRATEGY_PAIRS`.
  2. Execute Quick Win 1.3 (wire the generator) ONLY after Medium Fix 2.3 (real futures data) is complete.
  3. Invest 1-2 weeks in Long-Term Fix 3.1 (fundamental signals) before declaring COMMODITY live-ready.
- **Risk:** High if restarted prematurely. Without a rebuilt signal stack, COMMODITY will emit garbage or silence again.

---

## Appendix: Key Files Reference

| File | Relevance |
|------|-----------|
| `audit_trail/quality_gates.py` | `BLOCKED_ASSET_CLASSES`, `BLOCKED_ASSET_STRATEGY_PAIRS`, `BLOCKED_DIRECTION_TRIPLES` |
| `alpha_engine/futures_strategies.py` | 4 vetted futures strategies (TSMOM, ConnorsRSI2, Cross-Asset, Vol-Breakout) |
| `alpha_engine/commodity_signal_generator.py` | Standalone generator with crypto proxies — needs pipeline wiring + data rewrite |
| `alpha_engine/commodity_kill_switch.py` | Blocks toxic inverse commodity strategies (keep active) |
| `non_crypto_agent/main.py` | Non-crypto emission pipeline entry point |
| `audit_trail/universal_pick_resolver.py` | Expires stale picks |
| `audit_trail/dashboard_generator.py` | Regenerates `dashboard_data.json` |
| `copy_trader_intel/multi_asset_copytrader_scraper.py` | Source of CT=F COT over-emission |
| `paper_trading/strategies/proven_winners.py` | Existing futures strategy imports for paper mode |
