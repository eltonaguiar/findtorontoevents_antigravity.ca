# GHA Hourly Health Monitor — 2026-08-21

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — `ci.yml` returns 404; no "CI Tests" workflow found in last 100 main-branch runs. Tests are not running on main push.

**Chronic workflows (cancellation):** none — no `cancelled` conclusions found in 100 recent runs.

**Chronic workflows (failure — noteworthy):**
- `robust-edge-miner` — 15/15 consecutive failures in last 15 runs (runs #109–123, spanning 2026-08-07 to 2026-08-21). **This is intentional by design**: step 7 is labeled "Alert if a ROBUST candidate appeared (fail-LOUD = good news, review now)" — the workflow deliberately fails to loudly signal a robust edge candidate. Steps 1–6 (checkout, Python setup, deps, run miner, upload artifact) all succeed. Latest alert run: [#32484714176](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/32484714176) at 13:01 UTC.

**Open PRs:** 9 open (#667, #666, #665, #657, #600, #595, #581, #564, #562). CI Tests check status is N/A — no CI Tests workflow exists to gate these PRs.

**Action required:** Operator should investigate why the "CI Tests" (`ci.yml`) workflow is absent — no test gate on main or open PRs means regressions can merge silently. The `robust-edge-miner` chronic failure is by design (alert mechanism) — operator should review the 15 consecutive robust-candidate alerts and decide whether to act on the signals or adjust the workflow to avoid alert fatigue.
