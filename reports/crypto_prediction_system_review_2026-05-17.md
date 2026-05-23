# Crypto Prediction System Review — Pipeline Applicability Audit
**Date:** 2026-05-17
**Source:** `C:/Users/zerou/Downloads/crypto-prediction-system-review (3)/src/`
**Files reviewed:** `App.tsx`, `components/CodeBlock.tsx`, `utils/cn.ts`, `main.tsx`

---

## Executive Summary

The reviewed files are a React/TypeScript **interactive gap-analysis document** — a single-page app that presents 5 production gaps in the existing `crypto_ml_edge` / `coinglass_strategies` pipeline. The code itself is a UI for displaying structured data (gap cards, code diffs, architecture diagrams). The substantive content is the **gap data embedded in `App.tsx`** (lines 43–837): each gap entry contains exact file targets, code diffs, constraints, and implementation risk assessments directly applicable to this repo's pipeline.

This review extracts only the items with direct applicability to the existing codebase.

---

## Applicable Pipeline Gaps (Ranked by Effort-to-Impact)

### Gap 1 — Open Interest Not in Feature Pipeline
**Target files:** `crypto_ml_edge/features/engine.py`, `coinglass_strategies/data_fetcher.py`
**Effort:** ~2 hours | **Risk:** Medium | **New APIs:** None (data already cached in `coinglass.db`)

**Finding:** OI data is already being fetched and stored in `coinglass.db` (table `open_interest`: symbol, oi_usd, oi_change_pct, ts) but `engine.py` does not read from it. The gap proposes two new features:
- `oi_change_pct_4h` — percent change in OI over 4 hours (1-bar at 4h timeframe)
- `oi_price_diverge` — binary flag when OI change and price change have opposite signs (precedes short squeezes)

**Applicability:** HIGH. The data exists, zero new API calls required, ffill reindex ensures no look-ahead leakage, and both features are purge-safe for walk-forward CV.

---

### Gap 2 — Garman-Klass Volatility Missing
**Target files:** `crypto_ml_edge/features/engine.py`
**Effort:** ~30 minutes | **Risk:** Low | **New APIs:** None

**Finding:** The pipeline uses ATR-only as its volatility estimator. Garman-Klass (GK) volatility uses the full OHLC structure (`0.5 * ln(H/L)^2 - (2*ln(2)-1) * ln(C/O)^2`) and is a more efficient estimator for intraday/4h bars. Correlation with ATR-14 is typically 0.6-0.8 — enough to provide marginal signal without multicollinearity. The gap proposes:
- `gk_vol_14` — GK vol over 14 bars
- `gk_vol_30` — GK vol over 30 bars (multi-scale view)

**Applicability:** HIGH. Pure additive feature, zero external deps, SHAP pruning in `trainer.py` will auto-detect redundancy with ATR. This is the highest effort-to-impact ratio item (30 minutes, medium signal potential).

---

### Gap 3 — No Order Book Imbalance (OBI) Features
**Target files:** `coinglass_strategies/orderbook_fetcher.py` (new), `crypto_ml_edge/features/engine.py`
**Effort:** ~4 hours | **Risk:** Medium | **New APIs:** Binance REST `/api/v3/depth?limit=5` (no auth)

**Finding:** No microstructure features exist in the pipeline. OBI = `(bid_qty - ask_qty) / (bid_qty + ask_qty)` at L1 is a well-established short-term directional predictor. The gap proposes a lightweight 4h REST poller storing to a new `orderbook_snapshots` table in `coinglass.db`, then wiring `obi_zscore_10` (rolling z-score over 10 snapshots) into `engine.py`.

**Applicability:** MEDIUM-HIGH. Cold-start issue: first ~12h produces z-scores of 0 (handled by `fillna(0)`). At 1 req/symbol/4h this is well within Binance's 1200 req/min non-auth limit. Pattern matches the existing SQLite caching pattern used for OI and funding rates.

---

### Gap 4 — On-Chain Metrics (NUPL, Exchange Netflow)
**Target files:** `coinglass_strategies/onchain_fetcher.py` (new), `audit_trail/quality_gates.py`
**Effort:** ~6 hours | **Risk:** HIGH | **New APIs:** CoinGlass API (requires key)

**Finding:** The system has `COINGLASS_API_KEY` env var but does not use NUPL (Net Unrealized Profit/Loss) or exchange netflow. These are **macro regime filters**, not per-trade features:
- NUPL > 0.75 = euphoria zone, historically precedes major BTC drawdowns → block LONGs
- NUPL < 0 = capitulation → block SHORTs
- Exchange netflow > $500M deposits = selling pressure → block LONGs

The gap implements these as env-var-gated (`ENABLE_ONCHAIN_REGIME=1`), fail-open gates in `quality_gates.py` — matching the approved gate pattern in this repo.

**Applicability:** HIGH for the gate logic in `quality_gates.py`; UNCERTAIN for the data source. **Warning:** CoinGlass NUPL API endpoint may not be publicly documented or may require a paid plan. The `onchain_fetcher.py` code uses a plausible path (`/public/v2/indicator?indicator=nupl`) that must be verified before deployment.

**Alignment with expert findings:** This directly implements the NUPL regime filter cited by Ernie and Xiao Mi Mimo as P1 action item.

---

### Gap 5 — Multi-Exchange Divergence (Binance vs Bybit)
**Target files:** `coinglass_strategies/cross_exchange_fetcher.py` (new), `crypto_ml_edge/features/engine.py`
**Effort:** ~3 hours | **Risk:** Medium | **New APIs:** Bybit `/v5/market/tickers` (no auth)

**Finding:** System uses Binance exclusively for price data. When Binance spot and Bybit perps diverge by >0.3%, it signals liquidity imbalance, cross-exchange arbitrage opportunity, or exchange lag. The gap proposes:
- `bybit_binance_spread_bps` — cross-exchange spread in basis points
- `cross_exchange_spread_abs` — absolute spread as a volatility proxy

**Applicability:** MEDIUM. Bybit perp prices include funding cost, so a small persistent basis vs Binance spot is expected (0-5 bps). The model must learn to distinguish persistent basis from divergence spikes. At 1 req/symbol/4h this is well within Bybit's public rate limit (10 req/sec). The API requires no authentication.

---

## Pipeline Architecture Confirmed (Already Implemented — Do Not Re-implement)

The review document explicitly calls out the following as already implemented in this repo. Confirmed to avoid duplicate work:
- Triple-barrier labeling with cost gates
- Walk-forward 5-fold CV with 20-bar purge + 1% embargo
- Deflated Sharpe Ratio gate (p_dsr >= 0.05)
- Fractional differentiation at d=0.4
- LightGBM + Optuna hyperparameter search
- SHAP feature pruning + isotonic calibration
- Funding rate z-score and momentum features
- Long/Short ratio from CoinGlass
- HMM regime detection (bull/bear/chop)
- 15+ system ensemble voting + conflict detection
- XGBoost as second ensemble model
- Asset-class smart gates (`ASSET_CLASS_SMART_THRESHOLDS`)
- PNL threshold by class (CRYPTO=0.1bp)

---

## Audit Dashboard Patterns Applicable to `audit_dashboard/template.html`

The React app's architecture reveals the following UI/data model patterns that the static audit dashboard could adopt:

### 1. Gap Card Pattern with Risk-Tiered Badging
The app uses a structured `GapData` interface with `risk: 'high' | 'medium' | 'low'` and colored badges. The audit dashboard could adopt this pattern for the per-asset-class health cards — color-coded by tier (T1/T2/sub-floor) rather than risk level, with expandable code diff sections for each proposed fix.

### 2. "Already Implemented" Section
The app has an explicit "Already Implemented (Do Not Re-implement)" section that prevents redundant work. The audit dashboard's `update-entry` cards could include a similar "implemented" vs "proposed" state with a visual distinction.

### 3. Pipeline Flow Diagram
The app renders a horizontal step-by-step pipeline diagram (Raw OHLCV → Feature Engine → Triple-Barrier → LightGBM+XGB → Walk-Forward CV → DSR Gate → Ensemble Vote → Quality Gates → Audit Dashboard). This could be embedded in `audit_dashboard/template.html` as a static HTML/CSS flow showing the exact pipeline path that produces the dashboard numbers — useful for operator transparency.

### 4. Priority Matrix Table
The summary section's priority matrix table (Priority / Gap / Risk / Effort / Impact / New APIs / Pipeline Safe) is a high-signal pattern for the audit dashboard's "action items" section. The current dashboard shows performance metrics but lacks a ranked action items table with effort estimates.

### 5. Scoring Model: `GapData.effort` + `GapData.risk` Fields
The `effort` field is a human-readable string (e.g., "~2 hours") and `risk` is a typed enum. The audit dashboard's `performance.asset_class_health` JSON could add analogous `rescue_effort` and `rescue_risk` fields to each asset class entry, driving a sortable action-priority UI.

---

## Implementation Sequence Recommendation

| Priority | Gap | File | Effort | Blocker |
|----------|-----|------|--------|---------|
| 1 | GK Volatility | `crypto_ml_edge/features/engine.py` | 30m | None |
| 2 | OI Features | `crypto_ml_edge/features/engine.py` | 2h | Verify `coinglass.db` has `open_interest` table |
| 3 | Cross-exchange Divergence | `coinglass_strategies/cross_exchange_fetcher.py` | 3h | None (Bybit public API) |
| 4 | OBI Features | `coinglass_strategies/orderbook_fetcher.py` | 4h | Cold-start period |
| 5 | NUPL/Netflow Gates | `coinglass_strategies/onchain_fetcher.py` + `quality_gates.py` | 6h | Verify CoinGlass NUPL endpoint availability |

**Total:** ~16 hours, 0 breaking changes, 7 new features added to the ML pipeline.

---

## Key Safety Constraints (All 5 Gaps)

1. All new features use `ffill` reindex against the OHLCV time index — no look-ahead leakage
2. Walk-forward CV with purge gap is preserved — features are row-aligned
3. DSR gate remains active — no bypasses proposed in any gap
4. Gap 4 regime filter uses the approved `env-var-gated, fail-open try/except` pattern
5. All new SQLite tables use `(symbol, ts) PRIMARY KEY` matching the existing schema convention
6. `fillna(0)` handles cold-start and missing data gracefully — model learns to downweight absent features
