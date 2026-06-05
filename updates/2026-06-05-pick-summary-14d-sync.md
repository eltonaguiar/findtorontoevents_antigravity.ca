# pick_summary_stats_14d.json sync (live 404 fix)

**Date:** 2026-06-05

## Problem

`/audit/data/pick_summary_stats_14d.json` returned **404** on production.

## Solution

`sync_pick_summary_14d.py` copies `pick_summary_stats_2w.json` with `alias_of` metadata; hourly `build_recency_summary.py` invokes it after each run.