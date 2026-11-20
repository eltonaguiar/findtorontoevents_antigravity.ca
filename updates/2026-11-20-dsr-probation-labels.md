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

## Follow-up, same day: the labels were stripped 6 minutes later

The label landed on `main` at 20:24 and a refresh at 20:30 published 81 rows of which **4 had no
label**, while the payload still claimed `{PUBLISHABLE: 6, PROBATION: 74}` = 80. Measured by
diffing the merged blob against the live artifact:

| row | n | dsr | label before | label after |
|---|---|---|---|---|
| `commodity_rsi_divergence` | 43 | 0.9280 | PROBATION | *absent* |
| `luxalgo_confluence` | 5099 | 0.5904 | PROBATION | *absent* |
| `regime_mild_bear` | 283 | 0.0356 | PROBATION | *absent* |
| `metals_mean_reversion` | 25 | 0.0285 | PROBATION | *absent* |

`n` and `dsr` were byte-identical, so this was not a recompute: rows were re-emitted by a writer
that does not know about the label, merged into the older payload (which is why
`publication_labelled_at` stayed at 20:24 while `generated_at` moved to 20:30). The same refresh
also emitted **`regime_mild_bear` twice** — 81 rows over 80 distinct names, and
`n_strategies_audited` still says 80. That duplicate is left in place deliberately: deleting a row
to tidy an artifact is the exact move this whole change exists to prevent.

Two things were wrong with the original fix, and both were mine:

1. **The label was applied at row construction.** `audit_strategy()` labelled every row it built,
   which is true only for rows built there. It now labels in one pass over `rows` just before the
   payload is assembled, so a row appended by any other path is still labelled, and the sidecar
   itself emits `publication_label_counts` / `publication_label_rule` / `publication_labelled_at`
   instead of leaving those to a separate tool.
2. **Nothing checked it.** `tools/apply_dsr_probation_labels.py --check` now exits 1 when any row
   is unlabelled, when a label contradicts its own DSR, or when the stated counts disagree with the
   rows. The hourly workflow runs `--apply` then `--check` after the sidecar, so the artifact
   self-heals and a future stripping writer fails the run instead of quietly shipping.

`tests/test_publication_labels_consistency.py` asserts the same invariants in CI. The duplicate is
reported by the suite rather than deleted or silently tolerated.

