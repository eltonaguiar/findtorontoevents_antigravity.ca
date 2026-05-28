# AI Tournament + Audit Data Quality Fixes (2026-05-28)

**Source audit:** `TOURNYFIND_CURSOR_COMPOSER.MD`  
**PR scope:** P0/P1 fixes for misleading leaderboard math, missing live JSON deploys, stale static HTML, and audit console 404s.

## What was broken

1. **AI Tournament ALL-tab leaderboard** recomputed `WR × PF` in the browser while the footnote promised CI-adjusted `lower_95%(WR) × lower_95%(PF)` from `ai_tournament_leaderboard.json` — rankings could disagree by 2–3× on score.
2. **`ai_tournament_model_diagnostics.json`** existed locally but was never in `deploy_audit_files.py` or the tournament pipeline commit step → live 404.
3. **Static registry table** listed 11 models (with "Antrhopic" typo) while JSON had 39 models.
4. **Footer cron text** said 23:00 UTC while picks fleet runs at 12:00 UTC.
5. **Main `/audit/`** fetched `regime_report.json` from GitHub raw (404 in browser console) instead of `/audit/data/regime_report.json`.

## What changed

| File | Change |
|------|--------|
| `audit_dashboard/ai-tournament.html` | ALL tab renders `ai_tournament_leaderboard.json`; window tabs show approximate banner; dynamic model registry from summary JSON; phase bar + footer cron aligned |
| `tools/deploy_audit_files.py` | Deploy diagnostics, recency JSONs, `regime_report.json` to `/audit/data/` |
| `audit_dashboard/template.html` | Regime fetch uses `data/regime_report.json` (same-origin) |
| `.github/workflows/ai-tournament-pipeline.yml` | Run `generate_diagnostics.py` and commit diagnostics JSON |

## Verification

```bash
node tools/check_syntax.js audit_dashboard/ai-tournament.html   # must exit 0
python3 -c "import py_compile; py_compile.compile('tools/deploy_audit_files.py', doraise=True)"

# After deploy:
curl -sS -o /dev/null -w '%{http_code}\n' https://findtorontoevents.ca/audit/data/ai_tournament_model_diagnostics.json
curl -sS -o /dev/null -w '%{http_code}\n' https://findtorontoevents.ca/audit/data/regime_report.json
```

Playwright: zero `pageerror` on `/audit/ai-tournament.html`; main `/audit/` should no longer 404 `regime_report.json` once `regime_report` is deployed via `deploy_audit_files.py --only audit_data`.

## Not in this PR (follow-up)

- OPEN picks with `pnl_pct: 0.0` placeholder (resolver/ingest)
- Standalone `money_ready_verdict.json` 13h staleness vs dashboard embed
- `EXPIRED` status emission vs methodology copy
