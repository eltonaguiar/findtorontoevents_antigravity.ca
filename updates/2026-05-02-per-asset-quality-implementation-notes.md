# Per-Asset Quality Implementation Notes (2026-05-02)

## What was implemented
- Added per-asset smart thresholds and normalization in `audit_trail/quality_gates.py`.
- Enforced `forward_validated` and per-class smart-gate floors (`score`, `forward WR`, `min trades`).
- Added `_smart_reject_reasons` for threshold failures.
- Reduced correlated penalty over-stacking and tuned specific high-impact penalties.
- Kept active gate safety-first while defaulting quality-only strict floors to permissive mode.
- Added per-asset payload sections in `audit_trail/dashboard_generator.py`:
  - `asset_class_summary` / `assetClassSummary`
  - `smart_picks_by_asset` / `smartPicksByAsset`
- Added per-asset quality badges in `audit_dashboard/template.html` with pass/warn/fail/idle states.
- Added monitor and gate scripts:
  - `audit_trail/quality_monitor.py`
  - `audit_trail/check_asset_quality_gate.py`
- Wired CI validation step in `.github/workflows/audit-dashboard.yml`.

## Validation performed
- `python -m py_compile audit_trail/quality_gates.py audit_trail/dashboard_generator.py audit_trail/quality_monitor.py audit_trail/check_asset_quality_gate.py`
- `python audit_trail/quality_monitor.py --check-per-asset --output-json audit_trail/data/asset_quality_monitor.json`
- `python audit_trail/check_asset_quality_gate.py`
- Baseline report generated:
  - `reports/per_asset_quality_baseline_2026_05_02.md`

## Post-CI validation recommendations
1. Confirm `Validate per-asset quality gates` step shows expected violations/warnings and mode behavior.
2. Confirm generated payload contains all seven asset classes in both new summary objects.
3. Open `/audit` and verify:
   - badge counts match payload,
   - pass/warn/fail state coloring is correct,
   - existing filters (`f-asset`, score, Smart Picks) still behave normally.
4. Run one hard-mode validation cycle by setting `QUALITY_GATE_MODE=hard` and verify CI blocks on violations.

## GitHub Actions steps to watch
- `Generate dashboard payload and build HTML`
- `Validate per-asset quality gates`
- `Commit updated data`
- `Deploy to all 3 FTP sites in parallel`
- `Verify URLs`
