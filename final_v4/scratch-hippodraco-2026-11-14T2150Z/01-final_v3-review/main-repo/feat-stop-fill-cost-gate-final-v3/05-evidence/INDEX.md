# Evidence index

## Directly checked in this review

- GitHub main workflow inventory: 360 workflow YAML files; 365 API registrations; five registrations have no matching repository file.
- Workflow safeguards: 161/360 with `concurrency`; 271/360 with `timeout-minutes`; 39/360 with a `push` trigger.
- Recent `CI Tests` run `43644095951` at 2026-11-14 21:40Z failed in Python 3.11 and 3.12 jobs. Logs were not inspected.
- `audit-dashboard.yml` recent run state: 21:14Z pending, 20:14Z in progress, 19:14Z cancelled at check time.
- GitHub main `alpha_engine/money_ready_verdict.py`: `MONEY_READY_FDR_GATE` and `MONEY_READY_SINGLE_SOURCE_GATE` default to `0`.
- GitHub main `ml_gatekeeper/gatekeeper.py`: leakage masking defaults on unless explicitly disabled.
- Remote main report snapshots:
  - `d18adb510ab19c3aa8a87e8921533a339efb9a1d`: six-file `final_v3/finpredict` package.
  - `086f410713ecd6cb3feec2735b224670418c0588`: main tree used for the 470-path / 309-unique Markdown inventory.
  - `e1db9f5881bd874ee402de74e51887dde24b385e`: latest observed main at final check; later than the report-tree inventory snapshot.
- Local feature branch snapshot: `6c219e2ebd8e05c75f7ee0c9704272f6d6660995`; 602 dirty paths at final check, 234 commits behind and 3 ahead of local `origin/main`.

## Source audit anchors

- `alpha_engine/money_ready_verdict.py:179-194` - FDR and single-source hard enforcement defaults.
- `ml_gatekeeper/gatekeeper.py:90-108` - leakage feature list and default-on masking.
- `tools/per_class_cost_gate.py:29,152-179` - policy for missing/stale evidence.
- `tools/hc_gates_python.py:446-450,522-536` - cost gate call and exception path.
- `audit_trail/dashboard_generator.py:7772-7789` - after-cost stamping error handling.
- `tools/cot_contrarian_backtest.py:330-359` - parameter selection/OOS section; exact selection expression not confirmed by source-review agent.
- `tools/fund_walkforward_backtest.py:200-213,226-235` - peer comparison sample availability.
- `tools/mf_trait_features.py:33-75` - date alignment assumptions.
- `tools/mf_traits_walkforward_runner.py:48-49,208-246` - account/commission/share assumptions.
- `tools/mf_walkforward_backtest.py:78-80,217-247` and `tools/fund_walkforward_backtest.py:43-64` - cache loaders.
- `tools/verify_crypto_short_forward.py:108-113,144-152` - fixed cost and zero-total concentration calculation.
- `tools/tactical_rotation_backtest.py:102-163` - monthly decision/execution and costs.
- `tools/walkforward_strategy_eval.py:234-248` - minimum sample default.

## Key peer reports reviewed

- Local `final_v3/00_common_themes/BUGS.md`, `DEEP_INVESTIGATION.md`, `01_plan/GENERAL_FIXES.md`, `GITHUB_ACTIONS_FIXES.md`, `ASSET_CLASS_FIXES.md`, `BACKTEST_SIMULATIONS.md`, `02_subq/COVERAGE_AND_COMPARISON.md`, `03_focus/DECISION.md`, and `MUTUAL_FUNDS_SUBSET.md`.
- Remote `final_v3/finpredict/README.md`, `PLAN.md`, `FOCUS_DECISION.md`, and `subq/A_COMMON_THEMES.md`, `B_ASSET_CLASS_RANKING.md`, `C_MUTUAL_FUND_SUBSET.md`.
- Remote `final_2026_11_14/finpredict-v2/05_final/FINAL_SYNTHESIS.md`, `MASTER_AUDIT.md`, `PEER_CLAIMS_MATRIX.md`, `VWAP_VERDICT.md`, research scorecard/v4 verdict, peer reviews of mega-mutation and Variant C, and selected class reports.
- Specific conflicting claim sources: `final_2026_11_14/finpredict-v2/03_peer_reviews/FP1_flaxen_hair_mega_mutation.md`, `FP2_deepAI_profitable_v1.md`, and `final_2026_11_14/finpredict-v2/02_research/profitability/runs/v4/VERDICT.md`.
- Remote `final_v2/finpredict/per-asset-class/PROFITABILITY_ROADMAP.md`, `final_v2/inspect-wt/02_profitability_per_asset_class/_overall.md`, `mutual_funds.md`, and `REVIEW_SYNTHESIS.md`.

## Not independently reproduced

The following are peer-reported figures, not new results generated here: the 3,500-row class ledger; stop-fill replay deltas; the 170-ledger benchmark result; COT OOS PF; crypto mega-mutation/Variant C metrics; mutual-fund rankings/returns; and claims about CI failure frequency, Python setup, or workflow runtime. Use their source reports as hypotheses to reproduce, not as verified live performance.

No tests, backtests, database queries, scanners, or model training were run in this review.

