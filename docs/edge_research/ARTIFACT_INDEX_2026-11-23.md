# Kilo artefact index — 2026-11-23 session

All paths below verified to resolve at the time of writing. Paper only; zero capital.

## Updates (fix/analysis notes) (16)

- `updates/2026-11-23-P0-fixes-parity-drawdown.md`
- `updates/2026-11-23-P1-5-benchmark-blocker-verifier.md`
- `updates/2026-11-23-P2-10-fmp-key-rotation.md`
- `updates/2026-11-23-P2-7-fx-backfill-blocker.md`
- `updates/2026-11-23-branch-staleness-and-merge-readiness.md`
- `updates/2026-11-23-cross-system-consensus.md`
- `updates/2026-11-23-crypto-cost-breakthrough.md`
- `updates/2026-11-23-equity-etf-coverage-is-zero.md`
- `updates/2026-11-23-gate-engine-rankings.md`
- `updates/2026-11-23-incubator-defects.md`
- `updates/2026-11-23-ml-inventory-and-top-gainer-test.md`
- `updates/2026-11-23-shrinkage-does-not-create-edge.md`
- `updates/2026-11-23-spy-timing-vs-buyhold.md`
- `updates/2026-11-23-strategy-family-merge-readiness.md`
- `updates/2026-11-23-synthetic-closed-picks-defect.md`
- `updates/2026-11-23-two-hurdle-kill-rule.md`

## Edge research docs (7)

- `docs/edge_research/CHANGELOG_G3_AND_COST_2026-11-23.md`
- `docs/edge_research/DISTANCE_TO_INVESTABLE.md`
- `docs/edge_research/G3_DSR_ANALYSIS_AND_CRITERIA_2026-11-23.md`
- `docs/edge_research/KILO_PLAN_ACHIEVEMENTS_CRITIQUE_2026-11-23.md`
- `docs/edge_research/PREREG_H-2026-11-23-01_TOM_CRYPTO.md`
- `docs/edge_research/PROCUREMENT_SPECS_2026-11-23.md`
- `docs/edge_research/STATE_OF_PROGRAMME_2026-11-23.md`

## Tools added (20)

- `tools/aggregate_agent_picks.py`
- `tools/assert_no_investable.py`
- `tools/assert_surface_parity.py`
- `tools/build_asset_class_rankings.py`
- `tools/cross_review_picks.py`
- `tools/cross_system_consensus.py`
- `tools/label_closed_pick_outcomes.py`
- `tools/mf_vs_etf_measured.py`
- `tools/pick_gate.py`
- `tools/pit_universe.py`
- `tools/rank_on_lower_bound.py`
- `tools/rank_picks_lower_bound.py`
- `tools/shrinkage_estimator.py`
- `tools/spy_timing_test.py`
- `tools/tom_forward_clock.py`
- `tools/top_gainer_backtest.py`
- `tools/two_hurdle_kill.py`
- `tools/validate_gate_reports.py`
- `tools/validate_incubator.py`
- `tools/verify_forward_benchmark.py`

## JSON reports (26)

- `reports/agent_picks_rollup.json`
- `reports/asset_class_rankings.json`
- `reports/closed_picks_outcome_basis.json`
- `reports/cost_ladder.json`
- `reports/cost_per_class_model.json`
- `reports/cross_review_picks.json`
- `reports/cross_system_consensus.json`
- `reports/crypto_breakeven_costs.json`
- `reports/crypto_cost_breakthrough_sensitivity.json`
- `reports/deflation_programme.json`
- `reports/distance_analysis.json`
- `reports/g3_bar_analysis_corrected.json`
- `reports/g3_shortlist.json`
- `reports/investable_invariant.json`
- `reports/lower_bound_ranking.json`
- `reports/mf_vs_etf_measured.json`
- `reports/overall_ranking.json`
- `reports/picks_lower_bound_ranking.json`
- `reports/pit_status.json`
- `reports/quant_metrics.json`
- `reports/real_dated_class_verdicts.json`
- `reports/real_dated_picks_dsr.json`
- `reports/shrinkage_estimator.json`
- `reports/spy_timing_test.json`
- `reports/sr_star_table.json`
- `reports/two_hurdle_kill.json`

## Verification

- files listed: 69; missing: 0
- 62 project tests pass; `tools/assert_no_investable.py` enforces the 0-investable verdict in CI.
