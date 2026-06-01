# Force PF Registry Refresh — AFTER (Result)

Date: 2026-05-31  
Author: peer Claude (force-refresh agent)

## TL;DR
**STILL_STALE.** Published `pf_registry.json` + `money_ready_verdict.json` are still timestamped `2026-05-31T03:54:06Z` / `03:54:05Z` — both pre-#182 (merged 05:47Z). The workflow run we depended on (`26704966861`) is **still queued** as of container time 06:12:34Z. Reason: GitHub Actions runner queue saturated + an upstream peer-agent cancellation cascade that consumed all prior dispatch attempts. Retired strategies `cta_golden_cross_200` + `prediction_market_consensus` ARE already absent from the published JSON (occurrence count = 0 in both), so the live dashboard is not lying to users — but the `generated_at` field has not refreshed since the merge, making it impossible to prove the post-#182 config was honored.

## Workflow forensic timeline (UTC)

| Time | Run ID | Event | SHA | Conclusion |
|---|---|---|---|---|
| 03:23:29 | 26702060367 | schedule | 2113be82 | **success** (origin of current 03:54Z JSONs) |
| 05:37:45 | 26704453085 | workflow_dispatch | 6f38a9a1 | cancelled |
| 05:44:36 | 26704578909 | schedule | 0e0f8e5f | cancelled |
| 05:44:58 | 26704585108 | workflow_dispatch | 7bc58626 | cancelled |
| 05:47Z | — | **PR #182 merged** (fc5d2f9f2) | — | — |
| 05:48:15 | 26704645417 | workflow_dispatch | fc5d2f9f | cancelled |
| 05:50:12 | 26704679535 | workflow_dispatch | c41fff24 | cancelled |
| 05:58:18 | 26704818902 | workflow_dispatch (Phase-8) | 3a352a5b | cancelled |
| 06:06:07 | **26704966861** | workflow_dispatch (this agent) | 705e8d35 | **still queued** |

7 consecutive cancellations is anomalous for a workflow whose YAML declares `cancel-in-progress: false` (audit-dashboard.yml line 37). Concurrency group "dashboard-publish" should be QUEUING dispatches, not cancelling them. Either:
- A peer agent is calling `gh run cancel` manually as part of some "kill stale runs" loop, or
- The runner pool ran out of capacity and GitHub auto-cancelled queued workflow_dispatch runs older than N minutes (less likely — schedule run also got cancelled at 05:44:36).

Run 26704966861 has been queued for ~6 minutes at container time 06:12:34 — within normal queue-wait expectations for this saturated state. Queue backlog at 06:12: 20+ workflows queued, 0 in_progress.

## Diagnosis of failure mode

There is no pipeline bug to fix:
1. `.github/workflows/audit-dashboard.yml` lines 509 + 513 correctly run `tools/money_ready_snapshot.py` and `tools/build_pf_registry.py`.
2. Line 801 stages both `audit_dashboard/data/pf_registry.json` and `audit_dashboard/data/money_ready_verdict.json` in the commit-step file list.
3. `tools/build_pf_registry.py` lines 222-240 already consult `BLOCKED_SOURCE_SYSTEMS` from `audit_trail/quality_gates.py` — which is the file PR #182 (commit `fc5d2f9f2`) modified to add both retired strategies.

The blocker is purely operational: get a runner slot for the queued run.

## Verification (post-monitor false-success events)

Monitor tasks `bkz6r1ugc` and `b8v2d1t01` both emitted spurious `completed:success` events while the underlying API consistently reported `queued`. These appear to be transient API/cache glitches (gh api 5xx returns producing different jq output that gets misread as state change). Treat monitor events as advisory only; ground truth is `gh api repos/.../actions/runs/<id>` polled directly.

Final state at end-of-session:
```
gh api repos/.../actions/runs/26704966861 → {"status":"queued","conclusion":null,...}
gh api .../jobs/78704330422              → {"status":"queued","completed_at":null,...}
git show origin/main:audit_dashboard/data/pf_registry.json   → generated_utc: 2026-05-31T03:54:06Z (UNCHANGED)
git show origin/main:audit_dashboard/data/money_ready_verdict.json → generated_at: 2026-05-31T03:54:05.895664+00:00 (UNCHANGED)
curl pf_registry.json → 2026-05-31T03:54:06Z
curl money_ready_verdict.json → 2026-05-31T03:54:05.895664+00:00
Retired-strategy occurrence count in live pf_registry.json: 0
Retired-strategy occurrence count in live money_ready_verdict.json: 0
```

## NEEDS_USER

Operator action required: **investigate the cancellation cascade source on the "Unified Audit Dashboard" workflow** AND let run `26704966861` finish (do NOT cancel it). Specific asks:

1. Identify which agent / script is calling `gh run cancel` on Unified Audit Dashboard runs at 05:37, 05:44, 05:44, 05:48, 05:50, 05:58. (Could be `gha-stale-workflows-audit.yml`, the cleanup hook in `audit-hourly-update.yml`, or a peer Claude session.) Kill or pause it until 26704966861 commits.
2. If the runner pool genuinely lacks capacity, increase the self-hosted runner count or wait — the run is at the head of the queue.
3. Once 26704966861 commits, verify `curl https://findtorontoevents.ca/audit/data/pf_registry.json | jq .generated_utc` > `2026-05-31T05:47:00Z`.

No new dispatch has been fired by this agent since 06:06:07Z to avoid adding to the cancellation cascade.

## Files
- `reports/peer_claude-force-pf-registry-refresh_plan_2026-05-31.md` (BEFORE)
- `reports/peer_claude-force-pf-registry-refresh_result_2026-05-31.md` (this file)
