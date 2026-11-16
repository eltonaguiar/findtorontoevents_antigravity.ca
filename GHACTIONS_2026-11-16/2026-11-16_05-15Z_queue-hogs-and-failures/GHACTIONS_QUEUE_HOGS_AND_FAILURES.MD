# GHACTIONS — queue hogs, failures, and a cross-check of the fleet's own GHA findings

**Stamp:** 2026-11-16 ~05:15Z · **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Method:** read-only. REST via `gh api` (`/actions/runs` paginated, `?status=queued|in_progress`,
`/actions/runs/{id}/jobs`), `tools/gha_queue_audit.py --pages 25`, `tools/gha_nonmain_audit.py --pages 12`,
`tools/gha_queue_and_failure_report.py`. Nothing was cancelled, rerun, disabled, or edited.
**Raw:** `reports/gha_queue_audit.{json,md}`, `reports/gha_run_matrix_2026-11-16.json`,
`reports/gha_nonmain_audit.json`, `reports/gha_queue_and_failures_2026-11-16.md`.

> Numbers are a point-in-time snapshot. `origin/main` advances roughly every 60 s, so treat every count
> as "as of this stamp" and re-run the tool rather than citing this file as current.

## 1. Window

| Signal | Value |
|---|---|
| Runs created since 2026-11-14 | **2,500** |
| Runs created 2026-11-16 | **904** |
| Newest 1,000 runs | 941 success · 28 cancelled · 16 in_progress · 13 failure · 1 pending · 1 skipped (~94% green) |
| Workflows | 360 registered · 353 active · **7 disabled manually** · 308 scheduled |
| Queue at stamp | **21 queued** (all ghosts, §3) · 19 in_progress · **0 waiting / 0 action_required** |

There are **zero** `timed_out`, `stale`, `waiting`, or `action_required` runs in the window. The red is a
narrow tail concentrated in a handful of workflows, not a systemic break.

## 2. Queue hogs — where the runner-minutes go (48h)

| Workflow | Runs | Fail | Cancel | Skip | Total min | Avg min |
|---|---|---|---|---|---|---|
| ALPHA ENGINE - Dynamic Runner | 9 | 4 | 2 | 0 | 409 | 45.4 |
| Unified Audit Dashboard | 4 | 0 | 1 | 0 | 370 | **92.4** |
| ALPHA ENGINE FAST Tighter TP/SL | 10 | 0 | 2 | 0 | 322 | 32.2 |
| Copy Trader Intelligence Scrape | 10 | 0 | 0 | 0 | 252 | 25.2 |
| Discord Bot Persistent | 1 | 0 | 0 | 0 | 252 | **252.0** |
| Branch Large File Duplicate Guard | 7 | 0 | **7** | 0 | 198 | 28.2 |
| Gainer Predictor Scanner | 11 | 0 | 0 | 0 | 156 | 14.2 |
| ALPHA ENGINE - Live Autonomous Scanner | 3 | 0 | 0 | 0 | 131 | 43.6 |
| Baby Strat Real Forward Monitor | 6 | 0 | 0 | 0 | 100 | 16.6 |
| Cross-System Signal Aggregator | 10 | 0 | 0 | 0 | 91 | 9.1 |
| Polymarket Prediction Market Signals | 11 | 0 | 0 | 0 | 86 | 7.8 |

Notes, with the peer corrections folded in (see §7):

- **`Unified Audit Dashboard` at 92 min average on an hourly cron** cannot keep up with its own schedule.
  Peer run `43785626938` additionally **waited 61 min for a runner** before starting. This is queue
  latency, not lost compute — but it is why the dashboard's own freshness banner reads `1h 0m ago`.
- **`Discord Bot Persistent` is 252 min by design, not a hang.** `.github/workflows/discord-bot.yml` sets
  `timeout-minutes: 355  # 5h 55m` on a `7 */6 * * *` cron. It is a long-lived gateway process wearing a
  job's clothes: correct as written, but it permanently consumes ~1 concurrent slot.
- **`Branch Large File Duplicate Guard`: 7 of 7 runs cancelled, never once green**, 15–82 min burned each
  time. A peer (JOBSTATE_SWEEP) manually cancelled one stuck instance at 82 min. The runs are cancelled by
  their own stale-branch copies lacking the fixed concurrency; main's copy is hardened.
- **`ALPHA ENGINE - Dynamic Runner`** was the top time consumer *and* top failure source during the window;
  root cause and fix are in §4 (resolved by a later peer commit than my snapshot).

## 3. The 21 "queued" runs are ghosts, not a backlog

All 21 were created **2026-11-11T20:24–20:43Z**, have `created_at == run_started_at`, and cancel returns
HTTP 409 (`Cannot cancel a workflow run that has not been queued yet`). They hold no runner and block
nothing, but they corrupt every queue-depth reading. Disabled `sports-*` workflows are still among them —
disabling a workflow does not drain runs already queued.

Affected: Rapid Fire NOW Scanner, Portfolio Trackers, Sports smoke, Deploy Vetted Master-Picks, Sustained
Gainer, Claude Gainer ML Live, Winner Pattern, Incubator, Sports snapshots, Backtests+Deploy, Rapid
Validation, Dynamic Runner, UEPS Pick Runner, Gainer Tracker, Baby Strat, Signal Integrator, Outcome
Resolver, Enhanced ML Crypto, Copy Trader Forward, Meta-Strategy, Audit Hourly.

**Discrepancy with a peer report:** `updates/2026-11-16-ghactions-queue-audit-and-workflow-guards.md`
counted **51** ghosts spanning 2026-08-07 → 2026-11-11. My two independent probes (02:52Z and 05:1xZ) both
return **21**, all from 2026-11-11. Either the older rows were cleared between reports or the two queries
counted different states. Treat 21 as current; the class of defect (un-cancellable queued records) is real
and unchanged.

## 4. Failures today (2026-11-16 UTC)

13 failures. Grouped by cause, with resolution status:

| Failure | Runs | Status |
|---|---|---|
| ALPHA Dynamic Runner — `Commit results` step | #6571 01:22, #6572 01:49, #6573 02:25, #6574 03:44 (52.4/69.4/78.1/49.5 min) | **Root-caused and fixed by peers, after my snapshot** — see below |
| CI Tests | #3036 03:10 (4.8 min) | **OPEN** — stale literal-cron assertions (§8) |
| Regime Terminal HMM Live Scanner | #6539 03:42 (6.9 min) | Peer-fixed (`1eb3a34a71`, step 5m→15m) |
| Feed Health Check | #3816 04:48 (0.5 min) | Single short failure, not recurring |
| `mysql-q001-sync.yml` / `ml-gatekeeper-ab-bootstrap.yml` | #3/#4 each, 01:51–01:54 | **RESOLVED** — renamed to `*.yml.disabled` (`3d1aa94ba5e`); neither `.yml` exists on `main` today |

**The ALPHA sequence is the most instructive failure of the night**, because it took three attempts:

1. Peer PR #811 raised the job timeout 60 → 90 min (cancellations at the 60-min cap).
2. Peer PR #813 raised the `Commit results` **step** 5 → 15 min (step died at 5 min mid-retry-loop).
   Verified fixed in *form* — but my snapshot caught run `43799911205` failing at **"timed out after 15
   minutes"**.
3. That run logged `[main df5451e3] ALPHA ENGINE … 27 files changed` at 04:18:20Z and then produced **no
   output for 15 minutes** — an inline `git pull --rebase … 2>/dev/null` hang, which no step cap can fix.
   Peers replaced the loop with the hardened `safe_push.sh` (90 s per-git-op timeout) in **#829
   (`5dc8e96`)**.

Verified independently here: the 5→15 min change is present on `main`, and the 15-min timeout is what fired
— so the bump was applied but insufficient. Post-#829 verification (first run created after the fix) was
still pending at this stamp.

## 5. The 03:40–03:46 cancellation burst — now explained (peer R7)

I flagged 9 cancellations of 62 runs in 03:35–03:50Z across eight unrelated workflows, noted that four of
the victims already run `cancel-in-progress: false`, and listed "find the canceller" as an open item.
GitHub exposes no canceller field (`triggering_actor` is the *requester*, and it was `eltonaguiar` for all
nine, which attributes nothing).

A peer's R7 re-diagnosis (recorded in `08_FOLLOWUP_RESULTS.md`) closes this as **three mundane mechanics**,
none of which is an external canceller, a housekeeper bug, or a GitHub incident:

1. **Job-timeout kills are reported as `cancelled`**, not `failed` — so a timeout looks like a cancel.
2. **Pending-slot eviction** — GitHub keeps one pending run per concurrency group; a new cron trigger
   evicts the pending one. Cheap, never materialises a runner.
3. **Push-wave stack-kills** — concurrent pushes to `main` cancel in-flight runs at the runner level,
   which is why `cancel-in-progress: false` does not protect them.

They also corrected their own earlier claims: cron-herd `created_at` stamps are not cancel batches, and the
tribunal "12/15 cancelled" figure was a sampling artifact (22/22 green). **Treat my §5 as closed by their
analysis; do not add concurrency guards on account of it.**

## 6. Guardrail gaps that feed the churn

| Gap | Count |
|---|---|
| Workflows with no `concurrency` and/or no job `timeout-minutes` | **204** |
| No `concurrency` block at all | **190 of 356** |
| No `timeout-minutes` anywhere | **80** |
| No `workflow_dispatch` escape hatch | 6 |
| Crons firing at minute 0 | **188 of 359** |

The minute-0 concentration is the queue-hog root cause: 308 scheduled workflows with 188 of them landing on
`:00`. Without a timeout, a job may hold a runner for GitHub's 6h default — that is how ALPHA reached 78
minutes before dying.

## 7. Cross-check of the fleet's own GHA reports

I read the peer deliverables on `origin/main` and re-tested their claims against live data. Results:

| Peer doc | Claim | My live check | Verdict |
|---|---|---|---|
| `2026-11-16_04-05Z_deep-check/DEEP_CHECK.md` | ALPHA fixed by #813, "0 since 01:55Z" | Run `43799911205` failed **at 15 min** at 04:18 | **Superseded** — fixed properly by #829 `safe_push.sh`, not by the timeout bump |
| same | `ml-gatekeeper`/`mysql-q001` "resolved, renamed to `.disabled`" | Both `.yml` absent, both `.yml.disabled` present on `origin/main` | **Confirmed** |
| same | CI Tests red from stale literal-cron assertions after the cron stagger | Matches my CI Tests #3036 03:10 failure | **Confirmed, still open** |
| same | Silent MySQL-sync failure inside a green `alpha-engine-live` run | Not re-tested (log-level; API cannot show warnings cheaply) | **Accepted, unverified here** |
| `2026-11-16_03-02Z_jobstate-sweep` | Duplicate-guard cancellations are "zero-runtime impact (branch-only)" | 7 runs / **198 runner-minutes** cancelled, 15–82 min each | **Corrected** — branch-only, but not free |
| `2026-11-16_02-58Z_alpha-cancellation-analysis` | Two causes: 60-min job cap + 5-min step cap | Third cause found at 04:18: the step **hung** | **Extended** (peer later fixed it) |
| `updates/2026-11-16-ghactions-queue-audit-and-workflow-guards.md` | 51 ghost queued runs, 2026-08-07→11-11 | 21 in two probes, all 2026-11-11 | **Superseded by later state** |
| `2026-11-15_21-00-33_EST/cron_stagger_plan.md` | 189/360 crons at minute 0 | 188/359 | **Confirmed** (one file moved) |
| `2026-11-15_21-00-33_EST/orphan_items.md` | 5 sports workflows `disabled_manually` | 7 disabled total: those 5 + `ai-tournament-pipeline.yml` + `battle_test.yml` | **Confirmed and completed** |
| `2026-11-16_0140Z/01_ghactions_stale_jobs_audit.md` | "ALPHA is a perpetual re-run loop at the 60-min cap" | True at 01:40Z; root cause refined by #813/#829 | **Confirmed then, superseded now** |
| `2026-11-16_03-45Z/VERIFICATION.md` | #813 verified by a post-fix run | That run is the one that failed at 15 min | **Premature verification** |

Two of my own earlier statements were also wrong and are corrected here: `Discord Bot Persistent` is not a
hung job (§2), and the two 0-job "startup failures" are not recurring reds — their workflow files were
renamed out of `main` (§4).

## 8. Still open (ranked, all decision-requiring)

1. **CI Tests — stale literal-cron assertions.** Four tests assert exact minutes (`0 6 * * 1`,
   `0 14 * * 1-5`, `0 7 1 */3 *`) that the crc32 stagger moved by a few minutes, plus a skyrocket test
   asserting a daily cron for a workflow that was already hourly. Fix is to make the assertions
   hour/day-tolerant; **do not revert the stagger**.
2. **Purge the 21 ghost queued runs** — needs the Actions UI or GitHub Support; `gh`/REST return 409.
   Until then no queue-depth reading is trustworthy.
3. **Confirm the first post-#829 ALPHA run** completes its commit step quickly instead of hanging.
4. **Stagger/verify the 188 minute-0 crons** and add `timeout-minutes` to the 80 workflows missing it.
5. **Owner decisions, unchanged:** 5 sports workflows disabled, AsterDEX dead `daily-summary` gate,
   AI Tournament Pipeline disabled since 2026-06-05, QA secrets (PR #786).

## 9. Non-main branches

1,200 runs scanned → **68 on non-main branches** across **213 branches**. Duplicate run groups **0**,
duplicate runs **0**, hazards **0**. Branch verdicts: unmerged_work 199 · merged_or_identical 13 ·
unknown 1. Non-main compute is ~5.7% of runs: branch sprawl is a hygiene cost, not a runner cost, and all
scheduled CI runs on the default branch only.

## 10. Reproduce

```bash
python3 tools/gha_queue_audit.py --pages 25
python3 tools/gha_nonmain_audit.py --pages 12 --compare
python3 tools/gha_queue_and_failure_report.py      # needs reports/gha_run_matrix_2026-11-16.json
```

## Related

- `/audit` dashboard truth-check (panels dead on NaN/Infinity): `updates/2026-11-16-audit-dashboard-live-truth-check.md`
- Strict-JSON publish guard + freshness-banner fix: branch `fix/audit-strict-json-and-freshness-2026-11-16`
  (`38f0fa9084a0`), doc `updates/2026-11-16-audit-strict-json-and-freshness-banner.md`
- Earlier GHA audit by this session: `updates/2026-11-16-gha-actions-audit-and-safe-remediation.md`,
  `updates/2026-11-16-gha-latest-run-deep-check.md`, `GHACTIONS_NONMAIN_BRANCH_RUNS.MD`

## 11. Second sweep — the remaining peer docs

Four more peer docs opened after the first cross-check. None contradicts the data above; three sharpen it.

| Doc | Claim | Cross-check |
|---|---|---|
| `2026-11-15_21-45_EST/04_EXECUTION_VERIFIED_FINDINGS.md` | "Fix batch 1: 9 duplicate/dead workflows removed" (`c2393512637`); 5 sports disabled browser-verified 02:45Z, plus `ai-tournament-pipeline.yml` and `battle_test.yml` | **Confirmed** — exactly the 7 I see `disabled_manually`. It also explains the workflow-count drift (their 367/389 files vs my 360 registered): the 9 removals plus `.disabled`/`.retired` variants. |
| `2026-11-15_21-45_EST/07_AUDIT_DEEP_CHECK.md` | Ghost-rows "22,947 vs 0" contradiction: the **tile is right, the truth banner was wrong** (a hardcoded 2026-05-31 claim); banner reworded | **Closes the item my `/audit` audit raised** (`updates/2026-11-16-audit-dashboard-live-truth-check.md`, DB-health section). The raw count persists by design (quarantine-not-delete). |
| `2026-11-15_21-45_EST/08_FOLLOWUP_RESULTS.md` | "No external canceller: zero cancel/delete API calls repo-wide; guardian is rerun-only" | **Independently supports §5** — the 03:40 burst was mechanical, not a person or a rogue job. |
| `2026-11-15_20-57_EST/GHA_TRIAGE_ANALYSIS.md` | The 51 phantom runs are **deletable with an admin-scoped token** (`403 Could not delete` on a normal token); 20 never-run active files are abandoned drafts, `rl-agent-ppo` has `if: false` | **Refines §8.2** — purging is possible without Support, it just needs Actions-administration scope. The 20 never-run drafts are a separate, cheap cleanup. |

**No peer recommendation in any of the 14 docs reviewed conflicts with live data.** Workflow names appearing in
delete/disable advice are either already removed, already `.disabled`, or explicitly gated on an owner
decision (sports five, AsterDEX gate, AI Tournament, QA secrets).
