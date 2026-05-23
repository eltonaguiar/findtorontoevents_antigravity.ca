---
description: EXHAUSTIVE curated review of GitHub Actions job logs — walks every workflow's latest run (plus prior runs when the latest is in-progress) and produces a full triage report. Slower than the standard variant.
argument-hint: [--since-days N] [--runs-per-workflow N] [--strict]
---

User invoked `/swarm-gh_actions-log-review-thorough $ARGUMENTS`.

## What this command does

The **thorough** variant of `/swarm-gh_actions-log-review`. Where the standard command samples ~40 workflows × 3 runs over 7 days, this command:

1. Discovers **every workflow that has run on `main` in the last 30 days** (list-limit 1000 to ensure no workflow is dropped from the recency window).
2. Caps at **200 workflows** so very large repos don't blow up.
3. Pulls **5 runs per workflow** — this guarantees the latest run + at least 4 prior runs are inspected. If the latest run is **in progress / partway** (status `in_progress`, `queued`, `waiting`, etc.) with no extractable failure signal yet, the prior runs provide the most recent completed signal for that job.
4. Same per-job log fetch, noise filter, error/warning extraction, severity ranking, and optional swarm_v2 LLM curation as the standard variant.
5. Writes the report to `docs/GHA_SWARM_CURATED_REVIEW_THOROUGH.md` (separate file so the standard report isn't clobbered).

Expect this to take **5–15 minutes** depending on workflow count and log size — every job log is downloaded via `gh run view --log`.

## Run

```bash
python3 tools/gha_swarm_curated_review.py \
  --since-days 30 \
  --list-limit 1000 \
  --max-workflows 200 \
  --runs-per-workflow 5 \
  --out docs/GHA_SWARM_CURATED_REVIEW_THOROUGH.md \
  --skip-ftp-env \
  $ARGUMENTS

Use `--strict` to only report jobs whose conclusion was `failure`, `cancelled`, or `timed_out` (drops successful runs with warnings — reduces noise on large repos).
```

## After the script completes

1. Read `docs/GHA_SWARM_CURATED_REVIEW_THOROUGH.md`.
2. Build a **per-workflow status matrix** for the user. For each workflow:
   - Latest run conclusion (success / failure / cancelled / in_progress).
   - If latest is `in_progress` or missing signals, state the **last completed run's** conclusion + a one-line excerpt of its top error.
   - Severity rank from the report.
3. Group findings into three buckets and present them as a brief markdown report in the chat:
   - **CHRONIC** — workflows where 3+ of the last 5 runs failed (these are the priority).
   - **NEW REGRESSION** — workflows where the latest run failed but the previous 2 succeeded.
   - **FLAKY** — workflows where failures and successes alternate.
4. Cross-reference any chronic failures against the project's `MAJOR GOALS` (in `CLAUDE.md`). Flag whether a broken workflow is blocking Goal #1 (audit dashboard / asset-class performance), Goal #2 (sports picks pipeline — note: `sports-smoke-and-e2e.yml` is critical here), or Goal #3 (events listing / scrapers).
5. If `$ARGUMENTS` contains `--fix`, generate concrete proposed diffs for the top 3 chronic failures — do not auto-commit, show diffs and ask before applying.

## Notes

- Writes to a **separate** output file from the standard variant so you can diff the two reports.
- The 5-runs-per-workflow setting is what handles "latest is partway" — `gh run list` returns most-recent-first, so the prior 4 runs are guaranteed to be inspected.
- If you want even deeper history for a specific suspect workflow, run it manually: `gh run list -w "<workflow name>" --limit 20 --json databaseId,conclusion,createdAt`.
- Requires `gh` CLI authenticated against the repo.
