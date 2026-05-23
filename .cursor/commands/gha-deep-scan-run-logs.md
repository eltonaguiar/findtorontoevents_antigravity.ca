# GitHub Actions — deep scan run logs

You are checking **GitHub Actions** for this repository using the **latest run per workflow** plus the **previous run only when the latest completed without success** (failure, cancelled, timed out, etc.). Goal: surface critical log lines (errors, missing symbols/quotes, git conflicts, stale payloads, API451/403/404, tracebacks) and write the merged report.

## Prerequisites

- Shell at repo root: `e:\findtorontoevents_antigravity.ca` (or the user’s clone path).
- `gh` installed and authenticated (`gh auth status`).
- Python available as `python` (Windows) or `python3`.

## Run the scanner

**Option A — single process (simplest)**

```powershell
Set-Location e:\findtorontoevents_antigravity.ca
python tools/gha_latest_prior_log_scan.py --out docs/GHA_DEEP_SCAN_LATEST_PRIOR.md
```

**Option B — parallel shards (faster when many workflows), then merge**

```powershell
Set-Location e:\findtorontoevents_antigravity.ca
python tools/gha_latest_prior_log_scan.py --shards 2 --shard 0 --out docs/GHA_DEEP_SCAN_LATEST_PRIOR_part0.md --max-workflows 80 --hours 24
python tools/gha_latest_prior_log_scan.py --shards 2 --shard 1 --out docs/GHA_DEEP_SCAN_LATEST_PRIOR_part1.md --max-workflows 80 --hours 24
python tools/gha_merge_deep_scan_parts.py
```

Tune: `--hours`, `--max-workflows`, `--branch main`, `--repo owner/name`. For one workflow only: `--workflow "Unified Audit Dashboard"`.

## After the run

1. Read `docs/GHA_DEEP_SCAN_LATEST_PRIOR.md` and give a short **human summary**: worst regressions, data/symbol issues, git/push failures, cancelled churn.
2. Note if many rows are `in_progress` / `pending` (noisy); suggest re-running when the queue is calmer.
3. **Do not** invent fixes unless the user asks. **Do not** commit or push unless the user explicitly asks to save the report to git.

## Reference

- Implementation: `tools/gha_latest_prior_log_scan.py`, `tools/gha_merge_deep_scan_parts.py`
- Related skill: `.cursor/skills/gha-run-log-deep-scan/SKILL.md`
