# Inventory and review coverage

## Local dated report set

The local dedup scan covered:

- `final_2026_11_14/**/*.md`
- `final_v2/**/*.md`
- `final_v3/**/*.md`
- `quick_wins/**/*.md`
- `updates/*2026-11-14*.md`

Result at the final local scan: **140 Markdown paths, 135 byte-unique documents, 5 duplicate paths suppressed.** This is a candidate inventory; unrelated update entries were not treated as finance evidence.

Local `final_v3` contained multiple peer packages. The current review read the local common-themes, deep-investigation, plan, GHA, asset-class, simulation, SubQ, focus, mutual-fund, and README reports; the prior review pass covered the 10-document `quant-audit-2026-11-14` package. These packages were not overwritten.

## Remote GitHub inventory

- Main ref used for the remote report-tree dedup: `086f410713ecd6cb3feec2735b224670418c0588`. GitHub main advanced during the review; the final observed main ref was `e1db9f5881bd874ee402de74e51887dde24b385e`.
- Remote `final_v3/finpredict/` commit: `d18adb510ab19c3aa8a87e8921533a339efb9a1d`, six Markdown files. All six were read. The folder describes “SubQ” comparisons but does not contain a verified provider invocation/response artifact.
- Across remote `final_v2/` and `final_2026_11_14/`: **470 Markdown paths, 309 unique Git blob SHAs, 161 duplicate paths**. Selected decision-bearing documents were reviewed by the peer-report audit, but not every unique document.
- Remote `final_v2/` subtree at the inspected snapshot: 447 paths, including 152 Markdown paths / 146 unique Markdown blob SHAs, 20 Python files, 135 JSON, 62 TXT, 65 ERR, 10 CSV, and 1 YAML. Generated and raw artifacts were inventoried, not all opened.
- The remote `final_v2` package includes hundreds of action/evidence files. The reviewed final/synthesis, peer, VWAP, scorecard, and asset-class documents are listed in `../05-evidence/INDEX.md`.

## Source-code review

The read-only source audit covered the requested backtest, mutual-fund, cost-gate, and relevant test modules. Actionable findings and anchors:

- Cost-gate policy / stale or missing index: `tools/per_class_cost_gate.py:29,152-179`.
- High-conviction gate exception path: `tools/hc_gates_python.py:446-450,522-536`.
- After-cost stamping error suppression: `audit_trail/dashboard_generator.py:7772-7789`.
- COT parameter selection and OOS boundary requiring verification: `tools/cot_contrarian_backtest.py:330-359`.
- Fund walk-forward survivorship/peer availability: `tools/fund_walkforward_backtest.py:200-213,226-235`.
- Feature series independently truncated and paired by position: `tools/mf_trait_features.py:33-75`.
- Fund account/commission/whole-share assumptions: `tools/mf_traits_walkforward_runner.py:48-49,208-246`.
- Cache loaders: `tools/mf_walkforward_backtest.py:78-80,217-247`; `tools/fund_walkforward_backtest.py:43-64`.
- Crypto verifier fixed cost and zero-total concentration division: `tools/verify_crypto_short_forward.py:108-113,144-152`.
- Tactical rotation timing/cost assumptions: `tools/tactical_rotation_backtest.py:102-163`.
- Small strategy-evaluation default sample: `tools/walkforward_strategy_eval.py:234-248`.

Still not covered in source: `tools/mf_case_study_what_wins.py`, `tools/stop_fill_replay.py`, `tools/hold_time_anomaly_scan.py`, `tools/per_asset_class_winners.py`, `tools/validators/`, and additional financial tests outside the named areas. No full codebase scan is claimed.

## Mutual-fund cache inventory

Read-only metadata inventory by the source-review agent:

- `audit_dashboard/data/mutual_fund_nav_cache/`: 46 CSV files, 10 column schemas; 37 use `Date,close`, nine use `Date,<ticker>`. Aggregate date span: 2010-01-01 to 2026-10-21.
- `audit_dashboard/data/mf_backtest_cache/`: 71 CSV files, all `Date,close`; aggregate date span: 1980-01-02 to 2026-10-22; includes `mf_backtest_universe.json`.
- `mf_walkforward_results.json` and `mf_traits_walkforward_results.json` are dated 2026-10-23. Outputs do not prove that the *current* untracked cache snapshots were used; no cache hash/provenance link was verified.

## Current GitHub Actions snapshot

- 360 YAML workflow files exist in the local tree and remote `main`.
- `gh workflow list --all --limit 5000` reports 365 registrations, five with no matching repository file: two `.github/workflows` paths and three `dynamic/...` paths. Reconcile before calling them stale.
- Of the 360 workflow files, 161 declare `concurrency`, 271 declare `timeout-minutes`, and 39 have `push` triggers.
- Latest checked `CI Tests` run at 2026-11-14 21:40Z, failed in both Python 3.11 and 3.12 jobs (run `43644095951`; head `96c53863`). Failure logs were not analyzed in this pass.
- At check time, `audit-dashboard.yml` had a pending 21:14Z run, an in-progress 20:14Z run, and a cancelled 19:14Z run. This is a snapshot, not a current guarantee.

## Explicit exclusions

This package does not claim that every file in the 602-path dirty worktree or every one of the 309 remote unique Markdown blobs was read. Most generated JSON/CSV/ERR artifacts, unrelated changes, and remaining detailed class/action reports were not content-reviewed. No strategy result is called independently reproduced unless this review directly checked the underlying artifact.

