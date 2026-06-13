# Pro-Level Batch — P1-B Tribunal + Picks-Now Intrabar Gate

**Date:** 2026-06-13  
**Branch:** `feat/pro-level-batch-2026-06-13`  
**Worktree:** `.worktrees/pro-level-batch-2026-06-13`

## Summary

Next steps toward pro-level picks on `/audit` and `/audit/picks-now.html`:

### P1-B — Strategy kill tribunal
- `tools/strategy_kill_tribunal.py` — weekly KILL/PROBATION/KEEP from intrabar `at_signal_outcomes`
- `.github/workflows/strategy-tribunal.yml` — Friday 14:00 UTC dry-run; optional `--apply` via `TRIBUNAL_APPLY` secret
- luxalgo_confluence on do-not-auto-kill list unless n≥100 and WR<40%

### Picks-now pro-level gate
- `tools/picks_now_intrabar_gate.py` — sym×dir forward WR classification
- `tools/picks_now_professional.py` — demotes STRONG_BUY when intrabar WR<50% (n≥5) or class FAIL
- `audit_dashboard/picks-now.html` — intrabar FWD badge on each card
- `tools/build_intrabar_sym_dir_stats.py` — sym×dir JSON (from #572)

### CI wiring
- Hourly: `build_intrabar_sym_dir_stats.py` in `audit-dashboard.yml`
- Daily picks-now: sym×dir build before screener in `picks-now-refresh.yml`

## Verification

```bash
cd .worktrees/pro-level-batch-2026-06-13
python3 -m pytest tests/test_pro_level_intrabar_gate.py -q
python3 -c "import py_compile; py_compile.compile('tools/strategy_kill_tribunal.py', doraise=True); py_compile.compile('tools/picks_now_intrabar_gate.py', doraise=True)"
node tools/check_syntax.js audit_dashboard/picks-now.html
```

## Rollback

- Tribunal apply: revert `audit_trail/data/emitter_audit.json` force_kill entries
- Picks gate: unset scorer intrabar maps (empty JSON) — screener falls back to quant-only
