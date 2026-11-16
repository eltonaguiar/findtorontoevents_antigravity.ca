# Agent Prompt — GH Actions repair pass (copy-paste)

Hand this to any agent working this repo. It is self-contained: it assumes no memory of prior runs.

---

```text
You are repairing GitHub Actions health on eltonaguiar/findtorontoevents_antigravity.ca
(local checkout: E:/findtorontoevents_antigravity.ca, remote name `antigravity`, default branch `main`).

HARD RULES
1. A run's conclusion is only meaningful in SEQUENCE CONTEXT. Never report a failure list.
   Pull per-workflow history (last 15-50 runs) and classify into exactly one bucket, worst wins.
2. Read `.github/workflows/*.yml` LOCALLY for triggers before calling anything stale.
   `workflow_dispatch`-only workflows are manual by design — flagging them is the #1 false positive.
3. A cancelled run is NOT a failure. A run with `jobs_executed = 0` never started.
4. Never force-push. Bots commit to main every ~60s, so pushes are non-fast-forward: loop
   `git fetch antigravity main; git merge antigravity/main; git push` and VERIFY with
   `git merge-base --is-ancestor <sha> antigravity/main`. Never trust the text of `git push`.
5. Land workflow changes as a PR from a worktree branch, then merge — cron only takes effect
   from the default branch. Rebase is unsafe here (case-insensitive `.claude/skills` collision);
   use merge.
6. Do not `git add -A`. The tree carries 80+ dirty files from other agents. Stage exact paths.

BUCKETS (classify every workflow once, worst-bucket-wins)

 1. BROKEN NOW — latest completed run is failure/timed_out AND zero successes after it.
    EXCEPTION: if a run is still in flight (status in_progress/queued, conclusion null, run_attempt>1),
    it is a live RETRY, not broken. Verify with GET /actions/runs/{id} before calling it dead.
    Severity by cadence: 15-min cron failing 3h = P1 (3+ missed cycles); monthly = P2.
    If it NEVER passed in its whole history AND has no run in >30d, it is dead weight → bucket 4, one line.

 2. RECOVERED / FLAPPING — a success exists after the last failure. NOT an issue; report a count only.
    Flapper = >=5 failures in last 15 runs yet currently green. Sub-classify infra flake
    (Playwright/deps/network install) vs real bug (a gating test step).

 3. QUEUE HOGS — three patterns, check all three:
    a) ZOMBIE QUEUED: status=queued and age > ~1 day with ZERO materialized jobs.
    b) RUNNER HOGS: in_progress for hours — decide "legit long job" vs "stuck", don't assume bug.
    c) CANCEL CHURN: cancelled/total > 50% in wf-history = the concurrency group eats its own runs.

 4. STALE / PRUNE — no run beyond expected cadence, checked against the workflow's OWN `on:` triggers.
    Cron: stale if now - last > max(3 x interval, 48h). Manual-only: never stale.

FACTS ALREADY ESTABLISHED — do not re-derive, do not contradict without new evidence
- 190 failures in a 24h window had a later success. They are noise. Suppressing them is the whole point.
- 7 workflows are `disabled_manually` and ALL are sports/ai-tournament. The owner chose to disable
  sports betting. They are NOT stale, NOT broken, and must NOT be re-enabled without asking.
- 28 workflow files are `workflow_dispatch`-only. Never flag them.
- Zero BROKEN-NOW workflows as of 2026-11-15 20:42 EST.
- Fixed and merged: PR #814 — `audit-dashboard.yml` `10 * * * *`→`10 */3 * * *` (runtime 63-125min vs
  60min cron) and `dynamic-alpha-engine.yml` `18,48 * * * *`→`23 */2 * * *` (runtime 77-80min vs 30min).
  Root cause: GitHub keeps ONE pending run per scheduled workflow, so each fire arriving during a live
  run replaced the pending one (cancelled, jobs_executed=0). `cancel-in-progress: false` does NOT protect
  scheduled triggers — only widening the interval works. Do not "fix" this by adding cancel-in-progress.
- 29 phantom queued runs were purged via DELETE /actions/runs/{id} (works with a `repo`+`workflow` PAT).
  **21 remain that are unrecoverable by API**: cancel → 409 "has not been queued yet" (status still reads
  `queued`), delete → 403 "Could not delete the workflow run", already retried with 1.2s pacing.
  These need a GitHub Support ticket. Do not waste calls retrying them.
- Bulk cancellations at identical timestamps across unrelated workflows are EXTERNAL (cleanup/incidents),
  not concurrency self-cancels. Do not edit those configs.
- Unauthenticated REST is 60 req/hr shared across all agents on this host. Check /rate_limit FIRST and
  report RATE_LIMITED rather than an empty green result. Prefer local YAML over API for trigger facts.
  The `gh` CLI keyring token is dead — use `git credential fill` to obtain the working PAT.

DELIVERABLE
- Write findings to `GHACTIONS_<YYYY-MM-DD>/<YYYY-MM-DD>_HH-MM_EST_<slug>/` on main, committed and verified
  on the remote (report the sha and prove ancestry).
- For every fix: a branch from antigravity/main, a PR, verify the merged content on main, and a revert
  command in the PR body.
- State explicitly which buckets are EMPTY. "0 broken, 190 recovered suppressed" is a finding;
  a list of 190 failures is not.
- Mark every claim UNVERIFIED if it came from a pattern rather than a measurement. Never assert a
  workflow is dead from a 1-day window — say the window is too thin and name what would settle it.
```

---

## Why each rule exists (evidence trail)

| Rule | What it prevents |
|---|---|
| Sequence context | A 24h window on this repo hits ~1,000 runs; 190 of them are failures that later succeeded. Reported raw, that is 190 fake issues. |
| Local YAML for triggers | 28 manual-only workflows look abandoned until you read `on:`. |
| In-flight ≠ broken | `Model Picks Emission` had `conclusion: null, run_attempt: 2` — a live retry that was misclassified as a P0 in an earlier pass. |
| Cancelled ≠ failed | The repo's historical "97-98% failure" alarm was concurrency-slot replacement with `jobs_executed=0`, not code failures. |
| Loop + ancestry check | A previous push was reported "PUSH OK" by grepping output while the commit was not on the remote. |
| PR then merge | Cron is read from the default branch only; a fix sitting on a branch changes nothing. |
