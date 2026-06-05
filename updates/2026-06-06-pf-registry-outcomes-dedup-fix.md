# pf_registry Outcomes Dedup Fix — MeanReversionBB n=175 (2026-06-06)

## Broken

`PF_REGISTRY_INCLUDE_OUTCOMES=1` loaded 9,815 `at_pick_outcomes` rows but **MeanReversionBB never appeared** in `by_asset_class_strategy_policy_clean_net`. EQUITY showed a bogus `at_pick_outcomes` sleeve (n=85, PF=0.49).

Root cause (two bugs in `_load_outcomes_rows` + `_trade_date`):

1. **`source_system = "at_pick_outcomes"`** — `_strategy()` prefers `source_system` over `strategy`, so all outcomes rows keyed as one strategy.
2. **`v1::signal_validation::...` pick_ids** — `_trade_date()` truncated to 10 chars (`v1::signal`), collapsing 168 distinct EQUITY MeanReversionBB rows into ~8 symbol buckets.

## Fixed

- `tools/build_pf_registry.py`: stop setting `source_system` on outcomes rows; use full `v1::` pick_id in `_trade_date()`.
- `.github/workflows/audit-dashboard.yml`: `PF_REGISTRY_INCLUDE_OUTCOMES: '1'` on hourly build.

## Verified

```bash
PF_REGISTRY_INCLUDE_OUTCOMES=1 python3 tools/build_pf_registry.py
# → MeanReversionBB EQUITY n≈175, PF≈1.82 in by_asset_class_strategy_policy_clean_net

PYTHONPATH=. python3 tools/money_ready_snapshot.py
python3 tools/deploy_audit_files.py --only audit_data
```
