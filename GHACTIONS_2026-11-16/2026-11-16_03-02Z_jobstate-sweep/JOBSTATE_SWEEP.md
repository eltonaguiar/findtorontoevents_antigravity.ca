# Job-state sweep findings (skipped / timed_out / hogs) — 2026-11-16

Snapshot: last 300 runs (01:14–02:48Z). Zero `timed_out` / `neutral` / `action_required` /
`stale` / `waiting` runs. Zero phantom `queued` (>60 min, 0 jobs). 13 non-terminal runs all <30 min.

## Actions taken
- **Cancelled run `43787523178`** — `Branch Large File Duplicate Guard` on branch
  `hermes/forex-session-window-fix`, stuck **82+ min** in `Scan for duplicated large blobs` with **no
  timeout** (stale branch copy; main is fixed with 15-min timeout + serialized concurrency). Freed a
  runner. Result: `cancelled`. ✅ **This was a real live queue hog.**

## Findings — documented, NOT auto-fixed (need a decision; external/user-facing or possibly intentional)

| Item | Evidence | Why not auto-fixed |
|---|---|---|
| **AsterDEX `daily-summary` permanently dead** | gate `if: github.event.schedule == '0 0 * * *'` but the only cron is `'12 * * * *'`; that literal never matches → daily summary **never runs on schedule** (`asterdex-paper-trading.yml:187`) | fixing it restores **daily Discord posts** (external action) — needs explicit go-ahead |
| **AI Tournament Pipeline** | workflow `disabled_manually` since **2026-06-05**; daily `33 12 * * *` cron → **silent ~5-month outage** of daily picks + DB ingest | it was *manually* disabled; blind re-enable could re-run a deliberately-stopped pipeline |
| **`rl-agent-ppo`** | job `if: false` (DEPRECATED 2026-03-16) — dead but still dispatchable (green no-op) | low impact; delete/disable is cosmetic — owner's call |
| **Master Automation Scheduler** | 3 of 4 jobs skipped per hourly fire (per-cron gates) | **by design** — structural yellow, not breakage |

## Notes
- **Unified Audit Dashboard** `43785626938` waited **61 min** for a runner before starting (then ran
  normally). Borderline queue-latency, not a phantom — worth watching as the fleet grows.
- By-design skips confirmed (no action): `wsl-direct` in ALPHA (dispatch-only), `smart-money-tracker`
  weekday/Sunday gates, `worldclass-pipeline` validate, `live-trading` weekly job.

## Recommended next (needs user sign-off)
1. AsterDEX: add `cron: '0 0 * * *'` + gate `trade` to the hourly literal and `daily-summary` to the
   daily literal (with `if: always()`), IF daily Discord summaries are wanted.
2. AI Tournament: confirm whether the June-disable was intentional; if not, re-enable and watch one run.
3. `rl-agent-ppo`: delete or rename to `.disabled`.
