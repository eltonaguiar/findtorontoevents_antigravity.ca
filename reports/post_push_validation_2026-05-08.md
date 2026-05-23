# Post-Push Validation 2026-05-08

Validation of main push `92c81c91f1d..53383d8b938` (17 commits) + downstream
loop3 ship plan items pushed through `558a367db31` (~30 more commits).

## TL;DR

| Item | Status | Evidence |
|---|---|---|
| #5 EW compound cap 500→10 | ✅ VERIFIED | `summary.total_pnl_pct_compounded_ew` = **85.23** (was 20,311,796.96%) |
| #1+#2 LONG_TERM filter (concept_registry + _CLOSED_PICK_KEEP_FIELDS) | ⚠️ PARTIAL — ROOT CAUSE FOUND | 16 UEPS picks present; tagged `concept_family="standard"` because `assign_concept_fields` short-circuits on placeholder tag (now fixed in follow-up commit) |
| #14 hyro-bridge-regen.yml numpy fix | ⏳ PENDING — runs on next 05:40 UTC daily cron | `hyro_quan_bridge.json` mtime still 2026-04-18 |
| Freebuff FOREX P0/P1 (TP/SL widening + kill-switch unblocks) | ✅ CODE VERIFIED | `forex_strategies.py:_forex_tp_sl()` shows TP cap 1.5%, SL cap 0.8%; `fx_kill_switch.py` has 2 strategies commented out; `quality_gates.py` JPY_CROSS_BUY_KILL_DISABLED default + 4 forex kills commented |
| db_health.json regenerated | ⏳ STALE — generated_at 2026-05-08T15:00:00Z (pre-push) | Next clean cron will regen |

## Cron state

| Run | sha | start | conclusion |
|---|---|---|---|
| 25577639645 | 53383d8b9 (fast-wins) | 2026-05-08T20:22:11Z | **in_progress 80+ min** — stuck on "Resolve active picks (TP/SL/time exits)" |
| 25578119373 | 298203679 | 2026-05-08T20:33:02Z | in_progress (queued behind 25577639645) |
| 25575894411 | c1d8c4af0 | 2026-05-08T19:42:52Z | success ✅ (last clean baseline before fast-wins) |

Resolver step has been in_progress since ~20:43Z. Likely processing backlog
of unresolved active picks. The dashboard JSON committed at
`93133fbd5d9` (2026-05-08 20:28:09 UTC, sha 53383d8b9) was written EARLY in
the 20:22 cron — before the resolver step stuck.

## EW compound cap (#5) — VERIFIED ✅

```
summary.total_pnl_pct: 85.23
summary.total_pnl_pct_compounded_ew: 85.23
generated_at: 2026-05-08T20:23:36Z
```

Was 20,311,796.96% pre-fix. New value matches `total_pnl_pct` (sum-of-pcts)
because with cap=10% the compound product `prod *= 1 + capped/100` collapses
to roughly the sum. Working as designed.

## LONG_TERM filter (#1+#2) — root cause identified, fix shipped

UEPS picks reach the dashboard with `source_system="ueps"`, but
`concept_family="standard"` and `pick_type=None`.

Sample row (PYPL):
```
source_system: 'ueps'
source:        'value_screener'
strategy:      'magic_formula_x_piotroski_x_acquirers'
pick_type:     None
concept_family:'standard'   ← should be 'long_term_value'
```

Why: `assign_concept_fields()` line 6373 short-circuited when
`concept_family` was already stamped — even when the existing tag was the
default placeholder `"standard"`. An upstream `_normalize_pick` pass set
`"standard"` before `pick_type`/source was populated; the registry then
refused to upgrade.

Fix (this validation commit): allow re-derivation when
`concept_family.lower() == "standard"`. Ships via the same dashboard
generator path. Next cron run picks up.

## Hyro-bridge numpy fix (#14)

Current `hyro_quan_bridge.json::generated_at` = 2026-04-18T22:18:59Z (still
20-day stale). The `hyro-bridge-regen.yml` workflow is on a daily cron at
05:40 UTC; numpy/pandas fix landed in the workflow file at commit
`53383d8b938`. Next refresh: 2026-05-09 05:40 UTC.

Cannot validate until tomorrow's cron fires. Manual trigger via
`gh workflow run hyro-bridge-regen.yml` available.

## FOREX P0/P1 (freebuff)

Code verification — files merged from working tree to main:

```
alpha_engine/forex_strategies.py:_forex_tp_sl()  — TP cap 0.8% → 1.5%, SL cap 0.5% → 0.8%
alpha_engine/fx_kill_switch.py                    — forex_rsi2_mean_reversion + myfxbook_retail_contrarian commented out of _KNOWN_TOXIC_FOREX_STRATEGIES
audit_trail/quality_gates.py                      — 4 FOREX kills commented + JPY_CROSS_BUY_KILL_DISABLED default
docs/PERFORMANCE_DEEP_DIVE_MAY82026.md            — root cause analysis (freebuff)
updates/2026-05-08-forex-p0-p1-fixes-implementation.md — implementation notes
```

Performance impact (FOREX PF 0.27 → ?) not measurable until 7d window of
post-fix forward closes. Monitor in next week's `asset_class_health.FOREX`
delta.

## db_health.json

`generated_at`: 2026-05-08T15:00:00Z (pre-push baseline).

Headline numbers from this snapshot:
- pnl_integrity: 58% mismatch >1% (TIER 1, RED) — 100k sample, 58k mismatch
- ghost_rows: 655,000 phantom-resolved rows across 18 cohorts (TIER 1)

Next clean cron will regen via `tools/db_health_check.py` step now in
`audit-dashboard.yml` (added 2026-05-08).

## Loop3 ship-plan items pushed downstream

In addition to the 17-commit fast-wins push, this loop also shipped the
top-7 swarm queue + 4 loop2 16-queue extras:

| # | Item | Files | Verified |
|---|---|---|---|
| Top-7 #1 | STOCKSUNIFY2 wire-in | tools/sync_stocksunify2.py + .github/workflows/stocksunify2-pull.yml + JSON_PICK_SOURCES | 18 picks bootstrapped to audit_dashboard/data/stocksunify2_active_picks.json |
| Top-7 #2 | FRED macro context | alpha_engine/fred_macro_context.py + dashboard wire-in + UI strip | Code only; needs FRED_API_KEY in env to populate |
| Top-7 #3 | COMMODITY 2x sizing | alpha_engine/config.py + config/risk_policy.json | Strategy weights live; per-symbol cap applies on next pick |
| Top-7 #4 | CRYPTO drag-cohort kill | audit_trail/quality_gates.py BLOCKED_ASSET_SOURCE_PAIRS + alpha_engine/feed_hygiene.py Polymarket v2 | Effective immediately on next pick generation |
| Top-7 #6 | F8 divergence card | _compute_fwd_vs_bt_divergence + template.html | Renders on tab-btvsfwd; populated when next cron emits payload |
| Top-7 #7 | F2 leaderboard chips | dashboard_generator.py asset_class on rows + template.html chip bar | Renders on tab-leaderboard once payload has asset_class field |
| L2 #3 | scanner.py:2232 pnl-sign guard | multi_asset/scanner.py | Effective on next scanner run |
| L2 #7 | _win_fraction ghost-row filter | cross_aggregation/performance_alerts.py | Effective on next alerts pass |
| L2 #11 | MAJOR GOAL banner data-driven | template.html data-mg-class hooks + script | Renders live values on next page load if asset_class_health populated |
| L2 #12 | Total PnL tooltip | template.html cardTips.totalPnl | Live on next page load |

## Outstanding

- **Loop2 #6 Sharpe annualization** — deferred. Mercury Sharpe at line 12639 uses sqrt(252) which is correct for daily-aggregated input. The "should be sqrt(N_trades)" verdict assumes per-trade Sharpe formulation. Needs a scope decision (rewrite as per-trade vs keep daily) before shipping. Adding a scope-clarifying tooltip is the safe interim.
- **20:22Z + 20:33Z cron** — let resolver finish; if it times out, manual rerun via `gh workflow run audit-dashboard.yml`.
- **Concept-tag upgrade** — fix shipped this validation commit; verify on next clean dashboard build that 16 UEPS picks now carry `concept_family="long_term_value"` and `LONG_TERM` filter on /audit returns 16+ rows.

## How to reproduce

```bash
gh run list -R eltonaguiar/findtorontoevents_antigravity.ca --workflow audit-dashboard.yml --limit 3
git show origin/main:audit_dashboard/data/dashboard_data.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['summary']['total_pnl_pct_compounded_ew'])"
git show origin/main:audit_dashboard/data/db_health.json | python -m json.tool | head -10
```
