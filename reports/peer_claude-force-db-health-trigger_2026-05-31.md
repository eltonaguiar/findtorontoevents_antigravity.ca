# Force db_health Cron Run — Banner Cleared (2026-05-31)

## Context
PR #208 merged with two surgical fixes:
1. Direction-aware `pnl_integrity` check (leverage-agnostic sign consistency)
2. Total-vs-info `open_bloat` check (eliminates info_schema overestimate false-reds)

Default cron is hourly. This task force-ran the Unified Audit Dashboard workflow to publish a fresh `db_health.json` so the live `/audit` banner clears immediately.

## Workflows triggered

| Workflow | ID | Run ID | Trigger | Status | Notes |
|---|---|---|---|---|---|
| Unified Audit Dashboard | 281988696 | 26705433076 | workflow_dispatch (mine) | completed/cancelled | Auto-cancelled by concurrency group (prior dispatch already in-progress) |
| Unified Audit Dashboard | 281988696 | 26704966861 | workflow_dispatch (prior) | completed/success | Ran on post-#208 main; published green db_health.json + FTP-deployed to all 3 sites |

The prior in-progress run (06:06 UTC dispatch) already incorporated PR #208 since it merged before that dispatch. The concurrency group held my 06:31 dispatch; cancellation is the correct/expected behavior — no second run needed because the prior run published the artifact this task required.

## Before / After

### Before (cached pre-fix snapshot)
```
generated_at: 2026-05-31T03:41:36Z
overall.any_red: true
checks.pnl_integrity.data.tier: "red"
checks.open_bloat.data.tier: "red"
```

### After (post-PR-#208 + FTP deploy)
```
generated_at: 2026-05-31T06:41:42Z
overall.any_red: false
checks.pnl_integrity.data.tier: "green"
checks.open_bloat.data.tier: "green"
```

### pnl_integrity payload (post-fix)
- metric: `sign_consistency (direction-aware, leverage-agnostic)` (NEW from #208)
- sampled: 24,158
- sign_mismatch: 130 → mismatch_pct = **0.54%** (green threshold pass)
- For reference, the OLD naive magnitude check would have reported 6,535 mismatches (27.05%) — the historical source of the false red.

### open_bloat payload (post-fix)
- open_count (canonical COUNT(*) WHERE status='OPEN'): 3,651
- info_schema_estimate: 41,051 (acknowledged as a misleading upper bound — total table rows, not opens)
- trading_picks.count_suspect: false
- last_terminal_write: 2026-05-31 04:12:54 (validator NOT frozen, only 2h since last close)
- tier: green

## Live verification
```
curl -s https://findtorontoevents.ca/audit/data/db_health.json | jq '.checks.pnl_integrity.data.tier, .checks.open_bloat.data.tier, .overall.any_red'
"green"
"green"
false
```

## Deployment path
The "Unified Audit Dashboard" workflow includes the dashboard build + 3-site FTP deploy steps (findtorontoevents.ca + tdotevent.ca + torontoevent.net) in the same job that runs `tools/db_health_check.py`. No separate dashboard workflow needed — both the JSON generation and the live-site push happen in run 26704966861.

## Result
BANNER_CLEARED: any_red=false, pnl_tier=green, bloat_tier=green.
