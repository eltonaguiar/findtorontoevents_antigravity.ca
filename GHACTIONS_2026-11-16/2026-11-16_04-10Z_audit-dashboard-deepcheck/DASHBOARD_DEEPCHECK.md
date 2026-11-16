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

## C. Prediction-market & WIRED feeding (verified via subagent SA2)
**2 PM feeds genuinely reach `/audit`; 3 are dead/gitignored:**
| Registered source | File | On main? | Feeds /audit? |
|---|---|---|---|
| `polymarket_signals` | `copy_trader_intel/data/polymarket_picks.json` | ✅ 7,082B (committed) | **YES** (polymarket-signals.yml `2,32 * * * *`) |
| `prediction_market_consensus` | `alpha_engine/data/prediction_market_picks.json` (+ fallback consensus) | ✅ 6,203B (committed) | **YES** — live `pick_summary_stats_48h.json` shows `strategy:"prediction_market_consensus"` rows in `by_class.CRYPTO` |
| `pm_momentum_signals` | `prediction_market_agents/data/momentum_signals.json` | ❌ | **NO — dead by design** (in `_GHOST_SYSTEMS`, skipped) |
| `pm_whale_signals` | `prediction_market_agents/data/whale_signals.json` | ❌ (gitignored) | **Ephemeral** — produced only inside the `audit-dashboard` job's local workspace; never committed |
| `pm_kalshi_signals` | `prediction_market_agents/data/kalshi_signals.json` | ❌ (gitignored) | **Ephemeral** — same |

**Why whale/kalshi never persist:** `.gitignore:328` ignores `**/data/*_signals.json`; commit steps use
`git add` without `-f` + `2>/dev/null || true` → silent skip. They exist only during the audit-dashboard
run that regenerates them (`audit-dashboard.yml:129`), so they contribute **only on that job**, nothing
persisted between runs.

**Classification gotcha (important):** there is **no PREDICTION asset class**. PM picks carry
`category:"crypto"` + USDT symbols → `_derive_asset_class` files them under **CRYPTO**. They are shown
with a **"🔮 PM" badge** (`template.html:9191-9198`) but counted in the CRYPTO tile/WR/PF. So "are PMs
feeding the dashboard?" = **yes, but invisibly inside CRYPTO**, not as a distinct class.

**Data-integrity concern:** `_snapshot_prediction_market_entry` (`dashboard_generator.py:5493-5524`)
backfills `entry_price` from the **spot** quote and derives TP/SL (`_derive_prediction_market_trade_levels`)
for signal-only PM rows — i.e. a prediction-market contract is priced/TP-SL'd as if it were a spot crypto
trade. This can distort PM pick PnL realism.

**WIRED_IN:** origin/main has **24** top-level dirs; **only `wired_in_childlike` is wired**
(`dashboard_generator.py:4288-4292`, resolver `:265`, paper-only flagged). The other **23 are unwired**
(no `JSON_PICK_SOURCES`/`SYSTEM_SOURCES` entry, no code globs `WIRED_IN`) — including the per-stamp
childlike folders (0230Z/0653Z/0700Z/0703Z/0709Z/final_v001) and all scratch/flaxen-hair/buffy/inspect-wt
dirs. Only the single consolidated `audit_dashboard/data/wired_in_childlike_*.json` is consumed.

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
4. **Prediction markets**: 2 feeds work (polymarket + consensus→CRYPTO). Decide fate of `pm_whale`/`pm_kalshi`
   (either commit them by negating `.gitignore` for those two files, or remove the ephemeral registrations) and
   fix PM spot-pricing (`_snapshot_prediction_market_entry`) so prediction contracts aren't TP/SL'd as spot crypto.
5. **WIRED_IN**: 23 of 24 dirs are unwired — either register the intended ones or archive the rest.
6. **db_health.json**: fix duplicate-key emit.


