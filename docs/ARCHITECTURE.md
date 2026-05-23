# System Architecture — findtorontoevents.ca/audit

## System Overview

This repository is an autonomous multi-asset-class trading prediction system. It continuously scans live market data across Crypto, Equity, Commodity, ETF, Bond, and Forex using a portfolio of 100+ quantitative strategies (momentum, carry, mean-reversion, ML-based). Each candidate pick passes through layered quality gates before being written to the audit dashboard at `findtorontoevents.ca/audit`. After picks close, an outcome resolver fetches final prices, computes realized PnL, and updates per-class performance metrics (`asset_class_health`) that drive tier-based strategy sizing decisions.

---

## Data Flow Diagram

```
Data Sources                Feature Engineering         ML Models / Strategies
(Binance, yfinance,    -->  (OHLCV, funding rate,  -->  (RF, LSTM, momentum,
 FRED, CoinGecko,           RSI, ATR, macro overlay,     carry, DNA mutations,
 Stooq, copy-trader)        sector/regime signals)       baby strategies)
        |                                                        |
        v                                                        v
  Quality Gates  <---------  Pick Generation  <---------  Score / Rank
  (passes_active_gate,       (production_scanner.py,       (elite_score,
   passes_smart_gate,         smart_picks_engine.py,        confidence,
   AUDIT_DOW_GATE,            forex_smart_picks.py,         kelly_position_sizer)
   pick_sanity)               bond_data_fred.py)
        |
        v
  Dashboard Generator  -->  audit_dashboard/data/  -->  findtorontoevents.ca/audit
  (audit_trail/              dashboard_payload.json
   dashboard_generator.py)   index.html (generated)
        |
        v
  Outcome Resolver  -->  closed_picks.json  -->  Performance Metrics
  (outcome_resolver.py)                          (asset_class_health,
                                                  profit_factor, win_rate,
                                                  MDD, n-trades)
```

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `alpha_engine/` | Core pick generation: strategies, ML models, scoring, outcome resolver, Kelly sizer, config |
| `audit_trail/` | Quality gates (`quality_gates.py`), dashboard generator, pick sanity, audit event logging |
| `audit_dashboard/` | Dashboard template (`template.html` — edit this, NOT `index.html`), generated HTML/JSON data files |
| `tools/` | Utility scripts: filter picks, mutation analysis, deploy helpers, notary, weekly picks |
| `quan_engine/` | Quantitative engine with failover cache; separate scanner contributing to system volume |
| `baby_strategies/` | Lightweight strategy bundles registered via `register_bundle.py`; lower bar to add new signals |
| `genome/` | DNA mutation lab — evolutionary strategy generation and mutation tracking |
| `copy_trader_intel/` | Copy-trader research data; scraped JSON merged into candidate pipeline |
| `cross_aggregation/` | High-conviction cross-system consensus alerts (Discord, conviction picks) |
| `shared/` | Shared utilities: `calculate_win_rate`, regime detection |
| `docs/` | All documentation (architecture, runbooks, edge analysis, strategy audits) |
| `reports/` | Generated audit reports, orphan resolver dry-runs, value screener runs |
| `tests/` | Pytest unit tests + Playwright end-to-end browser tests |
| `.github/workflows/` | 100+ GitHub Actions workflows driving autonomous scanning, deployment, and monitoring |
| `updates/` | Public-facing changelog entries (rendered on `findtorontoevents.ca`) |
| `data/` | ML gatekeeper output, shared data artifacts |
| `favcreators/` | Web/PHP integration layer for the live site |

---

## Key GitHub Actions Workflows

| Workflow file | Trigger | Purpose |
|--------------|---------|---------|
| `alpha-engine-live.yml` | Every 2 hours | Main autonomous scanner — runs `production_scanner.py`, generates picks across all asset classes, syncs to MySQL |
| `alpha-engine-daily-picks.yml` | Weekdays 22:00 UTC + Sunday 05:00 UTC | Daily equity/ETF scan using default or S&P 500 universe |
| `audit-dashboard.yml` | Hourly + push to `template.html` | Runs `dashboard_generator.py`, publishes JSON payload and regenerated `index.html` to FTP |
| `consensus-outcome-tracker.yml` | Every 30 minutes | Resolves unresolved closed picks; updates `asset_class_health` metrics |
| `sports-smoke-and-e2e.yml` | Hourly + every sports PR | Smoke tests + Playwright suite against live production sports endpoints |
| `deploy-fte-index.yml` | Push to `TORONTOEVENTS_ANTIGRAVITY/index.html` or events scrape | FTP-deploys the 4,845-line live homepage to 50webs |
| `deploy-alpha-dashboard.yml` | Push to `alpha_engine/live_dashboard.html` | FTP-deploys the live alpha engine dashboard |
| `bond-agent.yml` | Scheduled | Runs bond-specific pick generation; respects `BOND_ELITE_FLOOR` GitHub repo variable |
| `alpha-engine-fast.yml` | Scheduled / dispatch | Fast-mode scanner with `ALPHA_FAST_MODE=1` (tighter TP/SL, shorter hold) |
| `actions-failure-guardian.yml` | Scheduled | Monitors for chronic workflow failures and alerts via Discord |

---

## Asset Class Status (as of 2026-05-03)

| Asset Class | Profit Factor | Win Rate | n (trades) | Tier Status |
|-------------|--------------|----------|------------|-------------|
| EQUITY | 1.41 | 52.7% | 421 | T2 candidate — close to floor |
| COMMODITY | 1.78 | 46.9% | 750 | T2 PF met; lift WR to solidify |
| BOND | 1.72 | 55.6% | 18 | T2 PF+WR met; n below charter floor (need n>=100) |
| CRYPTO | 1.25 | 44.6% | 8,067 | Sub-T2 — `quan_engine` (18% vol, PF 0.70) + `unknown` (7%, PF 0.35) drag elite strats (PF 2.34-3.97) |
| ETF | 1.24 | 55.2% | 87 | Borderline — grow n toward 100 |
| FOREX | 0.27 | 46.4% | 1,169 | Genuinely sub-floor — mutation-before-kill protocol active (see `docs/MUTATION_THREE_AXIS_PROTOCOL.md`) |

**Tier definitions (hedge-fund grade):**
- Tier 1 (Renaissance target): PF > 2.0, WR > 55%, MDD < 10%
- Tier 2 (size-up floor): PF > 1.5, WR > 50%, MDD < 20%

Reference: `reports/hedge_fund_performance_review_*.md` and `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ALPHA_FAST_MODE` | `0` | When `1`, uses tighter TP/SL and shorter hold times (`CATEGORY_RISK_FAST` in `config.py`) |
| `AUDIT_DOW_GATE` | `0` | When `1`, enables day-of-week gate that suppresses picks on statistically worst days per class |
| `AUDIT_PICK_SANITY_GATE` | `0` | When `1`, enables strict pick sanity check (`audit_trail/pick_sanity.py`) rejecting malformed geometry |
| `BOND_ELITE_FLOOR` | `15` | GitHub repo variable — minimum elite score for bond picks to pass curation (raised/lowered to tune BOND volume) |
| `KELLY_DD_HALT_ENABLED` | `0` | When `1`, halts all sizing when 30-day rolling drawdown exceeds `KELLY_DD_HALT_MAX` |
| `KELLY_DD_HALT_MAX` | `0.30` | Drawdown threshold that triggers Kelly halt (clamped 0.01–0.95) |
| `DB_PASS` / `DB_PASS_STOCKS` / `DB_PASS_BACKTESTS` | — | MySQL credentials for audit DB and backtests DB (GitHub secrets) |
| `FRED_API_KEY` | — | FRED (Federal Reserve) API key for bond/macro data; optional for local dev |
| `MYSQL_PASS` / `AUDIT_DB_PASS` | — | Aliases accepted by `audit_sync.py` for MySQL password |

---

## Adding a New Strategy

1. **Create the strategy module** under `alpha_engine/` (e.g., `alpha_engine/my_strategy.py`) with a `generate_signals(symbol, data) -> list[dict]` interface. Each pick dict must include: `symbol`, `strategy`, `source_system`, `asset_class`, `direction`, `entry_price`, `take_profit`, `stop_loss`, `confidence`, `elite_score`.

2. **Wire it to a production caller** — the strategy must be called from at least one of: `production_scanner.py`, `smart_picks_engine.py`, `calculate_smart_score`, `passes_active_gate`, or a registered baby-strategy bundle. Unwired modules are orphans and will be rejected (Wire-Up Rule in `CLAUDE.md`).

3. **Verify it passes quality gates** — run `py_compile alpha_engine/my_strategy.py` for syntax, then check that `passes_active_gate(sample_pick)` returns True for valid signals in `audit_trail/quality_gates.py`.

4. **Add tests** — add at least one pytest test in `tests/` covering the `generate_signals` output structure (required fields, valid price geometry: TP > entry for LONG, SL < entry for LONG).

5. **Submit a PR** with the Wire-Up Rule compliance check: include `grep` output showing a production caller, or explicitly label the PR "opt-in sidecar" with a `## Wiring Plan` section naming target caller + expected PR/date.

---

## Monitoring — Where to Look When Something Breaks

| Symptom | Where to look |
|---------|--------------|
| Dashboard not updating | Check `audit-dashboard.yml` run in GH Actions; look at `audit_trail/dashboard_generator.py` logs |
| Pick volume dropping | Check `alpha-engine-live.yml` for failures; check `audit_trail/quality_gates.py` gate thresholds |
| Asset class WR/PF degrading | Check `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`; run `tools/weekly_filter_picks.py` |
| FOREX PF still below 1 | Check `docs/MUTATION_THREE_AXIS_PROTOCOL.md` for kill/mutate protocol; check `alpha_engine/data/recent_exits.json` |
| BOND picks not appearing | Check `BOND_ELITE_FLOOR` GitHub repo variable (default 15); check `alpha_engine/bond_data_fred.py` |
| ML model drifting | Check `alpha_engine/data/ml_health_status.json`; run `alpha_engine/ml_health_monitor.py` |
| Outcome resolver stuck | Check `resolver.log` and `reports/orphan_resolver_dryrun_*/`; run `alpha_engine/outcome_resolver.py` manually |
| Sports endpoint down | Check `sports-smoke-and-e2e.yml` hourly run; read `tools/deploy_sports_files.sh` instructions |
| Live site broken | Check `deploy-fte-index.yml`; NEVER replace with Next.js build output (see `CLAUDE.md` critical file rules) |
| CI coverage below threshold | Requires `--cov-fail-under=40` (A15.2 gate); add tests before merging |
