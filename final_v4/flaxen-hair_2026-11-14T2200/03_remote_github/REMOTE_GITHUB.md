# Remote GitHub Review

**Worktree:** flaxen-hair_2026-11-14T2200 | **Scope:** remote GitHub financial files and workflow state

## Remote GitHub State

**Origin/main ahead by 5 commits:**

| Commit | Subject | Time | Type |
|--------|---------|------|------|
| ea7a4c6ed13 | Alpha Engine FAST: 2026-11-14 21:50 [AUTO] [skip ci] | 21:50 | Auto |
| 5679f88d0d3 | Sustained Gainer scan: 2026-11-14 21:48 [AUTO] [skip ci] | 21:48 | Auto |
| fc8f961811d | Auto-update prediction quality metrics 2026-11-14 21:48 UTC [skip ci] | 21:48 | Auto |
| e1db9f5881b | Dashboard pick trader: 2026-11-14 21:47 UTC [skip ci] | 21:47 | Auto |
| 489ec2ae9cd | chore: mega mutation tracker hourly update [skip ci] | — | Auto |

All 5 commits are automated updates with `[skip ci]` — no substantive new profitability claims, no new strategies, no new backtests, no new statistical validations.

## Remote Financial Files Fetched

### audit_dashboard/data/money_ready_verdict.json (generated 2026-11-14T20:58:53Z)

Source: `alpha_engine/money_ready_verdict.py --json`

| Class | n | WR | PF | WR OK | PF OK | DSR OK | Expectancy OK | MDD OK |
|-------|---|----|----|-------|-------|--------|---------------|--------|
| CRYPTO | 3705 | 35.87% | 0.9196 | false | false | false | false | false |

Key sub-metrics for CRYPTO:
- policy_clean_n: 21416
- policy_clean_wr: 42.09%
- policy_clean_pf: 0.2617 (severe PF inflation: 0.28× factor)
- expectancy: -0.0588 (negative)
- mdd_ok: false
- cvar_ok: false
- FDR gate: OFF (n_fdr_pass: 23, n_bonferroni_pass: 21)
- ML enhanced quarantine: 517 rows

### audit_dashboard/data/pick_summary_stats_48h.json (generated 2026-11-14T21:06:14Z)

FUTURES class (last 48 hours):
- n_decisive: 7 (below insufficient_n_floor of 10)
- wr_shrunk_pct: 44.44%
- pf: 4.888 (inflated by single-source concentration=100% via AlphaEngine)
- caveats: single_source_concentration, INSUFF-N

CRYPTO class data was truncated in fetch but showed high single-source concentration (99% via AlphaEngine).

### audit_dashboard/data/pick_summary_stats_14d.json (generated 2026-11-14T21:06:13Z)

FUTURES class (last 14 days):
- n_decisive: 189, wr_pct: 41.8%, pf: 1.376
- top_source_concentration: 100% via AlphaEngine

CRYPTO class (last 14 days):
- n_decisive: 1389, wr_pct: 44.28%, pf: 1.05
- dup_groups: 32, single_source_concentration: 99% via AlphaEngine

### audit_dashboard/data/pf_registry.json

Not fetchable — file may not exist on main or schema incompatible.

## Assessment

All remote financial files confirm: no class meets money-ready gates. WR below 50%, PF near or below 1.0, single-source concentration extreme (99-100%), FDR gate OFF, expectancy negative where reported.

## Remote vs Local Divergence

Remote is ahead by 5 auto-commits; local has uncommitted files (MARKET_BEATING_REPORT.md, dashboard/live_picks.json, mercury2/data/metrics_report.json, research/profitability/*, research/asset_class/equity/*). None of the local uncommitted files or remote commits change the profitability conclusion.
