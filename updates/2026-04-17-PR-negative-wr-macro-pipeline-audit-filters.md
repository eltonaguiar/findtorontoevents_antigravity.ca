# PR: Fix Negative Win-Rate, Add Macro Pipeline + Audit Dashboard Filters

**Branch:** `fix/negative-wr-macro-audit-2026-04-17`  
**Date:** 2026-04-17  
**Scope:** Alpha engine data pipeline, circuit-breaker integration, audit dashboard UX, and hyrotrader resilience.

---

## Problem Statement

1. **Negative win-rate across the board** — the aggregate closed-pick book shows 32.3% WR / PF 0.4 because low-expectancy strategies (especially `quan_engine_scalp`) drown out the few verified edges.
2. **No macro overlay** — the system trades without awareness of yield-curve inversion, Fed policy, or liquidity regimes.
3. **Audit dashboard lacks recency filters** — users cannot see "last 20 picks" or "latest active + closed per strategy", making it impossible to spot when a newly-added strategy is actually winning.
4. **HyroTrader page shows mostly `NO_DATA`** — Binance API timeouts and no fallback data source.

---

## What Changed

### 1. Macro Data Pipeline — Yield Curve + Fed Policy + Dual-Source Failover

**New files:**
- `alpha_engine/macro_data_pipeline.py` — Fetches `T10Y2Y`, `T10Y3M`, `DFF` from FRED. Falls back to Yahoo Finance v8 chart API / yfinance. Computes `macro_risk_score` (-1..1) and per-asset-class regime labels.
- `tools/run_macro_update.py` — Cron/CI runner.
- `alpha_engine/data/macro_factors_snapshot.json` — Now populated (v2 schema).
- `alpha_engine/data/macro_circuit_breaker.json` — Breaker state written by the pipeline.

**Modified:**
- `alpha_engine/fred_liquidity.py` — Stripped trailing whitespace from `FRED_API_KEY` read (was breaking every FRED URL with "control characters" error).

**Circuit-breaker behavior:**
- If both FRED and Yahoo fail 3 times within 1 hour, the breaker trips `OPEN`.
- Open state writes `{"active": true, "level": "RED", "reason": "dual_source_failure", "timestamp": "..."}` so `circuit_breaker_aggregator.py` can read it.
- Cleared state writes `{"active": false, "level": "GREEN", ...}`.

### 2. Unified Circuit Breaker + Production Scanner Integration

**New file:**
- `alpha_engine/circuit_breaker_aggregator.py` — Reads drawdown, portfolio, and macro breaker states. Returns one unified decision (`GREEN/YELLOW/RED/HALT`) with `max_picks` and `min_confidence`.

**Modified:**
- `alpha_engine/production_scanner.py` — 
  - Calls `get_unified_breaker_state()` at start of `main()`; `HALT` aborts generation immediately.
  - Refreshes macro snapshot before signal generation.
  - Adjusts `MAX_ACTIVE_PICKS` and `QUALITY_GATE_MIN_CONFIDENCE` based on macro risk score (-0.8 = -50% picks, +0.10 conf; -0.5 = -25% picks, +0.05 conf).
  - Blocks EQUITY/ETF picks when yield curve is inverted **and** Fed is hiking, unless `conf >= 0.90`.
  - Attaches `attach_macro_overlay()` to every surviving pick.
  - Applies `apply_macro_risk_off_gate()` — picks with `macro_score < -0.5` and `conf < 0.90` are rejected; `conf >= 0.90` survive with 0.5× sizing.
  - Restores original constants at end of `main()` to avoid side effects on re-entry.

### 3. Audit Dashboard — Last N Picks + Latest Per Strategy

**Modified:**
- `audit_dashboard/template.html`
  - **Last N filter:** Dropdowns in both Crypto and Non-Crypto panels (options: Last 10, 20, 50, 100, All Time). Default is `Last 20`. Filtering keeps the N most recent closed picks plus any active picks opened on or after the oldest of those N.
  - **Strategy view toggle:** New "Category view / ✓ Strategy view" button for non-crypto and new "Latest/Strat" split-mode for crypto.
  - **Latest Active + Latest Closed per Strategy cards:** Each strategy card shows the most recent active pick (symbol, entry, unrealized PnL), most recent closed pick (symbol, exit reason, realized PnL), and mini stats from the last 10 closed picks for that strategy only (WR, PF, avg PnL).

### 4. HyroTrader Resilience + Data-Quality Improvements

**Modified:**
- `tools/hyro_pick_performance_validator.py`
  - Adds `extract_signals_from_closed_picks()` — pulls crypto closed picks from `alpha_engine/data/closed_picks.json` as a pre-validated, API-free data source.
  - Binance kline fetch now retries up to 2 times across mirrors with 1s sleep between rounds.
  - Symbol normalization for Binance compatibility.
  - Signal cap raised to 500 recent signals; lookback extended to 30 days.
- `audit_dashboard/hyrotrader/index.html`
  - Better handling for sparse/NO_DATA signals.
  - Improved "no numeric prices" helper text.

---

## Research & Recovery Plans (Documentation Only)

The following `.md` files contain deep-dive findings and **proposed** (not yet implemented) tactical fixes:

- `updates/2026-04-17-crypto-winrate-recovery-plan.md` — Crypto WR diagnosis: only confidence 0.8–0.9 and R:R 1.0–1.5 are profitable. `quan_engine_scalp` is the biggest drag (29.2% WR, PF 0.39). Recommendations: kill/score-penalize sub-0.7 conf scalps, raise sizing on 0.8+ conf proven ML picks.
- `updates/2026-04-17-noncrypto-winrate-recovery-plan.md` — Non-crypto crisis is largely a **pipeline-wiring** problem: dedicated `equity_strategies.py`, `forex_strategies.py`, etc. are orphaned and never called by `production_scanner.py`. Actual non-crypto picks come from unvalidated copy-trader scrapers with 0–3% WR. Recommendations: disable toxic scrapers, wire real strategy modules, add per-asset-class confidence gates.
- `updates/2026-04-17-audit-dashboard-filters.md` — UI filter documentation.
- `updates/2026-04-17-circuit-breaker-integration.md` — Integration architecture and testing notes.
- `updates/2026-04-19-hyrotrader-audit-dashboard-fixes.md` — HyroTrader front-end and backend enrichment details.

---

## Verification Steps

1. **Syntax**
   ```bash
   python -c "import py_compile; py_compile.compile('alpha_engine/macro_data_pipeline.py', doraise=True); py_compile.compile('alpha_engine/circuit_breaker_aggregator.py', doraise=True); py_compile.compile('alpha_engine/production_scanner.py', doraise=True); py_compile.compile('alpha_engine/fred_liquidity.py', doraise=True); py_compile.compile('tools/run_macro_update.py', doraise=True); py_compile.compile('tools/hyro_pick_performance_validator.py', doraise=True)"
   ```

2. **Macro pipeline dry run**
   ```bash
   python tools/run_macro_update.py
   cat alpha_engine/data/macro_factors_snapshot.json
   cat alpha_engine/data/macro_circuit_breaker.json
   ```

3. **Audit dashboard locally**
   ```bash
   python tools/serve_local.py
   # Open http://127.0.0.1:5173/audit/
   # Toggle "Last N" dropdowns and "Strategy view" buttons.
   ```

4. **HyroTrader validator**
   ```bash
   python tools/hyro_pick_performance_validator.py --save --lookback-days 30
   ```

---

## Safety Checklist

- [x] No hard crashes — all new imports in `production_scanner.py` are wrapped in `try/except ImportError`.
- [x] No breaking changes to existing circuit-breaker files (`drawdown_circuit_breaker.py`, `portfolio_circuit_breaker.py` left untouched).
- [x] Macro data pipeline degrades gracefully if FRED/Yahoo both fail (returns neutral default snapshot).
- [x] `MAX_ACTIVE_PICKS` and `QUALITY_GATE_MIN_CONFIDENCE` are restored at end of scanner `main()`.
- [x] All Windows-safe file I/O uses `encoding="utf-8"`.
- [x] Nothing pushed to `main` — this is a clean branch for PR review.

---

## Files Changed

| File | Action | Why |
|------|--------|-----|
| `alpha_engine/macro_data_pipeline.py` | Created | Yield curve + Fed policy fetcher with dual-source failover |
| `alpha_engine/circuit_breaker_aggregator.py` | Created | Unified drawdown/portfolio/macro breaker decision layer |
| `tools/run_macro_update.py` | Created | Cron/CI runner for macro pipeline |
| `alpha_engine/production_scanner.py` | Modified | Integrated macro gating, overlays, and unified breakers |
| `alpha_engine/fred_liquidity.py` | Modified | Fixed trailing space in `FRED_API_KEY` env read |
| `audit_dashboard/template.html` | Modified | Last N filters + latest-per-strategy cards |
| `audit_dashboard/hyrotrader/index.html` | Modified | Null-price handling, sparse-data notices |
| `tools/hyro_pick_performance_validator.py` | Modified | Closed-picks fallback source, retry logic, normalization |
| `alpha_engine/data/macro_factors_snapshot.json` | Updated | Populated with live v2 snapshot |
| `alpha_engine/data/macro_circuit_breaker.json` | Created | Current breaker state (`active: false`) |
