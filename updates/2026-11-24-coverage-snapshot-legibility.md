# Coverage snapshot made legible (Block 63)

## The defect

After Block 57 applied the `COVERAGE-LIMITED` label, I reported that its
machine-readable json block was "guarded by a test so it cannot drift". That was
false. Block 62 measured the ledger mid-refresh and found the block's integers had
already moved while `tests/test_coverage_limits_doc.py` stayed green:

| Field | In `COVERAGE_LIMITS.md` | Ledger at `origin/main` (2026-11-24T00:42Z) |
|---|---|---|
| `covered` | 3,190 | 3,188 |
| `scored_rows` | 8,886 | 8,933 |
| `total_closed_picks` | 14,997 | 15,057 |

The existing test only checked the document's *internal* arithmetic -- each rate
recomputed from the document's own integers -- so it could never notice that the
whole block was stale. The document was self-consistent and out of date, with
nothing saying so.

## What was verified first

The snapshot reproduces exactly at the ref the header already names:

    git show ce214306b5caf:audit_dashboard/data/audit3_ledger.json
    -> generated_at 2026-11-23T18:31:33.087120+00:00
    -> selection_alpha.covered 3190, n_universe 3500
    -> coverage.scored_rows 8886, total_closed_picks 14997

So the recorded numbers are honest; they are simply not current.

## What was changed (additive only)

- `CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md`
  - a `snapshot` object in the json: `captured_at_ref`, `ledger_generated_at`,
    and a note saying the figures are point-in-time, refresh hourly, and that
    `tools/check_excluded_summary.py` gives live state.
  - a prose paragraph above `## Machine-readable`: **"These figures are a snapshot,
    not live"**, with the drift table and the statement that the finding's shape is
    unaffected.
  - a dated bullet in `## Observation log` correcting the earlier "cannot drift"
    claim (earlier entries untouched).
- `tests/test_coverage_limits_doc.py`: three new tests --
  - `test_snapshot_stamp_exists_and_names_the_limitation` (stamp present, note
    mentions hourly/not-live and the checker),
  - `test_prose_states_the_figures_are_a_snapshot_not_live`,
  - `test_snapshot_is_within_tolerance_of_the_current_ledger` (skips when the
    ledger is absent; fails if the snapshot drifts more than 5% from live).

No integer, rate, label, `applies_to` entry or `unmeasured` entry was changed; no
verdict, dossier or the programme tally
`0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` was touched.

## Why tolerance and not equality

Chasing the live value would make the document permanently wrong by design, since
the ledger refreshes hourly. A 5% band encodes the real intent: a snapshot is
allowed to be stale, but if it drifts wildly the finding has changed and someone
must re-read it. Today's 3,188 is 0.06% from the recorded 3,190, so the check
passes and still discriminates.

## Verification

- RED (doc not yet updated): `2 failed, 9 passed` -- the two stamp/prose tests fail,
  the tolerance test passes against today's ledger.
- GREEN: `11 passed`.
