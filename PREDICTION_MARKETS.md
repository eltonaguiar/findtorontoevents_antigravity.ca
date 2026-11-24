# PREDICTION_MARKETS.md

**Status:** Structural inventory + registry wiring (OPEN_TODOS #17)
**Date:** 2026-11-18
**Repo root:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/`

---

## 1. Scope

Prediction-market signals are already wired into the live alpha pipeline via `prediction_market_agents/orchestrator.py`. They feed `alpha_engine/data/active_picks.json` under `source_system: "prediction_market_agents"`, `strategy: "prediction_market_consensus"`. The missing gate is **M-107 pre-registration**: no `PREDICTION_MARKET` asset_class exists in `reports/hypothesis_registry.json`, and no PM hypotheses are filed.

This document:
- Inventories the 11 agents + data artifacts.
- Documents known defects / gating.
- Registers the first PM hypotheses as a **new additive block** (`prediction_market_2026_11_18`) following the lane pattern already used for `fund_durability_2026_10_23`, `copilot_fund_etf_simulation_2026_11_15`, etc.

---

## 2. Agent Inventory (prediction_market_agents/)

| File | Role | Key Constants / Notes |
|------|------|-----------------------|
| `orchestrator.py` (437 LOC) | Agent 5; pipeline coordinator | `MAX_SIGNAL_AGE_HOURS=12`, `MIN_MERGE_CONFIDENCE=0.60` (lowered from 0.80), `MERGEABLE_STRATEGIES={"prediction_market_consensus"}`. Output: `alpha_engine/data/active_picks.json`. |
| `cross_market_consensus.py` (16.8 kB) | Agent 4; weighted consensus | Merges whale + momentum + Kalshi + other. Output: `data/consensus_signals.json`. |
| `kalshi_signal_agent.py` (19.8 kB) | Agent 3; Kalshi multi-timeframe | Public endpoint `https://api.elections.kalshi.com/trade-api/v2/events` + `/markets`; **no API key**. Series_ticker based (fixed from keyword filter that returned 0 events). Timeframes: 15m/1h/1d/1w/1m/1y. |
| `polymarket_momentum_agent.py` (6.5 kB) | Agent 2; momentum wrapper | Thin wrapper over `alpha_engine.polymarket_signals` (crypto-only). |
| `polymarket_whale_tracker.py` (45.1 kB) | Whale scanner + direct fallback | Consumes shared `copy_trader_intel.polymarket_scraper`; outputs `data/whale_tracker.json`. |
| `polymarket_strategy_audit.py` (11.2 kB) | Audit snapshot | FOCUS_KEYS list (0x8dxd, justdance, bonereader, coinman2, …). Imports `_score_wallet`, `fetch_candidate_leaderboard`. |
| `polymarket_btc_updown_agent.py` (11.1 kB) | Opt-in sidecar (DRY_RUN) | Quarter-Kelly, Brownian-motion prob model, circuit breaker (3 losses), CLOB v2 read-only. Env: `DRY_RUN=true`, `PM_BTC_SYMBOLS`, `PM_MIN_EDGE=0.06`, `PM_MAX_KELLY_FRACTION=0.25`, `PM_BANKROLL=100`, `PM_CIRCUIT_BREAKER=3`. Target promotion ~2026-07-01 after ≥4w dry-run. |
| `pm_odds_history.py` (15.3 kB) | Persistence sidecar | `data/pm_odds_history.jsonl` (one row per snapshot). `--backfill` mode. Read-only, non-fatal in `alpha-engine-live.yml`. |
| `pm_lead_lag_analyzer.py` (14.3 kB) | IDEA-H lead/lag | Cross-correlates daily odds vs. underlying (TLT, EURUSD=X) at lags −3..+3. Classifies LEADING/COINCIDENT/REACTIVE/NO_SIGNAL (\|r\|≥0.30). Requires ≥20 daily snapshots. **Leakage caveat**: consumers must use a report generated strictly before the pick timestamp. Output: `data/pm_leadlag_report.json`. |
| `pm_macro_overlay.py` (16.1 kB) | IDEA-H Phase 1 (2026-06-06) | Kalshi + Polymarket Fed-rate probabilities. When both >70% agree → FOREX (EUR/GBP/NZD/AUD long/short on cut/hike) and bond-ETF (TLT/BND) picks. Tagged `forward_test_only=True` until 60d / n≥30. Called by `alpha-engine-live.yml` and `audit-dashboard.yml`. |
| `pm_hygiene.py` (4.0 kB) | Dedupe/staleness | Reads `audit_trail/data/universal_resolved_picks.json`; `MAX_CLOSED_AGE_HOURS=24`; composite key = symbol+direction+strategy. |
| `sports_prediction_market_bridge.py` (5.0 kB) | Sports additive | Polymarket sports markets → `live-monitor/api/sports_picks.php`. Uses `https://gamma-api.polymarket.com`. Does **not** touch the crypto-only `alpha_engine/polymarket_signals.py` pipeline. |

---

## 3. Data Outputs (prediction_market_agents/data/)

| File | Size | mtime | Notes |
|------|------|-------|-------|
| `pm_odds_history.jsonl` | 6.8 MB | 2026-11-18 00:27 | Primary time-series; append-only. |
| `pm_leadlag_report.json` | 373 kB | 2026-11-18 00:27 | Lead/lag classifications + leakage caveat. |
| `whale_tracker.json` | 24 kB | 2026-11-18 00:27 | Whale positions + scores. |
| `polymarket_strategy_audit.json` | 8.6 kB | 2026-05-25 | 6 months stale. |
| `whale_alerts.json` | 166 B | 2026-05-25 | Likely stale (empty alert set). |
| `orchestrator_summary.json` | 608 B | 2026-11-18 00:27 | Pipeline health snapshot. |
| `pm_macro_overlay_signals.json` | 122 B | 2026-11-18 00:27 | Fed-rate consensus signals. |

---

## 4. Known Defects / Gating

1. **Kalshi zero-event bug (historical)**: keyword filter returned 0 events; fixed by switching to `series_ticker`-based fetch in `kalshi_signal_agent.py`.
2. **BTC up/down agent gated**: `DRY_RUN=true` required; promotion target ~2026-07-01 after ≥4 weeks dry-run + edge ≥0.08.
3. **Stale audit artifacts**: `polymarket_strategy_audit.json` (May 25), `whale_alerts.json` (May 25) — 6 months old.
4. **Lead/lag leakage caveat**: `pm_lead_lag_analyzer.py` explicitly warns that consumers must use a report generated *strictly before* the pick timestamp.
5. **No M-107 registration**: PM signals merge into `active_picks.json` but are **not** pre-registered in `hypothesis_registry.json`. This is the gap addressed below.

---

## 5. Registry Wiring (M-107 Gate)

### 5.1 Decision

- Add a **new top-level block** `prediction_market_2026_11_18` (additive lane pattern) rather than mutating the 99 existing `hypotheses`.
- Asset class: `PREDICTION_MARKET` (new).
- Family limit: "Max 5 feature families per asset class" — we register **3 families** (macro_overlay, lead_lag, consensus) with room for 2 more.
- Status for all: `UNTESTED` (forward_test_only gate already present in macro overlay; lead/lag has leakage caveat).

### 5.2 Registered IDs

Max existing id was `H-140`; this block assigns `H-141` … `H-143`.

| ID | Family | Gate |
|----|--------|------|
| H-141 | `macro_overlay_fed_rate` | forward_test_only until 60d / n≥30 |
| H-142 | `lead_lag_underlying` | leakage guard: pre-pick report only |
| H-143 | `cross_market_consensus` | MIN_MERGE_CONFIDENCE=0.60, MAX_SIGNAL_AGE_HOURS=12 |

---

## 6. Constraints & Notes

- **No git commit / push / remote op** per coordinator rule.
- **Write to repo root only** — not to the brain artifact dir.
- **Family limit**: 3/5 registered; 2 slots remain (e.g. whale_leaderboard, sports_bridge).
- **Asset class `PREDICTION_MARKET`** does not collide with existing classes (BOND, CHEAP_STOCKS, COMMODITY, CRYPTO, EQUITY, ETF, FOREX, FUTURES, MEME, MULTI, PENNY_STOCK, SPORTS).
- The block lives in `reports/hypothesis_registry.json` starting at key `prediction_market_2026_11_18`; each record uses the standard record schema (`id`, `asset_class`, `family`, `description`, `test_statistic`, `acceptance_criteria`, `economic_prior`, `status`, `registered_at`, `data_sample_lock`, `result`).

---

**End of PREDICTION_MARKETS.md**
