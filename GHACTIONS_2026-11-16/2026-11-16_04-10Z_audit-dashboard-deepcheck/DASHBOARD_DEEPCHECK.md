# /audit dashboard deep-check — 2026-11-16 (~04:07Z)

Scope: active/closed/per-class picks, WIRED_IN + prediction-market (Kalshi/Polymarket)/hypothesis
feeding, JS/data errors, info-box stale states. Read-only audit + 2 subagent passes.

## A. Data contradiction on the page (highest priority) — CONFIRMED
| Where | Says | Source | Freshness |
|---|---|---|---|
| DB Health card | Ghost Rows **22,947**, PnL mismatch **130/24,158** | `db_health.json::checks.ghost_rows` | **FRESH** — `generated_at 2026-11-16T02:47:34Z` |
| TRUTH LAYER note | "Ghost rows: **0** (was 22,947). Status-PnL mismatches: **0**." | **hardcoded** `template.html:857` (also :911), dated "DATA QUALITY IMPROVEMENTS (2026-05-31)" | **STATIC / STALE** |

→ The DB Health card is **correct and current** (22,947 ghosts, 130 sign-mismatches). The **stale artifact
is the hardcoded truth note** from 2026-05-31, which now contradicts the live DB. Fix: make the note
data-driven from `db_health.json` (or delete the false "Ghost rows: 0" claim).
*(Nuance: "Status-PnL mismatches: 0" aligns with `won_pnl_contradiction.contradiction_detected=false`; the
PnL-Integrity `sign_mismatch:130` is a different metric — but the ghost-rows 0-vs-22,947 is a flat contradiction.)*

## B. Broken / missing / stale boxes
| Box | Displayed | Source | Verdict |
|---|---|---|---|
| **Money Ready Verdict** | "No data available / unknown" | `data/money_ready_verdict.json` | **FRONTEND BUG** — file is fresh (`generated_at 2026-11-16T03:02:14Z`) and schema matches; "no-data" only renders when `r.timestamp` is falsy, which it isn't. Path/schema are fine → render/fetch logic bug. |
| **Strategy IC Analysis** | "Failed to load IC analysis data" | `./data/strategy_ic_analysis.json` | **BROKEN+STALE**: repo file **absent**; builder removed 2026-06-12 (`pick-funnel-nightly.yml:73-85`); live URL still serves a **2026-05-29 (171 d old)** orphan. |
| **Strategy Kill Tribunal** | "generated 2026-05-05" | `strategy_tribunal_latest.json` **MISSING** → falls back to stale `asset_class_health` | STALE fallback |
| **Swarm Paper Picks** | "Jun 6, 2026 · 162 d" | `swarm_picks.json` | **DEAD by design** — pipeline decommissioned 2026-06-12; repo has only `swarm_*_OLD.json`; no live file. Box should be hidden. |
| regime report | (fetch) | `regime_report.json` **MISSING** | fetch fails silently |
| AI Leaderboard | 18h45m | `ai_leaderboard_index.json` | **FRESH** (daily cron, fails only >36h) — *not* stale |
| Edge Stability | 3h10m | `edge_stability_index.json` | FRESH |
| Forward Validator Freshness | 0h, last WON/LOST 02:26:30 | `db_health.json::open_bloat` | FRESH (`validator_frozen=false`) |
| `db_freshness.json` | — | not referenced by any page JS | **ORPHAN** (2026-05-23, RED) — dead file |

## C. Prediction-market feeding gap
`dashboard_generator.py` registers PM sources but data files are **absent on main**:
`prediction_market_agents/data/{momentum,whale,kalshi}_signals.json` = **MISSING** → 3 registrations are
**silent no-ops**. `copy_trader_intel/data/polymarket_picks.json` present (7KB);
`wired_in_childlike_{active,closed}.json` present (active 4.6KB / closed 106B≈empty).
*(Producer-workflow + classification detail: subagent SA2 — pending merge.)*

## D. By-design — do NOT "fix"
- **"20 of 4209 active · 0 proven / 4189 gated out"** — trust-tier gating (proven = ≥30 trades & ≥45% WR). Honest; matches 0/9 money-ready.
- 0/9 money-ready, ML-calibration-inverted, commodity survivor gap — accurate disclosures.
- AI Leaderboard 18h, Edge Stability 3h — within cadence.
- Swarm Paper Picks aging — dead pipeline (box should be hidden, not "fixed").

## E. Data-quality defect in emitted file
`audit_dashboard/data/db_health.json` contains **duplicate top-level JSON keys** (`won_pnl_contradiction`,
`pnl_integrity`, `status_standardization` each twice). Parsers keep the last; values near-identical, but it's
a malformed-emit defect in the DB-health generator worth fixing at source.

## F. Frontend fragility
Live PnL depends on many external APIs (coingecko, bybit, cryptocompare, twelvedata, **financialmodelingprep
& alphavantage demo keys**) + the **`allorigins.win` CORS proxy** + raw.githubusercontent. Any rate-limit/outage
silently degrades "Active PnL (Live)" and price tiles.

## G. Key data facts
- `dashboard_data.json` >5 MB, **not committed** — regenerated nightly by `pick-funnel-nightly.yml` (downloads from live). "Dashboard Data 1h0m" box is fresh.
- `audit_surface_truth.json` `generated_at 2026-11-15T04:52:54Z` (~23h) — the per-class truth tile; `money_ready_count 0`.
- `money_ready_verdict.json` fresh (03:02Z) — 10 classes present.

## Recommended fixes (priority)
1. **Truth-layer note** (`template.html:857`): drive from `db_health.json` or delete the false "Ghost rows: 0" — *misleads on data integrity*.
2. **Money-Ready box**: fix the no-data render path (file is good).
3. **Hide dead boxes** (Swarm Paper Picks) and either restore or hide **Strategy IC Analysis** + **regime report**.
4. **Prediction-market**: produce/commit the 3 missing `prediction_market_agents` signal files, or remove the dead registrations.
5. **db_health.json**: fix duplicate-key emit.

*(Section C SA2 detail appended when the prediction-market/WIRED subagent returns.)*
