# AI Leaderboard page fix + CI hardening (2026-06-06)

## Symptoms

`/audit/ai_leaderboard.html` looked broken: red money-ready bridge banner claimed "Frozen/thin book" (38 picks / 1 engine) while the leaderboard table had fresh data (189 picks / 43 engines). Unified Audit Dashboard CI was failing on `blueprint_generator.py` null `total_pnl_pct` sort.

## Root causes

1. **`audit_surface_truth.json` stale on FTP** — banner embeds leaderboard snapshot; not redeployed after swarm ingest revival.
2. **`audit-dashboard.yml` FTP gap** — `data/*.json` glob skips `data/ai_leaderboard/` subdirectory.
3. **`blueprint_generator.py`** — `sort(key=total_pnl_pct)` crashed when value is `None`.
4. **`swarm-pick-review.yml`** — promotion `SchemaError` on tournament timeframes aborted the job before resolver/leaderboard rebuild (fixed in prior commit via `normalize_timeframe()`).

## Fixes

| File | Change |
|------|--------|
| `tools/build_audit_surface_truth.py` | Context-aware leaderboard banner (frozen vs research-only) |
| `audit_dashboard/blueprint_generator.py` | Null-safe `total_pnl_pct` sort |
| `.github/workflows/audit-dashboard.yml` | FTP-deploy `data/ai_leaderboard/*.json` on all 3 hosts |
| `.github/workflows/swarm-pick-review.yml` | `continue-on-error: true` on promotion step |
| `tests/test_promote_tournament_timeframes.py` | Regression for horizon normalization |

## Verification

```bash
python3 tools/build_audit_surface_truth.py
python3 tools/deploy_audit_files.py --only audit_data
python3 tools/deploy_audit_files.py --only ai_leaderboard
curl -s 'https://findtorontoevents.ca/audit/data/audit_surface_truth.json' | jq '.ai_leaderboard'
pytest tests/test_ai_leaderboard.py tests/test_promote_tournament_timeframes.py
```

Live: `audit_surface_truth.json` generated 2026-06-06, banner "Research only — ingest active (189 picks, 29 resolved)".