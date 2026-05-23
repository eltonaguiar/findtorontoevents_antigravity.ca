# Sports live-smoke: gate behind `LIVE_SMOKE=1` env

**Date:** 2026-05-03
**Scope:** `tests/test_sports_endpoints_smoke.py`,
`.github/workflows/sports-smoke-and-e2e.yml`
**Owner:** ZZ-SPORTS-FLAKE subagent

## Change

`tests/test_sports_endpoints_smoke.py` now skips by default. It only
executes when the environment variable `LIVE_SMOKE=1` is set. The
canonical caller is `.github/workflows/sports-smoke-and-e2e.yml`,
which sets `LIVE_SMOKE: '1'` on the pytest step (PR-path-touch +
hourly cron + manual `workflow_dispatch`).

Run locally with:

```
LIVE_SMOKE=1 python -m pytest tests/test_sports_endpoints_smoke.py -v
```

## Why

On 2026-05-03 the live production endpoints
(`/live-monitor/api/sports_*.php`) started returning HTTP 200 with
`{"ok": false, ...}` JSON. The smoke suite asserts
`d.get("ok") is True` on five tests, so every PR running the default
pytest collection was failing, regardless of whether it touched
sports code.

This cascade-blocked PRs **#597, #608, #615, #661, #745**. None of
those PRs introduced the regression — the existing transient-flake
skip pattern (`URLError` / `socket.timeout` /
`ConnectionRefusedError`) does not catch a 200-but-`ok=false`
response, and the network-reachability probe at module load also
passes.

## Why not option A (skip on `ok=false`) or C (flaky-rerun)

- **Option A** silences real production regressions — exactly what
  this suite was built to detect.
- **Option C** wastes CI minutes and remains red on any
  persistent prod issue.
- **Option B (this change)** keeps the tests informative locally
  and via the hourly cron / on-demand workflow, but stops them
  blocking PRs that don't touch sports code.

## Trade-offs

PRs that DO touch sports paths still execute the smoke suite via
`sports-smoke-and-e2e.yml` (path filter unchanged, `LIVE_SMOKE=1`
set in env). General CI / unrelated PR pipelines no longer block on
live prod state.

## Next steps

- Investigate the underlying production `ok=false` regression
  separately. The hourly cron will continue surfacing it.
- If a future workflow needs to run these tests, set
  `LIVE_SMOKE: '1'` in its env block.
