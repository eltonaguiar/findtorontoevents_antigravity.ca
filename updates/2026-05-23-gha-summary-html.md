# GitHub Actions High-Level Summary HTML Dashboard

**Date:** 2026-05-23  
**Live URL:** https://findtorontoevents.ca/updates/gha-summary.html

## What was built

A fleet-wide GitHub Actions health dashboard that:

- Lists **every workflow** in the repo (via `gh api …/actions/workflows`)
- Shows **latest run + prior 2 runs** per workflow on `main`
- Highlights **in-progress / queued / waiting** runs
- Flags **unresolved failures** (latest completed run is `failure`, `timed_out`, `startup_failure`, `stale`, or `action_required` with no newer run)
- Flags **chronic cancellation** (same thresholds as `workflow_health_check.py`: 15-run window, ≥4 cancelled, 0 success, no success in 48h+)
- Scans logs on **latest completed (non-success)** and **in-progress** runs for `error` / `warning` line counts, critical signal regexes, and failure classification

## Files

| File | Role |
|------|------|
| `tools/gha_summary_lib.py` | Shared collection: workflows, runs, chronic/unresolved, log scan |
| `tools/generate_gha_summary_html.py` | CLI → `reports/gha_actions_summary.json` + `.html` |
| `tools/deploy_gha_summary.py` | FTP upload to `/findtorontoevents.ca/updates/gha-summary.html` |
| `.github/workflows/gha-summary-report.yml` | Every 6h + manual: generate, commit `[skip ci]`, deploy |
| `reports/gha_actions_summary.json` | Machine-readable payload |
| `reports/gha_actions_summary.html` | Self-contained dark-theme dashboard |

## Regenerate locally

```bash
# Smoke test (5 workflows)
python3 tools/generate_gha_summary_html.py --max-workflows 5

# Full fleet (~200 workflows; 15–45 min depending on log scans)
python3 tools/generate_gha_summary_html.py --max-workers 8

# Metadata only (no log fetch)
python3 tools/generate_gha_summary_html.py --skip-logs

# Deploy after generation
export FTP_SERVER=... FTP_USER=... FTP_PASS=...
python3 tools/deploy_gha_summary.py
```

Requires `gh auth login` and repo read access.

## Sharding (if CI times out)

```bash
python3 tools/generate_gha_summary_html.py --shard 0 --shards 4 --shard-json reports/shard0.json
# … repeat for shards 1–3 …
python3 tools/generate_gha_summary_html.py --merge-shards reports/shard0.json reports/shard1.json reports/shard2.json reports/shard3.json
```

## Definitions (aligned with fix-gh-actions)

- **Unresolved failure:** Latest *completed* run on `main` for that workflow has a bad conclusion and no newer run exists in the bulk scan.
- **Chronic cancelled:** Latest completed = `cancelled`, ≥4 cancellations in last 15 runs on `main`, 0 successes in that window, no success within 48h in scanned history.
- **Log scan:** `gh run view --log-failed`, then tail of full `--log`; counts lines matching `\berror\b` and `\bwarning\b`; classifies via `gha_health_monitor_cursor.py` heuristics.

## Verification

- `python3 -m py_compile tools/gha_summary_lib.py tools/generate_gha_summary_html.py tools/deploy_gha_summary.py` → exit 0
- `python3 tools/generate_gha_summary_html.py --max-workflows 5` → writes JSON + HTML
- Open `reports/gha_actions_summary.html` in browser; filter chips and tables populate
- After deploy: `curl -sI https://findtorontoevents.ca/updates/gha-summary.html` → HTTP 200

## Notes

- Reuses fresh `reports/actions_failure_guardian.json` (&lt;90 min) for unresolved/chronic/stale hints when available.
- Full fleet log scans are rate-limit sensitive; the generator retries on 403/429 with backoff.
- Read-only dashboard; reruns remain the job of `scripts/actions_failure_guardian.py`.
