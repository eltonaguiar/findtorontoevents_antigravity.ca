---
description: Curated review of recent GitHub Actions job logs — pulls failures/warnings from the last 7 days across the most recent workflows and writes a triage-ready markdown report.
argument-hint: [--since-days N] [--max-workflows N] [--runs-per-workflow N] [--strict]
---

User invoked `/swarm-gh_actions-log-review $ARGUMENTS`.

## What this command does

Runs `tools/gha_swarm_curated_review.py` with **standard breadth** settings, which:

1. Discovers every workflow that produced a run on `main` in the last 7 days.
2. For each workflow, pulls the most recent 3 runs and inspects every job.
3. Downloads job logs via `gh run view --log`, strips noise, and extracts error + warning signal lines.
4. Ranks jobs by severity (failure/timeout > cancelled, error count weighted 3×, warning count weighted 1×).
5. If `swarm_v2/swarms/core/llm_client.py` is importable and an API key is in the env, has an LLM curate the top 25 findings into 4 sections (Top Failing Jobs, Repeated Error Themes, High-Noise Warnings to Deprioritize, Quick Fix Queue).
6. Writes the report to `docs/GHA_SWARM_CURATED_REVIEW.md`.

This is the **standard** depth. For exhaustive coverage of every workflow (including stale ones and prior runs when the latest is in-progress), use `/swarm-gh_actions-log-review-thorough` instead.

## Run

```bash
python3 tools/gha_swarm_curated_review.py \
  --since-days 7 \
  --max-workflows 40 \
  --runs-per-workflow 3 \
  --skip-ftp-env \
  $ARGUMENTS

Use `--strict` to only report jobs whose conclusion was `failure`, `cancelled`, or `timed_out` (drops successful runs with warnings — reduces noise).
```

After the script completes:

1. Read `docs/GHA_SWARM_CURATED_REVIEW.md` and summarize the **top 5 failing jobs** for the user, each with: workflow name, job name, run URL, and a one-line root-cause guess based on the extracted error excerpts.
2. Flag any workflow appearing **3+ times** in the top findings — that signals a chronic failure, not a transient one.
3. If the user passes `--fix` in `$ARGUMENTS`, also propose concrete fixes (file paths + diffs) for the top 3 issues. Do not auto-commit; show the diff and ask.

## Notes

- Aliased by `/swarm-actions-log-review` (same behavior).
- Requires `gh` CLI authenticated against the repo.
- Output path is `docs/GHA_SWARM_CURATED_REVIEW.md` (overwrites on each run).
- The `--skip-ftp-env` flag prevents the script from trying to pull `.env` from FTP, which is slow and usually unnecessary when AI keys are already in the local env.
