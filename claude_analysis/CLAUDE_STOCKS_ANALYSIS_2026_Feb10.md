# CLAUDE_STOCKS_ANALYSIS_2026_Feb10

> **Author:** Claude (AI)
> **Date:** 2026-02-10
> **System:** GOLDMINE_CURSOR
> **Purpose:** Full audit of AntiGravity prediction suite + strategy to determine what works

---

## Executive Summary

The AntiGravity prediction suite runs **30+ prediction pages** powered by **50+ algorithms**,
**31 GitHub Actions workflows**, and **40+ PHP API endpoints** across stocks, penny stocks,
crypto, meme coins, forex, mutual funds, sports betting, and ETFs.

The system already has strong foundations (walk-forward validation, purged CV, paper trading,
self-learning). What was missing is a **unified cross-system view** that answers: *"Is any of
this actually working?"*

**GOLDMINE_CURSOR** was built to answer that question.

---

## Deliverables Created

### Main Dashboard
- **`goldmine_cursor/index.html`** — GOLDMINE_CURSOR main dashboard
  - Overview tab: Total stats, equity curve, asset breakdown
  - Track Record tab: Paginated, filterable prediction ledger (INSERT-only proof)
  - Weekly Scorecard tab: Algorithm rankings by profit factor with verdicts
  - Mission Control tab: Data health monitor, circuit breakers, admin actions
  - Hidden Winners tab: Algorithms flagged as outperformers
  - Regime Analysis tab: Performance segmented by bull/bear/sideways/high_vol

### API Endpoints
- **`goldmine_cursor/api/setup_tables.php`** — Creates all 7 `goldmine_cursor_*` tables
- **`goldmine_cursor/api/track_record.php`** — Public read-only API (summary, predictions, equity curve, rankings, etc.)
- **`goldmine_cursor/api/harvest.php`** — Pulls predictions from all source systems into unified ledger
- **`goldmine_cursor/api/weekly_scorecard.php`** — Computes per-algorithm performance + verdicts
- **`goldmine_cursor/api/health_check.php`** — Data freshness monitor + circuit breaker events
- **`goldmine_cursor/api/db_connect.php`** — Database connection (shared stocks DB)
- **`goldmine_cursor/api/db_config.php`** — Database credentials

### Analysis Tools (Python)
- **`claude_analysis/tools/deflated_sharpe.py`** — Deflated Sharpe Ratio calculator (adjusts for multiple testing)
- **`claude_analysis/tools/regime_tagger.py`** — Market regime classifier (bull/bear/sideways/high_vol)
- **`claude_analysis/tools/algo_correlation.py`** — Algorithm independence/correlation matrix

### Documentation
- **`claude_analysis/DEAD_DATA_FIXES.md`** — Complete dead data audit with exact patches
- **`claude_analysis/CLAUDE_STOCKS_ANALYSIS_2026_Feb10.md`** — This file

---

## Database Tables Created (goldmine_cursor_*)

| Table | Purpose |
|-------|---------|
| `goldmine_cursor_predictions` | Master prediction ledger (INSERT-only for new entries) |
| `goldmine_cursor_algo_scorecard` | Weekly algorithm performance snapshots |
| `goldmine_cursor_benchmarks` | Daily benchmark prices (SPY, BTC, EURUSD, VFINX) |
| `goldmine_cursor_regime_log` | Market regime detection history |
| `goldmine_cursor_correlation_matrix` | Algorithm independence measurements |
| `goldmine_cursor_circuit_breaker` | Max drawdown circuit breaker events |
| `goldmine_cursor_data_health` | Data freshness monitoring log |

---

## Dead Data Issues Found

| Issue | Severity | Details |
|-------|----------|---------|
| miracle2_data.json all pending | HIGH | 50 picks, 0 resolved. Resolution pipeline may be broken. |
| Stats page hardcoded dates | MEDIUM | 3 stats pages check `>= '2025-01-01'` — should be dynamic |
| Edge history price = 0 | MEDIUM | Weekend picks have no market data. Self-heals on weekdays. |
| Copyright 2024 | LOW | MOVIESHOWS2/index.html still says 2024 |

See `claude_analysis/DEAD_DATA_FIXES.md` for exact patches.

---

## Pro Algo Trading Standards — What We Need

### What the pros do that we now support:
1. **Timestamped immutable audit trail** — `goldmine_cursor_predictions` is INSERT-only
2. **Benchmark comparison** — `benchmark_return_pct` field on every prediction
3. **Algorithm ranking by profit factor** — Weekly Scorecard with auto-verdicts
4. **Hidden winner detection** — Auto-flagged when WR > 55% AND PF > 1.5
5. **Circuit breaker** — Auto-triggered at 15% drawdown
6. **Market regime tagging** — `market_regime` field on every prediction
7. **Deflated Sharpe Ratio** — Python tool to adjust for multiple testing
8. **Data health monitoring** — Real-time freshness checks across all systems

### Still needed (future work):
- CPCV (Combinatorial Purged Cross-Validation) extension
- Live benchmark price ingestion (SPY, BTC daily close)
- Email/push digest of weekly scorecard
- GitHub Actions workflow to auto-run harvest + scorecard daily

---

## How to Deploy

1. Deploy `goldmine_cursor/` directory to FTP
2. Call setup: `https://findtorontoevents.ca/goldmine_cursor/api/setup_tables.php?key=goldmine2026`
3. Run first harvest: `https://findtorontoevents.ca/goldmine_cursor/api/harvest.php?key=goldmine2026`
4. Build scorecard: `https://findtorontoevents.ca/goldmine_cursor/api/weekly_scorecard.php?key=goldmine2026`
5. View dashboard: `https://findtorontoevents.ca/goldmine_cursor/`

---

## Navigation

Added to main site under: **Investment Hub → Goldmines → Claude → GOLDMINE_CURSOR Dashboard**
