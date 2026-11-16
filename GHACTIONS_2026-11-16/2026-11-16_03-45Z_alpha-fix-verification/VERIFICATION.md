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
- **OUTCOME (checked 04:45Z): FAILED — `The action 'Commit results' has timed out after 15 minutes.`**
  - The 5→15m cap FIX ITSELF WORKED (failure says "15 minutes", not "5") — so PR #813 is verified as applied.
  - BUT it revealed the deeper bug: the commit step's inline `git pull --rebase … 2>/dev/null` **HUNG**
    with zero output for the entire 15 min (log: commit at 04:18:20, then silence → timeout 04:33:32).
    No step cap can fix an infinite hang.
- **Follow-up fix: PR #829** (merged 04:44:52Z `5dc8e96`) — replaced the inline loop with
  `bash .github/scripts/safe_push.sh` (90s `GIT_NET_TIMEOUT` per git op, shallow deepen+merge fallback,
  fail-fast auth), called non-fatally. A hung fetch/push can no longer hang the step.
- **New verification target:** the first ALPHA run **created after 04:44:52Z** (i.e. NOT 04:35's
  `43805037772`, which is pre-#829). Expected: commit step finishes in seconds–minutes (success, or
  `::warning`+green), never a 15-min "timed out".

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

## Re-check 06:00Z — no post-#829 run yet (peers moved the goalposts, favorably)
- **No `dynamic-alpha-engine` run created after 04:44:52Z yet.** Latest = 04:35:36Z SUCCESS (pre-#829, old code).
- Reason: a peer widened ALPHA's cron from `18,48 * * * *` (30-min) → **`23 */2 * * *` (every 2h)** (commit
  `9b2bf9f8808`/`00f1f0e`, "widen inverted cron intervals that silently lost 43%/62% of fires"). Next fire ~06:23Z.
- Also: peer `f2ba2441de2` raised the commit-step cap **15m → 30m** and bumped alpha-fast job 40→60m.
- **My safe_push.sh change (PR #829) SURVIVED** that peer commit — the scheduled `alpha-engine` commit step
  still ends with `if ! bash .github/scripts/safe_push.sh; then ::warning; fi` (origin/main line 208).
- The remaining inline `git pull --rebase … 2>/dev/null` loop at origin/main ~L87-88 is inside the
  **`wsl-direct` job** (manual `use_wsl_direct` dispatch only; skipped on every scheduled run) — not a
  scheduled hang risk.
- Net: safe_push + 30m cap are belt-and-suspenders; verification pending the first 2-hourly fire (~06:23Z),
  whose commit step lands ~07:10–08:00Z. Re-check scheduled ~08:10Z.

### Status vs wakeup criteria
- Not yet PASS/FAIL — no post-merge run has executed (cron widened to 2h). Deferred, not failed.

## FINAL 08:13Z — ALPHA PASS ✅ / CI Tests RESOLVED ✅
### ALPHA safe_push (PR #829) — PASS, verified on live run
- First post-#829 run **`43819637050`** (created 06:51:16Z, > 04:44:52Z merge) concluded **SUCCESS**.
- Commit-step log evidence: `(shallow repo — deepening history for pull/rebase)` → `=== Push attempt 1/8 ===`
  → `=== Push attempt 2/8 ===` → **`Pushed successfully on attempt 2`**. No hang, no `timed out`, no 5-min msg.
- The old inline `git pull --rebase … 2>/dev/null` no-hang loop is gone; `safe_push.sh` deepens + retries + succeeds.
- Prior runs (02:25, 03:44) failed with 5→15m timeouts (pre-fix). Fixed chain: #811 job 60→90, #813 step 5→15,
  #829 inline-loop→safe_push. **Verified.**

### CI Tests regression — RESOLVED
- Failures: 05:27Z, 07:17Z (×2), 07:21Z — `ImportError: audit_trail.dashboard_generator not in sys.modules`
  across ~5 test files (`test_etf_elite_floor_and_60d_enrich`, `test_hc_after_cost_gate`,
  `test_m033_blocked_aggregator`, `test_derive_asset_class_precedence`, `test_m067_registry_reader`).
- **Newest run `43828468855` (08:05:20Z) = SUCCESS.** A peer's fix between 07:21 and 08:05 cleared it.
  The earlier worry (conftest/order-dependence from v4 `f107b7d`) is moot — main CI is green again.

### Net
ALPHA commit-step churn class is closed and verified; CI Tests green. Remaining work is the P1-P3 backlog
in `GHACTIONS_2026-11-16/2026-11-16_0620Z_CONSOLIDATED/SUMMARY.MD` (DB integrity, 27 push migrations,
dup-guard, zombie scheduler, etc.) — none of it a regression from this session's changes.
