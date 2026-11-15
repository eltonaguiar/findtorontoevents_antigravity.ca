# Pick Pipeline — How Picks Flow Into findtorontoevents.ca/audit

This document explains the end-to-end pipeline for how picks move from generation → active monitoring → closed resolution → audit dashboard display. It also shows where the simulation candidate picks fit (and don't fit).

---

## Pipeline Overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   SCANNERS      │─────▶│  ACTIVE PICKS    │─────▶│   CLOSED PICKS  │
│ (alpha_engine,  │      │  active_picks.   │      │  closed_picks.  │
│  KIMI, genome,  │      │  json (per class)│      │  json           │
│  battleground,  │      │                  │      │                 │
│  etc.)          │      └──────────────────┘      └────────┬────────┘
└─────────────────┘                                       │
                                                          │ position closes / TP/SL hit
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  DASHBOARD GEN  │
                                                  │ audit_trail/    │
                                                  │ dashboard_gen.  │
                                                  │ erator.py       │
                                                  └────────┬────────┘
                                                           │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  AUDIT DASHBOARD│
                                                  │ findtorontoeve.  │
                                                  │ nts.ca/audit    │
                                                  │ (Active Picks,  │
                                                  │  Closed Picks   │
                                                  │  tabs)          │
                                                  └─────────────────┘
```

---

## Stage 1: Scanner Emits Pick → `active_picks_*.json`

Each scanner (alpha_engine, KIMI, genome, battleground, etc.) writes picks to its own `active_picks.json` file. The main `alpha_engine/data/active_picks.json` aggregates across scanners.

**Pick schema (matching your live files):**

| Field | Example | Description |
|-------|---------|-------------|
| `id` | `cta_golden_cross_200::SPY::2026-11-09_0309` | Unique pick ID |
| `strategy` | `cta_golden_cross_200` | Strategy name |
| `symbol` | `SPY` | Ticker symbol |
| `category` | `equity` | Asset class category |
| `signal_type` | `BUY` | BUY/SELL |
| `direction` | `LONG` | LONG/SHORT/FLAT |
| `entry_price` | `735.29` | Entry price |
| `entry_date` | `2026-11-09` | Entry date |
| `take_profit` | `763.08` | TP price |
| `stop_loss` | `718.62` | SL price |
| `confidence` | `0.68` | 0-1 confidence |
| `ml_score` | `0.6` | ML composite score |
| `status` | (absent for active) | Added when closed: WON/LOST/etc. |
| `pnl_pct` | (absent for active) | Added when closed |

**Active picks files in your repo:**
- `alpha_engine/data/active_picks.json` (149KB, 81 picks)
- `alpha_engine/data/active_picks_etf.json` (ETF picks)
- `alpha_engine/data/active_picks_bond.json` (bond picks)
- `alpha_engine/data/active_picks_fast.json` (149KB, fast scanner)
- `KIMI_RISEOFTHECLAW/data/active_picks.json`
- `genome/active_picks.json`
- `crypto_ml_edge/data/active_picks.json`
- `ml_battleground/ensemble_data/active_picks.json`

---

## Stage 2: Position Monitoring → Pick Closes

While a pick is active, the system monitors price vs TP/SL:

- If price hits TP → status = `TP_HIT`, pnl_pct = positive
- If price hits SL → status = `SL_HIT`, pnl_pct = negative
- If time exit → status = `TIME`, pnl_pct = at exit price
- If manually closed → status = `CLOSED`

The pick then moves from `active_picks_*.json` to `closed_picks.json` with status and PnL filled in.

**Closed picks files:**
- `alpha_engine/data/closed_picks.json` (503 picks)
- `alpha_engine/data/closed_picks_enriched.json`
- `paper_trading/data/closed_picks.json`
- Various scanner-specific closed_picks.json files

---

## Stage 3: Dashboard Aggregation → `audit_trail/dashboard_generator.py`

The dashboard generator (`audit_trail/dashboard_generator.py`, 18,741 lines) reads all active + closed picks across all scanner directories and produces:

- `audit_dashboard/data/picks_now.json` — all active picks
- `audit_dashboard/data/picks_now_live_pnl.json` — active picks with live PnL
- `audit_dashboard/data/summary_picks.json` — per-class summary stats
- `audit_dashboard/data/money_ready_verdict.json` — per-class money-ready verdicts
- `audit_dashboard/data/pf_registry.json` — registry PF/WR numbers

The dashboard at `findtorontoevents.ca/audit` reads these JSON files and displays:
- **Active Picks tab** — open positions with live PnL, TP/SL levels
- **Closed Picks tab** — historical picks with WON/LOST status, WR, PF per class

---

## Where Simulation Candidates Fit

**❌ They do NOT belong in live `active_picks.json`** — that would mix unproven simulation candidates with real scanner picks, confusing the dashboard and potentially leading to false confidence.

**✅ They belong in a segregated `simulation_candidate_picks.json`** (created at `01_asset_class_plans/candidate_picks/simulation_candidate_picks.json`) with these flags:

```json
{
  "status": "SIMULATION_CANDIDATE_FAILED_GATES",
  "monitoring_only": true,
  "not_for_real_money": true,
  "sizing_allowed": false,
  "money_ready": false,
  "gates_passed": 0,
  "gates_total": 7
}
```

These can be monitored alongside live picks but should be displayed in a **separate "Simulation Candidates"** section of the audit dashboard, clearly color-coded (e.g., gray/yellow) to distinguish from live picks (green/red).

---

## Stage 4: How to Feed Candidates Into Monitoring (Read-Only)

If you want to track these simulation candidates alongside live picks in the audit dashboard:

1. **Do NOT write to `alpha_engine/data/active_picks.json`** — keep live and simulation separate.

2. **Create a simulation monitoring file:**
   ```
   audit_dashboard/data/simulation_candidates.json
   ```
   This would contain the same picks from `candidate_picks/simulation_candidate_picks.json`, updated only when you re-run the simulation.

3. **Dashboard addition:** Add a "Simulation Candidates" tab/section to the audit dashboard that reads from `audit_dashboard/data/simulation_candidates.json` and displays:
   - Symbol, strategy, entry price, TP, SL
   - Backtest stats (WR, PF, net PnL, max DD, Sharpe, DSR, PBO)
   - Gates passed / total (e.g., "0/7")
   - Big red banner: "FAILED MONEY-READY GATES — NOT FOR REAL MONEY"
   - Live price vs entry (unrealized PnL) for reference only

4. **Forward testing:** If you want to forward-test these candidates, use the `FORWARD_TEST_TRACKING_PROTOCOL.md` protocol — track them in `forward_test_tracker.csv` with kill/promote signals. Do not size positions based on them.

---

## Files Created for This Purpose

| File | Purpose |
|------|---------|
| `01_asset_class_plans/candidate_picks/simulation_candidate_picks.json` | The 3 best simulation candidates (ADA-USD crypto, QQQ equity, EFA ETF), all flagged FAILED_GATES |
| `01_asset_class_plans/run_simulation_backtest.py` | Script to regenerate simulation picks |
| `01_asset_class_plans/SIMULATION_RESULTS.md` | Full simulation results summary |
| `01_asset_class_plans/simulation_results_2026-11-15.json` | Raw simulation output |
| `08_qa_validation/FORWARD_TEST_TRACKING_PROTOCOL.md` | Forward-test kill/promote protocol |

---

## Bottom Line

**No simulation candidate passed money-ready gates.** The 3 candidates shown are the "least bad" from 37 tested combos:
- ADA-USD EMA Trend: 0/7 gates passed (worst)
- QQQ DualMA: 4/7 gates passed but only 2 trades (statistical artifact)
- EFA DualMA: 4/7 gates passed but only 3 trades (statistical artifact)

Monitor them if you want, but **do not trade them.** The only capital deployment recommendation remains low-cost index ETF/MF passive allocation.
