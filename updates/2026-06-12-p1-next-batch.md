# P1 Next Batch — 2026-06-12

## What changed

### P1-A — Intrabar-only verdict sizing (Step 1)
- `alpha_engine/money_ready_verdict.py`: when `MONEY_READY_SIZING_SOURCE=intrabar` (default), verdict gates use intrabar WR/PF/n when intrabar n≥30.
- Preserves `policy_clean_*` fields for discovery-only display.
- `audit_dashboard/template.html`: major-goal tiles label sizing cohort + show discovery line when intrabar is primary.

Rollback: `MONEY_READY_SIZING_SOURCE=policy_clean`.

### P1-3 — Hourly pick_funnel + nav surface refresh
- `.github/workflows/audit-dashboard.yml`: runs `extract_funnel.py` + `build_nav_surface_matrix.py` after dashboard_generator (uses fresh local `dashboard_data.json`).
- Commits `pick_funnel_today.json`, `pick_funnel_90d.json`, `nav_surface_edge_matrix.json`.
- Freshness tripwires for nav_surface + pick_funnel_90d (26h).

### P1-4 — COMMODITY gap-fade intrabar replay
- `tools/replay_commodity_gap_fade_intrabar.py` — deduped intrabar stats vs BT proxy claim.
- Hourly report: `reports/commodity_gap_fade_intrabar_latest.json`.

### P0-5 — picks-now freshness tripwire
- audit-dashboard freshness block warns when `picks_now_track_record.json` age > 26h.

## Verification

```bash
python3 -m pytest tests/test_money_ready_intrabar_sizing_p1a.py -q
python3 tools/replay_commodity_gap_fade_intrabar.py --stdout
```

## Related PRs
- Builds on main (includes P0 merge wave)
- Complements #572 (sym×dir intrabar Track column)
