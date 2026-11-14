# GitHub Actions Fixes (final_v3, 2026-11-14)

**Scope:** All `.github/workflows/*.yml` related to financial predictions  
**Current state:** 365 workflows (361 active, 4 disabled); 30 failures, 11 cancelled, 20 never-run; `audit-dashboard.yml` itself was in_progress at snapshot

---

## Critical Path Workflows (must be green)

| Workflow | Status Today | Fix Required | Priority |
|---|---|---|---|
| `CI Tests` | failure (push, main) | Fix failing tests; add per-class cost gate, multiple-testing, PBO/SPA gates | P0 |
| `audit-hourly-update.yml` | success | Verify it populates `after_cost_net_per_trade` (fixed today in `dashboard_generator.py`) | P0 |
| `db-freshness-guardian.yml` | success | Verify `at_signal_outcomes` becomes GREEN (<360 min stale) | P0 |
| `Daily Price Refresh` | failure | `fetch_prices.php` HTTP 404 since 2026-04-29 | P0 |
| `Daily Prices yfinance Refresh` | failure | yfinance replacement also failing | P0 |
| `Pick Monitor & Price Validator (30min)` | success | Verify it reads fixed resolver output | P0 |
| `outcome-resolver.yml` | cancelled | Resolve why cancelled; ensure it runs hourly | P0 |
| `ALPHA ENGINE - Live Autonomous Scanner` | failure | Fix scanner; it emits picks without cost validation | P0 |
| `Autonomous Trading Bot` | failure | Fix; it trades without cost validation | P0 |
| `Live Trading Bot` / Canada variants | failure | Fix; trades without cost validation | P0 |
| `DNA Strategy Pipeline` | failure | Fix pipeline | P1 |
| `Forward Test - Strategy Validation` | failure | Fix forward test validation | P1 |
| `picks_dispatch` | failure | Fix dispatch | P1 |

---

## New CI Gates to Add

| Gate | Workflow | Trigger | Failure Mode | Priority |
|---|---|---|---|---|
| G1 Summary population | `ci-tests.yml` + `audit-dashboard.yml` | Every PR + hourly build | Hard fail | P0 |
| G2 Quote honesty | `audit-dashboard.yml` (post-generator) | Hourly build | Hard fail | P0 |
| G3 Metric liveness | `audit-dashboard.yml` (post-generator) | Hourly build | Hard fail | P0 |
| G4 Dedup/identity | `audit-dashboard.yml` (pre-deploy) | Hourly build | Hard fail | P0 |
| G5 Sidecar freshness | `audit-dashboard.yml` + deploy | Hourly build | Hide panel / hard fail | P0 |
| G6 Strict JSON | `audit-dashboard.yml` (pre-deploy) | Hourly build | Hard fail | P0 |
| G7 Workflow hygiene lint | `ci-tests.yml` | Every PR | Hard fail | P1 |
| G8 Scheduler guard | `ci-tests.yml` (static) | Every PR | Hard fail | P1 |
| G9 DB freshness | `db-freshness-guardian.yml` | Hourly | Hard fail (already exists) | P0 |
| G10 Open-pick backlog | `db-freshness-guardian.yml` | Hourly | Hard fail | P1 |
| G11 Source authenticity | Nightly | Hard fail | P1 |
| G12 Push contention | `ci-tests.yml` static + run audit | PR + nightly | Warn | P1 |
| G13 Secret scan | `db-password-leak-guard.yml` | Push/PR | Hard fail | P0 |

**Principle:** Gates that protect published truth (WR, PnL, quote honesty) fail hard. Gates that protect freshness fail hard for hourly pipeline, `--warn-only` for weekly/monthly. Gates must be <60s and deterministic; no live network for contract suite. Never re-enable `push:` trigger on `audit-dashboard.yml`.

---

## Workflow Hygiene

| # | Action | Priority |
|---|---|---|
| GA-9a | Disable or fix 30 failing workflows | P1 |
| GA-9b | Resolve 11 cancelled workflows | P1 |
| GA-9c | Schedule or remove 20 never-run workflows | P1 |
| GA-10 | Add stale-workflow audit: no active workflow >30 days since last success | P1 |
| GA-11 | Remove `[skip ci]` from non-doc commits on critical path | P1 |

---
