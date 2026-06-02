# Pick funnel discovery labels + deploy path (EAGLE2 A2/E)

**Date:** 2026-06-02

## Changes

- **`audit_dashboard/pick_funnel.html`**: Hero + live `money_ready_verdict` strip; nav matrix shows `DISCOVERY` / `NO SIZE` badges when holdout passes but class is not `MONEY_READY`; `why_no_edge` includes `policy_clean=` from sidecar.
- **`tools/deploy_audit_files.py`**: Upload `ai_leaderboard_index.json` under `ai_leaderboard` tag.

## Regenerate (local)

```bash
curl -fsS -o audit_dashboard/data/dashboard_data.json \
  'https://findtorontoevents.ca/audit/data/dashboard_data.json'
python3 tools/audit_pick_funnel/build_nav_surface_matrix.py
python3 tools/ai_attribution/build_ai_leaderboard.py
```

## Deploy

```bash
export FTP_USER=... FTP_PASS=...
python3 tools/deploy_audit_files.py --only pick_funnel
python3 tools/deploy_audit_files.py --only ai_portfolios
python3 tools/deploy_audit_files.py --only ai_leaderboard
```

Refs: `reports/EAGLE2_2026-06-02_GROK.md` workstreams A2, E.