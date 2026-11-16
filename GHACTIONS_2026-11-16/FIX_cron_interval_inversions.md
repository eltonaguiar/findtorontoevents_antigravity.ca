# FIX — Cron interval inversions (2026-11-16)

**Branch:** `fix/gha-cron-interval-inversions-2026-11-16`
**Base:** `antigravity/main` @ `a5e96c0b055`
**Applied by:** Hermes agent, executing the coordinator's ACTION_PLAN from `GHACTIONS_2026-11-16/`

## Why these two, and only these two

A scheduled workflow has a **runtime** and an **interval**. When runtime > interval, GitHub's
scheduler keeps only **one pending run per workflow** — every new fire that arrives while the
previous run is still executing **replaces the pending one**. The replaced run is recorded as
`cancelled` with `jobs_executed = 0`: it never started, so **no runner minutes were wasted**.
The only cost is lost data freshness.

Independent swarms (coordinator + 9 workers, and a second swarm of 10) converged on exactly two
workflows where this inversion is real. Everything else in the repo is healthy by this measure:
344 of 349 cron workflows run in under 0.5 × their interval.

| # | Workflow | Before | Runtime | Ratio | After |
|---|---|---|---|---|---|
| A | `audit-dashboard.yml` | `10 * * * *` (60 min) | 63–125 min (timeout 115) | 1.05–2.08 | `10 */3 * * *` (180 min) |
| B | `dynamic-alpha-engine.yml` | `18,48 * * * *` (30 min) | 77–80 min | ~2.6 | `23 */2 * * *` (120 min) |

`cancel-in-progress: false` was already set on both. That setting does **not** save scheduled
workflows — it protects manual/dispatch concurrency, while the scheduled-pending replacement is
scheduler behaviour. Widening the interval is the only fix that works.

## What this costs

- `/audit` dashboard data is now guaranteed fresh within **3 hours** instead of ~1 hour (which was
  already being missed on ~43% of fires, so the effective worst case was worse than 3h).
- ALPHA ENGINE dynamic runner fires every **2 hours** instead of every 30 minutes, but loses ~62%
  of those fires today — so real cadence improves from ~1 successful run/80 min to 1 run/2h
  guaranteed. Manual `workflow_dispatch` remains available on both.
- No runner-minute savings: the lost runs never started.

## Verification performed

```text
audit-dashboard.yml        schedule=[{'cron': '10 */3 * * *'}]  cancel-in-progress=False
dynamic-alpha-engine.yml   schedule=[{'cron': '23 */2 * * *'}]  cancel-in-progress=False
```

Both parse as valid YAML and resolve to a single cron entry. No other workflow files touched.

## Revert

```bash
git checkout antigravity/main -- .github/workflows/audit-dashboard.yml
git checkout antigravity/main -- .github/workflows/dynamic-alpha-engine.yml
git commit -m "revert: restore pre-stabilization cron intervals"
```

The pre-fix copies captured by the coordinator are also stored as
`GHACTIONS_2026-11-16/*.yml.pre-fix` on `main`.
