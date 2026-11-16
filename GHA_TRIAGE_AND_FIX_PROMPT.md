# GHA Triage & Fix Prompt — eltonaguiar/findtorontoevents_antigravity.ca

## Mission
Analyze all GitHub Actions workflows in the repo, classify into 4 buckets, fix broken/stale/queue-hog workflows, verify subsequent runs are clean.

## Context (already done — do not redo)
- **Commit `3d1aa94ba5e`** (pushed to main): renamed `ml-gatekeeper-ab-bootstrap.yml` and `mysql-q001-sync.yml` to `.disabled` (they had invalid `on: {}`)
- **Commit `c2393512637`** (pushed): removed 9 duplicate/dead workflows (Fix Batch 1)
- **Commit `d239770ca37`** (pushed): hardened finpredict emitter downloads; bumped alpha engine job timeout
- **Commit `a174e2d00c2`** (pushed): serialized branch-large-file-dup-guard concurrency (per-branch scope)
- Local analysis folders exist: `GHACTIONS_2026-11-16/`, `GHACTIONS_PR_ISSUES/` — NOT on remote

## Method: Get Live GHA Data via Chrome CDP
A Chrome browser is running with remote debugging on port 9222, logged into GitHub, viewing the Actions page. Use CDP over WebSocket to extract workflow run data:

1. List tabs: `GET http://localhost:9222/json/list` → find the page with `url` containing `github.com/.../actions`
2. Connect WS to that page's `webSocketDebuggerUrl`
3. Enable Runtime, Network, Page domains
4. Navigate to `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions`
5. Wait ~8s, then extract `document.documentElement.outerHTML`
6. Parse the embedded `workflowRuns` JSON array from the HTML:
   - Find `"workflowRuns":[` then match brackets to extract the full array
   - Each run has: `name`, `runNumber`, `id`, `workflowFilePath`, `state.status`, `state.conclusion`, `createdAt.timestamp`

## Classification (Worst-Bucket-Wins)

### Bucket 1 — BROKEN NOW (failed, NO subsequent success)
For each workflow, pull per-workflow history (~15-50 runs deep). A workflow is Bucket 1 if:
- Latest completed run conclusion = `failure`/`timed_out`/`startup_failure`/`stale`
- Zero successes after that failure

**Action:** List these with workflow name, last failure time, failing step, run URL. Fix each one.

### Bucket 2 — RECOVERED (failure followed by later success)
Count only, do not list. Suppress as "not an issue."

### Bucket 3 — QUEUE HOGS
- **Phantom queued runs:** status `queued` forever, 0 jobs materialized (uncancelable, undeletable)
- **Runner hogs:** `in_progress` > several hours, occupying a hosted runner 24/7
- **Cancel churn:** >50% of last 15 runs cancelled

### Bucket 4 — STALE / NEVER-RUN
- No run in > expected cadence
- Check `on:` triggers first — `workflow_dispatch` manual-only is NOT stale
- `.disabled`/`.retired` files are intentionally inert

## Known Remaining Items to Check/Fix

1. **DB Secret Scan** (`.github/workflows/secret-scan.yml`) — dead since 2026-06-05, never passed. Needs `.disabled` rename like the two already fixed.
2. **Fast Stocks Competition High Frequency Scanner** (`fast-stocks-competition.yml`) — cron `0 14,18 * * 1-5` but zero runs ever. Investigate trigger/filename mismatch.
3. **Discord Bot – Persistent** (`discord-bot.yml`) — occupies hosted runner 24/7, no concurrency group, duplicate runs stack `pending` behind it. Add concurrency group + decide if persistent bot belongs on hosted runners.
4. **Model Picks Emission** (`model-picks-emission.yml`) — was failing on GLD download (database locked). Commit `d239770ca37` claims to fix this — verify subsequent runs are clean.
5. **ALPHA ENGINE Dynamic Runner** — was hitting 60-min timeout. Commit `d239770ca37` bumps timeout — verify subsequent runs complete.

## Fix Pattern for Disabling a Workflow
```bash
git mv .github/workflows/<name>.yml .github/workflows/<name>.yml.disabled
git commit -m "fix(ci): disable <workflow name> — <reason>"
git push origin HEAD:main
```

## Revert Pattern
```bash
git mv .github/workflows/<name>.yml.disabled .github/workflows/<name>.yml
# Restore proper on: triggers, commit, push
```

## Documentation Rule (MANDATORY)
Every fix must be documented in `updates/YYYY-MM-DD-<descriptive-name>.md` describing:
- What was broken
- What changed
- How it was verified (subsequent run inspection)

## Output
Produce a `TRIAGE_REPORT.md` with:
1. Bucket 1 list (broken, no subsequent success) — with fixes applied
2. Bucket 2 count (recovered) — informational only
3. Bucket 3 list (queue hogs) — with fixes applied or escalation notes
4. Bucket 4 list (stale/never-run) — with actions taken
5. Verification results (subsequent runs clean?)

## Verification
After each fix, wait for the next scheduled run (or manually dispatch) and confirm the workflow completes successfully. Confirm no new Bucket 1 failures appear.
