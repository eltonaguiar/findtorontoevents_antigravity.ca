# Mixed-worktree hazard in `audit_trail/dashboard_generator.py` (2026-11-24)

## The hazard

This workspace is a shared worktree. On 2026-11-24 `audit_trail/dashboard_generator.py`
held **two unrelated sets of uncommitted edits at once**:

1. **Mine** (this session): `from audit_trail.excluded_cohorts import coverage_excluded_summary`
   at the import block, and a `coverage.excluded_summary` block in the payload literal.
2. **Someone else's** (dated 2026-11-23): removal of `funding_rate_arb` and
   `btc_breakout` from `_GHOST_SYSTEMS`, plus new `_FRESHNESS_REQUIRED_HOURS`
   entries for both. Those edits carry their own explanatory comments naming the
   H-254 and H-256 forward arms.

`git add audit_trail/dashboard_generator.py` would have committed both.

## What was done

- The two safe files (`audit_trail/excluded_cohorts.py`,
  `tools/excluded_cohorts_report.py`) were committed on branch
  `coverage-and-verdict-tooling-2026-11-24` as commit `39d59f9`.
- `dashboard_generator.py` was **deliberately left uncommitted**, per the
  workspace rule "NEVER `git push` commits that include files you didn't create
  or modify."

## Consequence for the next agent

The `coverage.excluded_summary` payload block is **on disk but not in the
commit**. `tests/test_dashboard_coverage_wiring.py` reads the working tree, so it
passes locally, but a fresh checkout of `39d59f9` would not have the block.

To finish it, separate the hunks:

```bash
# Show only the import and payload hunks
git diff -U0 -- audit_trail/dashboard_generator.py | grep -n "coverage_excluded_summary"
# Stage interactively, taking only those hunks
git add -p audit_trail/dashboard_generator.py
```

Do not use `git add audit_trail/dashboard_generator.py` (whole file) until the
other author's edits are committed or stashed by their owner.

## Detection recipe

Before staging any file in a shared worktree, confirm the diff is yours:

```bash
git diff -- <file> | head -60
```

If any hunk mentions a date, arm or subsystem you did not touch, stop.
