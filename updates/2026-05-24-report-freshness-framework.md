# Report Regeneration Framework — 2026-05-24

## Problem

Multiple audit reports were stale (11-74 days old) with no systematic way to detect or regenerate them:

| Report | Location | Age | Generator |
|--------|----------|-----|-----------|
| `health_report.json` | `audit_dashboard/data/` | 34d (Apr 20) | `tools/audit_data_health_pipeline.py` |
| `qa_report.json` | `audit_dashboard/data/` | 74d (Mar 11) | `audit_dashboard/database_consolidation.py` |
| `edge_decay_heatmap.json` | `audit_dashboard/data/` | 11d (May 13) | `tools/edge_decay_heatmap.py` |
| `hourly_asset_class_24h_report.json` | `audit_dashboard/data/` | 43d (Apr 11) | None (drift system, JS/PS1) |
| `hf_quality_report.json` | `audit_trail/data/` | 47d (Apr 7) | `audit_trail/hf_pick_validator.py` |
| `system_concentration.json` | `audit_trail/data/` | 7d (May 17, empty) | Inline in `dashboard_generator.py` (M-004) |

Root causes:
- **No scheduled workflow** for `qa_report.json` (database_consolidation.py runs only as part of the hourly audit-dashboard pipeline)
- **No scheduled workflow** for `hf_quality_report.json` (hf_pick_validator.py has no dedicated cron)
- **`hourly_asset_class_24h_report.json`** has no Python generator — it is produced by the drift system (JS/PowerShell), not tracked by any workflow
- **`system_concentration.json`** is written inline by `dashboard_generator.py` as a side-effect of the M-004 module; it was empty because the dashboard had no CRYPTO picks with concentration data at generation time
- **No freshness monitoring** — stale reports were only discovered through manual inspection

## What Changed

### 1. `tools/regenerate_stale_reports.py`

Central registry + staleness detector for audit reports:

- **Registry** maps each known report file to its generator script, default freshness threshold, and scan directories
- **`--dry-run`** (default): scans all registered reports, classifies as FRESH/STALE/NOT_FOUND, prints summary
- **`--execute`**: runs the generator for each stale report, captures stdout/stderr
- **`--threshold-days N`**: override default per-report thresholds
- **`--only <filename>`**: target a single report
- **`--json-output <path>`**: write findings as JSON

Usage:
```bash
# See what's stale
python -m tools.regenerate_stale_reports

# Regenerate only health_report
python -m tools.regenerate_stale_reports --only health_report.json --execute

# Tighten threshold to 3 days
python -m tools.regenerate_stale_reports --threshold-days 3

# Write results to JSON
python -m tools.regenerate_stale_reports --json-output reports/stale_check.json
```

### 2. `tools/report_freshness_tracker.py`

Broad freshness scanner for all audit JSON files:

- Scans `audit_dashboard/data/` and `audit_trail/data/` (recurses into subdirs, skips `ai_leaderboard/`, `edge_stability/`, `money_ready_archive/`, `research/`)
- Extracts `generated_at` / `generated_at_utc` / `timestamp` / `snapshot_ts` timestamps
- Classifies: **GREEN** (<24h), **YELLOW** (<7d), **RED** (>=7d)
- Writes `reports/report_freshness_YYYY-MM-DD.json`
- Returns exit code 1 if any RED files found (CI-friendly)

Usage:
```bash
# Full scan with defaults
python -m tools.report_freshness_tracker

# Tighter thresholds
python -m tools.report_freshness_tracker --green-hours 12 --yellow-days 3

# Scan only audit_trail
python -m tools.report_freshness_tracker --scan-dir audit_trail/data

# Quiet mode (JSON only)
python -m tools.report_freshness_tracker --quiet
```

### 3. `tools/test_report_freshness.py`

39 unit tests covering:
- Timestamp extraction (ISO, Z-suffix, Unix timestamps, missing/invalid)
- Age calculations (exact, negative clamping, large values)
- Freshness classification (GREEN/YELLOW/RED boundaries, custom thresholds)
- Registry integrity (all entries have scan_dirs, freshness_days, known reports present)
- End-to-end staleness detection with temp files
- Freshness tracker scanning (classification, tiny file skipping, ignored subdir skipping, output writing)
- Edge cases (invalid JSON, missing files, nested timestamps, boundary values)

Run: `python3 -m pytest tools/test_report_freshness.py -v`

## Findings

Running `report_freshness_tracker.py` against the actual repo reveals:
- **health_report.json** (34d RED) — generator exists, not run independently
- **qa_report.json** (74d RED) — generator exists, only runs as part of hourly pipeline
- **edge_decay_heatmap.json** (11d YELLOW) — has dedicated cron (`edge-decay-check.yml`, weekdays 07:20 UTC)
- **hourly_asset_class_24h_report.json** (43d RED) — **no Python generator**, drift system artifact
- **hf_quality_report.json** (47d RED) — generator exists, no dedicated cron
- **system_concentration.json** (7d, empty) — inline side-effect of dashboard_generator

## Recommended Follow-up

1. **Add `hf_quality_report.json` to a scheduled workflow** — either the hourly `audit-dashboard.yml` or a new weekly cron
2. **Ensure `qa_report.json` runs per-schedule** — the hourly pipeline runs `database_consolidation.py` but the QA report section may be gated or skipped
3. **Document `hourly_asset_class_24h_report.json` ownership** — if the drift system is deprecated, remove from registry; if still needed, add a regeneration step to the appropriate workflow
4. **Add freshness check to CI** — run `report_freshness_tracker.py` in a cron and alert on RED count growth
5. **Consider running `regenerate_stale_reports.py --execute`** to regenerate all stale reports now that the framework exists

## Files Changed

- `tools/regenerate_stale_reports.py` — NEW (400 lines)
- `tools/report_freshness_tracker.py` — NEW (323 lines)
- `tools/test_report_freshness.py` — NEW (481 lines)
- `updates/2026-05-24-report-freshness-framework.md` — NEW (this file)

## Test Results

```
39 passed in 0.10s
```

All tests pass — timestamp extraction, age calculations, freshness classification, registry integrity, staleness detection, freshness tracker scanning, and edge cases.
