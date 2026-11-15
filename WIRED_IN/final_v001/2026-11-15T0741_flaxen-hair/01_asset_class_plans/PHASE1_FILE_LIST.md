# PHASE 1 — File & Folder List for Sub-Agent Context

**Worktree:** flaxen-hair_2026-11-15T0234_flaxen-hair  
**Purpose:** Give sub-agents a head start by pointing them to exact files and folders to read first, so they don't waste time discovering the repository structure.

---

## TIER 1 — CRITICAL (Read first — these contain the core data)

| # | File Path | Why It Matters |
|---|-----------|----------------|
| 1 | `multi_asset/data/multi_asset_picks.json` | 41 active picks, all `forward_test_only=true`, `pnl_pct=null`. No live PnL exists yet. |
| 2 | `multi_asset/data/multi_asset_closed.json` | 93 closed picks (~8 months old, dated 2026-03-11 to 2026-03-13). Mixed PnL units (ratio vs percent ×100). Contains duplicate pick IDs. |
| 3 | `multi_asset/data/institutional_picks.json` | 22 picks, all OPEN, dated 2026-04-03 (~7.5 months old). All stale, never resolved. All `forward_test_only=true`, `pnl_pct=null`. |
| 4 | `multi_asset/data/institutional_closed.json` | 23 closed picks, mixed PnL units, stale (~8 months old). |
| 5 | `alpha_engine/risk_qa_validator.py` | QA validation framework — PnL=0% detection, blank field flags, stale data detection. |
| 6 | `alpha_engine/data/forward_testing/forward_tracker.py` | Forward-test tracker with K1–K8 kill signals and P1–P7 promote signals. Currently empty (no trades logged yet). |

---

## TIER 2 — HIGH PRIORITY (Read second — strategy definitions)

| # | File Path | Why It Matters |
|---|-----------|----------------|
| 7 | `alpha_engine/equity_strategies.py` | 15+ equity strategies defined (Connors RSI2, VIX spike reversal, dual momentum, etc.) |
| 8 | `alpha_engine/crypto_strategies.py` | 35+ crypto strategies (MACD, RSI, Bollinger, ML-enhanced, etc.) |
| 9 | `multi_asset/forex_strategies.py` | Forex strategies (RSI mean reversion, carry momentum, etc.) |
| 10 | `multi_asset/commodity_futures_strategies.py` | Commodity futures strategies (14 strategies: momentum, COT positioning, etc.) |
| 11 | `alpha_engine/bond_strategies.py` | Bond strategies (7 strategies: treasury yield curve, credit spread, duration rotation, bond equity rotation, etc.) |
| 12 | `alpha_engine/mutual_fund_strategies.py` | **DOES NOT EXIST** — confirms zero mutual fund coverage |
| 13 | `alpha_engine/antigravity_strategies.py` | Antigravity strategy implementations (8 crypto strategies, 4 equity strategies) |

---

## TIER 3 — MEDIUM PRIORITY (Read third — configuration & infrastructure)

| # | File Path | Why It Matters |
|---|-----------|----------------|
| 14 | `alpha_engine/asset_class.py` | Asset class mapping — no `MUTUAL_FUND` entry (confirms zero mutual fund coverage) |
| 15 | `alpha_engine/config.py` | Strategy family configuration, scoring config |
| 16 | `ml_gatekeeper/gatekeeper.py` | ML gatekeeper — no `MUTUAL_FUND` entry in `ASSET_CLASS_MAP` (confirming zero mutual fund coverage) |
| 17 | `audit_dashboard/dashboard_generator.py` | Dashboard generation — no mutual fund tile/bucket |
| 18 | `alpha_engine/scanner.py` | Production scanner engine — entry point for strategy execution |
| 19 | `alpha_engine/production_scanner.py` | Production scan orchestrator |

---

## TIER 4 — REFERENCE (Read as needed)

| # | File Path | Why It Matters |
|---|-----------|----------------|
| 25 | `multi_asset/data/multi_asset_closed.json` | Full closed-pick history (93 rows) |
| 26 | `multi_asset/data/institutional_closed.json` | Institutional closed picks (23 rows) |
| 27 | `multi_asset/data/institutional_picks.json` | Institutional open picks (22 picks, all stale from 2026-04-03) |
| 28 | `dashboard/live_picks.json` | Live dashboard picks (12 active picks, all OPEN, all `pnl_pct=null`) |

---

## TIER 5 — DOCUMENTATION (Read last, for context)

| # | File Path | Why It Matters |
|---|-----------|----------------|
| 29 | `WIRED_IN/flaxen-hair_2026-11-15T0234_flaxen-hair/README.md` | WIRED_IN package overview |
| 30 | `WIRED_IN/flaxen-hair_2026-11-15T0125/01_specification/ASSET_CLASS_SPECIFICATIONS.md` | Detailed per-asset-class findings |
| 31 | `WIRED_IN/flaxen-hair_2026-11-15T0125/02_justification/PREDICTION_MARKET_COPY_TRADING_AUDIT.md` | Prediction market & copy trader audit |
| 32 | `WIRED_IN/flaxen-hair_2026-11-15T0125/03_backtest_results/BACKTEST_AND_TRACKING_PROTOCOL.md` | Forward-test protocol details |
| 33 | `WIRED_IN/flaxen-hair_2026-11-15T0125/04_elimination_reasoning/` | Per-asset-class elimination reasoning |
| 34 | `WIRED_IN/flaxen-hair_2026-11-15T0125/05_irony_resolution/` | The irony: picks vs "no asset class proven profitable" |

---

## QUICK REFERENCE — Files to READ FIRST (Top 5)

If you only have time to read 5 files, read these in order:

1. `multi_asset/data/multi_asset_picks.json` — See what picks exist and their current state
2. `multi_asset/data/multi_asset_closed.json` — See what closed picks exist and their performance
3. `alpha_engine/equity_strategies.py` — See what equity strategies exist
4. `alpha_engine/risk_qa_validator.py` — Understand QA validation framework
5. `WIRED_IN/flaxen-hair_2026-11-15T0234_flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` — Overall summary

---

## QUICK REFERENCE — Files to WRITE NEW (if needed)

| # | File Path | Purpose |
|---|-----------|---------|
| A | `alpha_engine/mutual_fund_strategies.py` | Create — mutual fund strategies do not exist |
| B | `alpha_engine/data/mutual_fund_metadata.csv` | Create — mutual fund metadata CSV |
| C | `audit_dashboard/data/mutual_fund_nav_cache/` | Create — NAV cache directory for mutual fund data |
| D | `alpha_engine/data/mutual_fund_metadata.json` | Create — mutual fund metadata JSON |

---

## FILES TO IGNORE (Do NOT Modify)

| File | Reason |
|------|----------|
| `WIRED_IN/2026-11-15_0128_buffy/` | Another agent's worktree — do not modify |
| `COMMUNITY/` | Community agent workstream — do not modify |
| `ServiceNowMidServer/`, `ServiceNow_ServiceGraph_Lab/` | Other workstreams — do not modify |
| `___HELL_HEALTH_OPENCODE.MD` | Pre-existing file — do not modify |
| `WIRED_IN/CRYPTO_ASSET_CLASS_AUDIT.md` | Another agent's file — do not modify |
| `WIRED_IN/MUTUAL_FUNDS_ASSET_CLASS_AUDIT.md` | Another agent's file — do not modify |
| `WIRED_IN/NONCRYPTO_ASSET_CLASS_AUDIT.md` | Another agent's file — do not modify |
| `WIRED_IN/CRYPTO_ASSET_CLASS_AUDIT.md` | Another agent's file — do not modify |
