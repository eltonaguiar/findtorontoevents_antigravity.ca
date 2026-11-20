# Demoting the 74 DSR failures to PROBATION as a label, not a deletion (2026-11-20)

## The situation the gate reported

`tools/anti_overfit_audit_sidecar.py` writes `audit_dashboard/data/anti_overfit_audit.json`.
At the 2026-11-20T01:09Z snapshot it held **80 strategies, 6 above DSR 0.95 and 74 below**.
The gate fails on that, correctly: the gate is supposed to fail when 74 of 80 strategies
have not survived a multiple-testing correction.

What the payload did not carry was a *publication* consequence. Every row looked the same
shape, so nothing downstream could tell a strategy that had cleared the floor from one that
had not, short of re-deriving the comparison itself.

## What changed

**Labels are added; rows are not touched.**

| Field | Meaning |
|---|---|
| `publication_label` | `PUBLISHABLE` (DSR >= 0.95), `PROBATION` (DSR < 0.95), `UNRATED` (no DSR) |
| `publication_reason` | the arithmetic, e.g. `DSR 0.2071 < 0.95` |
| `publication_dsr_threshold` | the floor used, so a later change of threshold is visible |
| `publication_label_counts` | payload-level totals |

Two places write them, so neither a regeneration nor a re-label can lose the demotion:

- `tools/anti_overfit_audit_sidecar.py` — `publication_label()` is applied to every row at
  construction time and the counts are emitted in the payload.
- `tools/apply_dsr_probation_labels.py` — new standalone tool that stamps the same labels
  onto an existing payload without touching the database. Dry run by default, `--apply`
  writes, timestamped `.bak` kept.

The tool refuses to write if the row count or the `n` column changed (`return 3`). That
guard exists because "demote 74 strategies" is exactly the request where a helpful-looking
filter would be a bug: a demoted strategy must stay visible, with its sample size, or the
gate's own output stops being auditable.

## Verified

- `rows=80 (unchanged)`, `7 PUBLISHABLE`-family counts as expected, `PROBATION 74`.
- Re-running is idempotent: the second pass writes identical labels.
- The safety guard was exercised by asserting row count and `n` list equality before/after
  (the code returns 3 rather than writing if they differ).
- Every row keeps `n`, `pf`, `wr_pct`, `sharpe`, `dsr`, `verdict`.

## What this does *not* do

- It does not filter, block or hide anything on `/audit`. The label is in the JSON; a
  dashboard surface that reads it is a separate, reviewable change.
- It does not change the gate's exit code. The gate still fails while 74 of 80 miss 0.95,
  and that is the honest state of the book.
- It does not re-run the audit. The labels were applied to the existing 01:09Z snapshot; the
  next sidecar run will recompute them from fresh data.
