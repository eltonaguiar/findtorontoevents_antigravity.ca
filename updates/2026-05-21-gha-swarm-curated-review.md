# 2026-05-21 - GitHub Actions Curated Log Review Script

## What Was Requested

Build a runnable script that:

- Reviews recent runs across unique GitHub Actions workflows/jobs.
- Pulls logs and extracts real error/warning lines.
- Produces a curated list of job runs with links and diagnostics.
- Uses tools/swarm_v2 for AI-assisted curation when API keys are available.
- Attempts to hydrate keys from .env sources (including FTP-hosted .env when credentials exist).

## What Was Added

New script:

- tools/gha_swarm_curated_review.py

Core behavior:

1. Discovers unique workflows from recent run history.
2. Pulls recent runs per workflow (`gh run list`).
3. Pulls per-run jobs (`gh api repos/{repo}/actions/runs/{run_id}/jobs`).
4. Pulls per-job logs (`gh run view --job <job_id> --log`).
5. Extracts and de-noises error/warning signals.
6. Outputs ranked findings with direct run/job links.
7. Optionally uses `tools/swarm_v2` LLMClient for curated triage text.
8. Optionally loads env vars from:
   - local `.env`
   - FTP `.env` candidates via `FTP_SERVER/FTP_USER/FTP_PASS`.

## Output

Default output file:

- docs/GHA_SWARM_CURATED_REVIEW.md

Test output files generated during validation:

- docs/GHA_SWARM_CURATED_REVIEW_TEST.md
- docs/GHA_SWARM_CURATED_REVIEW_FTP_TEST.md

## Verification Performed

1. Syntax validation:

```bash
python3 -m py_compile tools/gha_swarm_curated_review.py
```

Passed.

2. Small-scope runtime test:

```bash
python3 tools/gha_swarm_curated_review.py --since-days 2 --max-workflows 2 --runs-per-workflow 1 --out docs/GHA_SWARM_CURATED_REVIEW_TEST.md --skip-ftp-env
```

Passed and generated report.

3. Broader runtime scan:

```bash
python3 tools/gha_swarm_curated_review.py --since-days 14 --max-workflows 12 --runs-per-workflow 2 --out docs/GHA_SWARM_CURATED_REVIEW_TEST.md --skip-ftp-env
```

Passed and generated non-zero findings.

4. FTP hydration path smoke check:

```bash
python3 tools/gha_swarm_curated_review.py --since-days 1 --max-workflows 1 --runs-per-workflow 1 --out docs/GHA_SWARM_CURATED_REVIEW_FTP_TEST.md
```

Passed. In this environment, no FTP `.env` source was loaded (no usable FTP credentials/path available at runtime).

## Notes

- The existing `tools/swarm_v2` GitHub Actions orchestrator currently uses mocked run data. This script uses real `gh` data for runs/jobs/logs and only uses `swarm_v2` for optional AI curation.
- Signal extraction rules were iterated to suppress common false positives (command echo noise, ANSI command traces, and benign test pass lines).