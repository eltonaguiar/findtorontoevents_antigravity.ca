# 06_PIPELINE_INTEGRATION — How Picks Flow Into findtorontoevents.ca/audit

**Date:** 2026-11-15T07:44Z UTC  
**Purpose:** Document the end-to-end pipeline for how picks move from generation → active monitoring → closed resolution → audit dashboard display. Show where picks fit (and don't fit).

---

## Pipeline Overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   SCANNERS      │─────▶│  ACTIVE PICKS    │─────▶│   CLOSED PICKS  │
│  (alpha_engine,  │      │  active_picks.   │      │  closed_picks.  │
│   KIMI, genome,  │      │  json (per class)│      │  json           │
│   battleground,  │      │                  │      │                 │
│   etc.)          │      └──────────────────┘      └────────┬────────┘
└─────────────────┘      │      │                  │           │
                         │      │                  │           │
                         │      ▼                  │           │
                         │   QUALITY GATES      │           │
                         │   (quality_gates.py) │           │
                         │      │                  │           │
                         └──────────────────────┘           │
                                                            │
                                                            ▼
                                                    ┌─────────────────┐
                                                    │  DASHBOARD GEN  │
                                                    │  dashboard_gen. │
                                                    │  erator.py      │
                                                    └────────┬────────┘
                                                           │
                                                            ▼
                                                    ┌─────────────────┐
                                                    │  AUDIT DASHBOARD│
                                                    │  findtorontoeve. │
                                                    │ nts.ca/audit    │
                                                    │  (Active Picks, │
                                                    │  Closed Picks   │
                                                    │  tabs)          │
                                                    └─────────────────┘
```

## Stage 1: Scanner Emits Pick → `active_picks_*.json`

Each scanner (alpha_engine, KIMI, genome, battleground, etc.) writes picks to its own `active_picks.json` file. The main `alpha_engine/data/active_picks.json` aggregates across scanners.

### Pick Schema (matching live files)

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
| `ml_score` | `0.6` | ML score |
| `status` | (absent for active) | Added when closed: WON/LOST/etc. |
| `pnl_pct` | (absent for active) | Added when closed |

### Active Picks Files

| File | Count | Description |
|------|-------|-------------|
| `alpha_engine/data/active_picks.json` | 89 picks | Main aggregated active picks |
| `alpha_engine/data/active_picks_etf.json` | 14 picks | ETF-specific picks (draft, `is_draft: true`) |
| `alpha_engine/data/active_picks_fast.json` | 29 picks | Fast scanner picks |
| `alpha_engine/data/active_picks_bond.json` | 6 picks | Bond picks |
| `KIMI_RISEOFTHECLAW/data/active_picks.json` | ? | KIMI claw picks |
| `genome/data/active_picks.json` | ? | Genome picks |
| `crypto_ml_edge/data/active_picks.json` | ? | Crypto ML edge picks |
| `ml_battleground/ensemble_data/active_picks.json` | ? | ML battleground picks |
| `rapid_fire_data/active_picks.json` | ? | Rapid fire picks |
| `crypto_signal_engine/data/active_picks.json` | ? | Crypto signal engine picks |

### Active Picks by Category (from `active_picks.json`)

| Category | Count |
|----------|-------|
| crypto | 58 |
| equity | 4 |
| forex | 11 |
| stocks | 7 |
| index | 1 |
| commodity | 8 |
| Total | 89 |

**Note:** No `mutual_fund` category exists. No `mutual_fund` picks are emitted.

---

## Stage 2: Position Monitoring → Pick Closes

While a pick is active, the system monitors price vs TP/SL:

- If price hits TP → status = `TP_HIT`, pnl_pct = positive
- If price hits SL → status = `SL_HIT`, pnl_pct = negative
- If time exit → status = `TIME`, pnl_pct = at exit price
- If manually closed → status = `CLOSED`

The pick then moves from `active_picks_*.json` to `closed_picks.json` with status and PnL filled.

### Closed Picks Files

| File | Count | Description |
|------|-------|-------------|
| `alpha_engine/data/closed_picks.json` | 503 picks | Main closed picks |
| `alpha_engine/data/closed_picks_enriched.json` | ? | Enriched closed picks |
| `paper_trading/data/closed_picks.json` | ? | Paper trading closed picks |
| `KIMI_RISEOFTHECLAW/data/closed_picks.json` | ? | KIMI claw closed picks |
| `genome/data/closed_picks.json` | ? | Genome closed picks |
| `crypto_ml_edge/data/closed_picks.json` | ? | Crypto ML edge closed picks |
| `ml_battleground/system_*/closed_picks.json` | ? | ML battleground closed picks |
| `battleground/data/closed_picks.json` | ? | Battleground closed picks |

---

## Stage 3: Dashboard Aggregation → `audit_trail/dashboard_generator.py`

The dashboard generator (`audit_trail/dashboard_generator.py`, 18,741 lines) reads all active + closed picks across all scanner directories and produces:

| Output File | Description |
|-------------|-------------|
| `audit_dashboard/data/picks_now.json` | All active picks |
| `audit_dashboard/data/picks_now_live_pnl.json` | Active picks with live PnL |
| `audit_dashboard/data/summary_picks.json` | Per-class summary stats |
| `audit_dashboard/data/money_ready_verdict.json` | Per-class money-ready verdicts |
| `audit_dashboard/data/pf_registry.json` | Registry PF/WR numbers |

The dashboard at `findtorontoevents.ca/audit` reads these JSON files and displays:
- **Active Picks tab** — open positions with live PnL, TP/SL levels
- **Closed Picks tab** — historical picks with WON/LOST status, WR, PF per class

---

## Where Simulation Candidates Fit

**❌ They do NOT belong in live `active_picks.json`** — that would mix unproven simulation candidates with real scanner picks, confusing the dashboard and potentially leading to false confidence.

**✅ They belong in a segregated `simulation_candidate_picks.json`** with these flags:

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

## Data Quality Issues Identified

| Issue | Count | Impact |
|-------|-------|--------|
| `audit_trail.db` empty | 9 tables × 0 rows | No database storage of picks |
| `recent_closed.json` 0 bytes | 0 bytes | No writer for recent closed picks |
| `at_signal_outcomes` RED | ~80 days stale | Signal outcomes not updated |
| 129/129 active picks stale | ~172 days stale | Active picks not updated |
| `fetch_prices.php` HTTP 404 | Since 2026-04-29 | No price refresh |
| 8 PnL sign contradictions | 8 picks | PnL sign wrong |
| 15 PnL calculation mismatches | 15 picks | PnL calculated incorrectly |
| 53 picks frozen at pnl_pct=0% | 53 picks | PnL stuck at zero |
| `audit_trail.db` empty | 9 tables × 0 rows | No database storage |
| All 3,500 closed rows missing `resolution_method` | 3,500 rows | No resolution provenance |
| EXPIRED→WON mislabeling | Dashboard CRYPCO 78.93% vs DB raw 39.38% | False win rate inflation |
| 851 active picks with no `current_price` | 851 picks | Shows as 0% PnL, corrupts aggregates |
| 25.5% of EQUITY picks have pnl_pct=0 | 25.5% | Dilutes WR/PF |
| CRYPCO negative expectancy | 61.4% negative picks | Strategy issue, not data issue |

---

## Data Quality Issues Impacting Pick Emission

1. **Picks with `entry_price=null`** → Cannot compute PnL, should be filtered at emission
2. **Picks with `exit_price=null`** (for closed picks) → Cannot compute realized PnL
3. **Picks with `status=null`** → Cannot determine outcome
4. **Picks with `resolution_method=null`** → Cannot determine how outcome was determined
5. **Picks with `pnl_pct=null` or `pnl_pct=0`** → Cannot compute performance metrics
6. **Active picks with no `current_price`** → Cannot compute unrealized PnL

These quality issues mean that many picks in the pipeline cannot be properly evaluated, leading to unreliable performance metrics.

---

## Integration Points for New Strategies

If a new strategy is developed and validated, it should:

1. **Emit picks to `active_picks.json`** with the standard pick schema
2. **Pass through `quality_gates.py`** before emission
3. **Have `resolution_method` populated** when the pick closes
4. **Have `pnl_pct` populated** when the pick closes
5. **Be included in `closed_picks.json`** when the pick resolves

Currently, no strategy passes all 10 proof gates, so no strategy should be emitted to `active_picks.json` for real-money trading.
