# ALPHA step-timeout fix — verification log (2026-11-16)

Fix: PR #813 `Commit results` step `timeout-minutes: 5 → 15` (merged 02:39Z `edda8b53277`).
Final config confirmed on `origin/main`: job `timeout-minutes: 90` (L118), step `timeout-minutes: 15` (L186).

## Pre-fix runs (created BEFORE 02:39Z → old 5m cap) — both reproduce the bug
| run | created | outcome |
|---|---|---|
| 43788456858 | 01:49Z | failed `The action 'Commit results' has timed out after 5 minutes` (02:58:25Z) |
| 43792072850 | 02:25Z | failed `The action 'Commit results' has timed out after 5 minutes` (03:43:30Z) |

This confirms the diagnosis: the step's 5-min cap kills the retry loop mid-flight, converting a
**non-fatal** push failure (designed to exit green via `::warning::`) into a red job.

## Post-fix run (created AFTER 02:39Z → 15m cap)
- **run `43799911205`**, `workflow_dispatch`ed 03:44:02Z against `main` (which has the 15m step).
- Expected: either pushes successfully (green) OR exhausts 10 retries (~12 min worst case) and exits
  **green** via the warning path — in both cases **well under the 15-min cap, never "5 minutes"**.
- Outcome check scheduled (~04:45Z; compute takes 36–90 min).

## Queue observation during verification
- 43792072850's job **waited 33 min** for a runner (started 02:58 vs created 02:25) behind 43788456858.
- Confirms the "long runner" pattern: runs take 36–90 min of job time against a 30-min cron. The
  30-min cron's extra triggers become cheap pending-replacement cancellations (never materialize a
  runner), so the real cost is **queue latency**, not lost compute. Cron change (`18 */2 * * *`) remains
  a documented option, not applied (halves /audit alpha-refresh throughput).

## Subagent reconciliation (all returned)
- A (job-state): zero timed_out/neutral/waiting/phantom-queued; cancelled a stuck 82-min no-timeout
  branch guard run. Flagged AsterDEX dead daily-summary gate (needs Discord-posting decision),
  AI Tournament 5-month manual disable, `rl-agent-ppo` if:false. → `2026-11-16_03-02Z_jobstate-sweep/`
- B (branch): no duplicate CI cost; 65% branches stale; narrow stale `dup-guard` risk on active
  branches (merge-back by owners). → `2026-11-16_03-00Z_branch-audit/`
- C (stale/flapping): 0 failures after 01:55Z; ALPHA the only flapper (now fixed). → folded here.
