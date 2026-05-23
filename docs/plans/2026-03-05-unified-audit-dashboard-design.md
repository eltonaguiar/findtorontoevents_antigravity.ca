# Unified Audit Dashboard — Design Document

**Date:** 2026-03-05
**Status:** Approved
**Approach:** Static JSON generator + HTML/JS frontend (GitHub Pages + FTP)

## Purpose

A single "birds-eye view" dashboard showing ALL picks, trades, portfolios, and system performance across every subsystem. Replaces the need to check 30+ separate data sources.

## Architecture

```
audit_trail/dashboard_generator.py  →  audit_trail/data/dashboard_payload.json
                                           ↓
                              audit_dashboard/index.html  (reads JSON, renders UI)
                                           ↓
                              GitHub Pages + FTP deploy
```

**Generator runs via GitHub Actions** every 15 min, reads all data sources, writes a single JSON payload. Static HTML/JS frontend consumes it.

## Data Sources (Complete Inventory)

### Primary JSON Pick Files (75 non-empty across 30+ systems)

| System | Active Picks | Closed Picks | Key File |
|--------|-------------|--------------|----------|
| Alpha Engine | 30 | 168 (+2,776 rigorous) | `alpha_engine/data/` |
| KIMI Rise of the Claw | 5 | 0 (in SQLite) | `KIMI_RISEOFTHECLAW/data/` |
| ML Battleground (6 systems) | 10 (system_f) | ~84 total | `ml_battleground/system_*/data/` |
| Battleground | 0 | 162 | `battleground/data/` |
| Mercury2 | 2 | 46 | `mercury2/data/` |
| Paper Trading | 55 | 15 | `paper_trading/data/` |
| Breakout Arena (3 approaches) | 7 | 3 | `breakout_arena/approach_*/data/` |
| ML Crypto Predictor | 0 | 289 (log) | `ml_crypto_predictor/enhanced_models/live_picks/` |
| Crypto ML Edge | multi | multi | `crypto_ml_edge/data/` |
| Coinglass Strategies | 3 | 0 | `coinglass_strategies/data/` |
| STOCKS Competition | 51 | 0 | `STOCKS/competition/` |
| Claude Gainer ML | 3 | 29 | `claude_gainer_ml/tracker/` |
| RL Agent | 3 | 0 | `rl_agent/data/` |
| Genome/DNA | 0 | 0 | `genome/active_picks.json` |
| Signal Aggregator | 5 | 0 | `signal_aggregator/data/` |
| Crypto Signal Engine | 0 | 2 | `crypto_signal_engine/data/` |

### SQLite Databases (16 with actual data)

| Database | Key Tables | Records |
|----------|-----------|---------|
| `data/audit_trail.db` | raw_picks, consensus_picks, audit_events | 4,050 + 43 |
| `KIMI_RISEOFTHECLAW/data/kimi_trading.db` | picks, signals | 133 + 379,995 |
| `data/live_picks.db` | live_picks, pick_history | 105 + 5,073 |
| `paper_trading/data/paper.db` | portfolios, positions | 12 + 70 |
| `sandbox/data/opposite_day.db` | opposite_picks | 225 |
| `coinglass_strategies/data/coinglass.db` | signals, positions | 270 + 5 |
| `signal_recorder/data/signal_log.db` | signals, outcomes | 151 + 82 |
| `KIMI_RISEOFTHECLAW/data/signal_tracker.db` | tracked_signals | 1,038 |
| `predictions/data/predictions.db` | predictions | 367 |
| `incubator/forward_test.db` | forward_signals, forward_summaries | 12 + 81 |
| `genome/strategy_registry.db` | live_signals | 27 |

### Portfolios

| Source | Portfolios | Type |
|--------|-----------|------|
| `paper_trading/data/portfolios.json` | 12 | Paper portfolios with equity/PnL/WR |
| `KIMI_RISEOFTHECLAW/data/portfolio_state.json` | 8 algorithms | Algorithm portfolios |
| `KIMI_RISEOFTHECLAW/data/paper_portfolio.json` | 1 | Paper portfolio |
| `portfolio_tracker/data/portfolio_metrics.json` | 1 | System-wide metrics |
| `asterdex_paper/data/portfolio_state.json` | 1 | Asterdex paper |
| `paper_trading/data/paper.db` (SQLite) | 12 | DB-backed portfolios |

### Duplicate/Mirror Files (Skip in Generator)

- `riseoftheclaw/data/*` = mirror of `KIMI_RISEOFTHECLAW/data/*`
- `deploy_riseoftheclaw/` = stale deploy artifact
- `updates/data/claude_ml_*` = mirror of `claude_gainer_ml/tracker/*`
- `updates/data/cursor_ml_*` = mirror of `crypto_gainer_ml/tracker/*`

## Dashboard JSON Payload Schema

```json
{
  "generated_at": "ISO timestamp",
  "summary": {
    "total_systems": 15,
    "total_active_picks": 180,
    "total_closed_picks": 3600,
    "overall_win_rate": 52.3,
    "total_portfolios": 22,
    "total_pnl_pct": 15.8
  },
  "systems": [
    {
      "name": "alpha_engine",
      "label": "Alpha Engine",
      "active_picks": 30,
      "closed_picks": 168,
      "win_rate": 54.2,
      "avg_pnl_pct": 1.8,
      "sharpe": 1.2,
      "asset_classes": ["CRYPTO", "FOREX", "EQUITY"],
      "last_signal_at": "ISO",
      "status": "active"
    }
  ],
  "picks": {
    "active": [ /* all active picks across systems */ ],
    "recent_closed": [ /* last 200 closed picks */ ]
  },
  "portfolios": [
    {
      "name": "Conservative Tier",
      "source": "paper_trading",
      "equity": 10450,
      "pnl_pct": 4.5,
      "win_rate": 58.0,
      "positions": 8,
      "max_drawdown": -3.2
    }
  ],
  "performance": {
    "by_asset_class": { "CRYPTO": {...}, "FOREX": {...}, "EQUITY": {...} },
    "by_strategy": [ /* top/bottom strategies */ ],
    "daily_pnl": [ /* last 30 days */ ]
  },
  "backtest_vs_forward": {
    "strategies": [
      { "name": "...", "bt_wr": 65, "fwd_wr": 52, "decay": -13, "bt_trades": 100, "fwd_trades": 20 }
    ]
  },
  "bundles": [ /* from baby_strats_dashboard.json */ ],
  "audit_events": [ /* last 50 audit events */ ]
}
```

## Frontend Sections

1. **Summary Cards** — total active/closed picks, overall WR, PnL, system count
2. **System Status Grid** — each system as a card with health indicators
3. **Active Picks Table** — filterable by system, asset class, direction, confidence
4. **Closed Picks Table** — sortable by PnL, with date range filter
5. **Portfolio Overview** — all paper portfolios with equity curves
6. **Performance Charts** — WR by system, PnL over time, asset class breakdown
7. **Backtest vs Forward** — decay analysis table
8. **Bundle Babies** — current bundles with confidence labels
9. **Audit Log** — recent filter/event log entries

### Filters

- Asset class: CRYPTO / FOREX / EQUITY / ALL
- System: dropdown of all systems
- Status: ACTIVE / CLOSED / ALL
- Direction: LONG / SHORT / ALL
- Date range picker
- Confidence: forward-confirmed / mixed / backtest-projected
- Search by symbol

## Generator Implementation

`audit_trail/dashboard_generator.py`:
1. Read all JSON pick files (skip mirrors/dupes)
2. Read key SQLite databases (audit_trail.db, paper.db, kimi_trading.db)
3. Read portfolio JSONs
4. Compute aggregate stats
5. Write `audit_trail/data/dashboard_payload.json`

## Deployment

- **GitHub Actions:** New workflow `audit-dashboard.yml` runs every 15 min
- **GitHub Pages:** Auto-deployed via existing Pages workflow
- **FTP:** Add to existing deploy workflows for findtorontoevents.ca + torontoevent.net
- **URL:** `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/`

## Gap Analysis: What's Missing from Audit DB

The current `audit_trail.db` has 4,050 raw_picks but the JSON files show ~3,600+ closed picks across systems. Key gaps to verify:
- ML Battleground system_f (500 history picks) — may not be in audit DB
- Quant Lab combo trades (24,975) — likely NOT in audit DB (too large, backtest data)
- ML Crypto Predictor (289 logged picks) — check if backfilled
- STOCKS competition (51 forward picks) — check if backfilled
- Paper trading positions — check if tracked in audit DB

The `backfill.py` script already handles most sources. We should run it once after generator is built to ensure completeness.
