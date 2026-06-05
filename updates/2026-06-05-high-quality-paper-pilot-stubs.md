# ENH #119 — High-quality picks → paper-pilot stubs

**Date:** 2026-06-05

## Problem

`reports/high_quality_picks_plan_2026-06-05.md` planned 4-week forward tracking but no `verified_strategies/paper_pilot/high_quality_2026-06-05/` state files existed.

## Solution

`tools/promote_high_quality_to_paper_pilot.py` applies the same 3-stage filter as `mlflow_high_quality_picks.py` (persona_id + bias scrutiny + symbol WR≥60%, n≥5) and writes JSON state stubs. **No DB writes.**

## Usage

```bash
python3 tools/promote_high_quality_to_paper_pilot.py --top 12
```

Resolve **INCIDENT #97** (SHY LONG vs SHORT) before any sizing.