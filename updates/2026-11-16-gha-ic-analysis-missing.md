# GHA dashboard IC analysis data missing — fix (Nov 16, 2026)

**NOT FINANCIAL ADVICE** — internal research notes.

## Summary

The `/audit` dashboard "Strategy IC Analysis" card showed:

> IC analysis data not available (404 or empty response). Will populate after the next `build_ic_analysis.py` run.

Root cause: **`build_ic_analysis.py` was a phantom script** — it never existed anywhere in the repo, any worktree, or any PR branch. The nightly `pick-funnel-nightly.yml` step that would have run it was removed on 2026-06-12 (with a note to restore only together with an actual committed builder), and `audit_dashboard/data/strategy_ic_analysis.json` was never (re)generated. The last known copy (`d_strategy_ic_analysis.json` audit artifact) was generated 2026-05-29 and is marked DEAD/stale (169 days). The dashboard's inlined IC card (`audit_dashboard/template.html:1329`) fetches `./data/strategy_ic_analysis.json` and renders the "not available" banner on 404/empty.

## What was missing

| Item | Status |
|------|--------|
| `tools/audit_pick_funnel/build_ic_analysis.py` | **Absent (phantom)** — referenced by template comment and removed workflow step, never committed |
| `audit_dashboard/data/strategy_ic_analysis.json` | **Absent locally** — last generated 2026-05-29, now DEAD |
| Workflow build step | **Removed** (2026-06-12) pending an actual builder |
| `tools/deploy_audit_files.py` deploy entry | Present (line 38, `pick_funnel` tag) but soft-skips when local file missing |

## What I fixed

1. **Created `tools/audit_pick_funnel/build_ic_analysis.py`** — pure-Python (no numpy/scipy, so it runs under the nightly workflow which only installs `pymysql`). Reads `audit_dashboard/data/dashboard_data.json::picks.recent_closed` (resolved WIN/LOSS picks), computes the Spearman rank correlation between `elite_score` and `pnl_pct` per strategy (min 3 resolved picks), groups by `asset_class`, applies a Bonferroni correction (alpha = 0.05 / n_strategies), and writes `audit_dashboard/data/strategy_ic_analysis.json` with the exact schema the dashboard card consumes (`by_class.*`, `n_strategies`, `n_positive_ic`, `n_negative_ic`, `n_decisive`, `n_ten_plus_classes`, `generated_at`).

2. **Generated `audit_dashboard/data/strategy_ic_analysis.json`** from the live `dashboard_data.json` (fetched from production) — 108 strategies across 6 classes, generated 2026-11-16T04:08:51+00:00. The IC card now loads real data instead of the 404 banner.

3. **Restored the workflow step** in `.github/workflows/pick-funnel-nightly.yml` — re-added "Build strategy IC analysis" after the `dashboard_data.json` fetch, soft-failing (`|| echo ...`) so one bad run never zeroes the nightly commit (masked-failure #7 lesson). The existing per-file guarded `git add` loop already covers `strategy_ic_analysis.json` (absent => skipped, never atomic-zeros the commit).

## Verification

- `python3 tools/audit_pick_funnel/build_ic_analysis.py` ran successfully and wrote valid JSON.
- Output passes the dashboard's expected-shape check: all fields accessed by `audit_dashboard/template.html:1321-1422` are present (`by_class[k].bonferroni_corrected_alpha`, `n_strategies`, `n_positive_ic`, `n_negative_ic`, `n_decisive`, `n_ten_plus_classes`, `generated_at`).
- `dashboard_enhancements.js` has no `strategy_ic_analysis` references (the IC card is fully self-contained in `template.html`), so no silent-fail fetch path exists there.
- Transient `audit_dashboard/data/dashboard_data.json` (fetched fresh in CI each night) was removed after generation; only the generator + output + workflow step are part of this fix.

## Files changed

- `tools/audit_pick_funnel/build_ic_analysis.py` (new)
- `audit_dashboard/data/strategy_ic_analysis.json` (new, generated)
- `.github/workflows/pick-funnel-nightly.yml` (restored build step)
