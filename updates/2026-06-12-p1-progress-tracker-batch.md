# P1 Progress Tracker Batch — 2026-06-12

## What changed

### P1-1 — Intrabar symbol×direction forward WR
- Added `tools/build_intrabar_sym_dir_stats.py` → writes `audit_dashboard/data/intrabar_sym_dir_fwd.json` from `at_signal_outcomes.intrabar_*`.
- Wired hourly build in `.github/workflows/audit-dashboard.yml` (after `build_intrabar_truth_by_class.py`).
- `audit_trail/dashboard_generator.py` stamps `sym_dir_fwd_wr`, `sym_dir_fwd_n`, `sym_dir_fwd_pf` on active/closed picks.
- `audit_dashboard/template.html` Track column prefers intrabar sym×dir WR when n≥3 (bold cell).

### P1-5 — FOREX F1=CONTRARIAN live block (M-038)
- `audit_trail/quality_gates.py`: blocks sized FOREX picks with `entry_condition_f1=CONTRARIAN` or htf_bias proxy (bull+SHORT / bear+LONG).
- Exempts `forward_test_only` and `_monitor_mode` measurement lanes.
- Kill-switch: `FOREX_F1_CONTRARIAN_GATE_ENABLED=0`.

### P1-6 — Portfolio history stale banner
- `audit_dashboard/portfolio_history.html`: visible 🚨 banner directing users to `/audit` intrabar truth until regen.

### Progress tracking
- `reports/PROGRESS_CURSOR_P0P1_June122026.MD` — living P0/P1/P2 checklist + PR status.

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('tools/build_intrabar_sym_dir_stats.py', doraise=True)"
python3 -m pytest tests/test_forex_f1_gate_p1.py -q
# DB creds required for sidecar build:
python3 tools/build_intrabar_sym_dir_stats.py --stdout | head
```

## Related PRs
- Builds on #570 (`feat/p0-next-steps-batch`)
- New branch: `feat/p1-progress-tracker`
