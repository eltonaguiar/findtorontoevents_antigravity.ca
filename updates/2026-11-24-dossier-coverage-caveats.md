# Dossier coverage caveats (Block 62)

**Date:** 2026-11-24 · **Branch:** `blk62-dossier-coverage-caveats` off `origin/main` (`a8c1d7732dba90ff9fe64ab532618e3d75252ba7` at dispatch)

## What was broken

Block 57 produced `CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md` and labelled eight ledger
surfaces `COVERAGE-LIMITED`, recording that CRYPTO, FOREX and FUTURES sit at
`alpha_coverage_ok = false`. Its constraints said a dossier verdict needing a coverage pointer
must be *reported, not edited* — and the follow-up block was never dispatched. The three class
dossiers therefore stated measured statistics without saying which subset of the class they
describe: the priced subset, not the full closed-pick population.

## Mapping (by §1 Identity, not by filename guess)

| Class | Dossier | Identity line |
|---|---|---|
| CRYPTO | `docs/audit_review_2026-11-22/01_CRYPTO.md` | `:7` "CRYPTO is one of the canonical classes" |
| FOREX | `docs/audit_review_2026-11-22/04_FOREX.md` | `:7` "FOREX is one of the canonical classes" |
| FUTURES | `docs/audit_review_2026-11-22/07_FUTURES.md` | `:6` "FUTURES is one of the canonical classes" |

All other classes (incl. PREDICTION_MARKET) are out of scope.

## Exact insertion points (additive; no section created)

- `01_CRYPTO.md` — end of `## 9 Cross-check against /audit and the database`, after line 50.
- `04_FOREX.md` — end of `## 9 Cross-check against /audit and the database`, after line 46.
- `07_FUTURES.md` — end of `## 9 Cross-check against /audit and the database`, after line 40.
- `CLASS_INDEX.md` — new trailing subsection `## Coverage caveats (2026-11-24)`; no table row touched,
  so no verdict quote in the table changed.

Section 9 is the section that already discusses cohort and coverage gaps, so the caveat strengthens
existing context instead of competing with `## 8 Blunt answer`. The numbering `## 1`–`## 9` +
`## Provenance` was left untouched.

## Coverage figures cited

Each dossier states **its own** class figure, all from
`CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md` (§2 "Price coverage is clustered by class"):

- CRYPTO **24.2%** (`01_CRYPTO.md`)
- FOREX **46.8%** (`04_FOREX.md`)
- FUTURES **83.3%** (`07_FUTURES.md`)

Each caveat also states:

- the gate already reads `alpha_coverage_ok = false` for the class, set at
  `alpha_engine/audit3_tribunal.py:1264`, against the `ALPHA_MIN_COVERAGE = 0.50` floor declared at
  `alpha_engine/audit3_tribunal.py:1179`, over rows counted at
  `alpha_engine/audit3_selection_alpha.py:383` (`"covered": len(per)`);
- that the dossier's measured statistics describe the priced subset, not the full closed-pick
  population, and point at `COVERAGE_LIMITS.md` for the aggregate;
- what would remove the caveat: the instrumented `coverage.excluded_summary`
  (`tools/check_excluded_summary.py`) once a live build feeds it `_excluded_cohort_rows`, or
  expiry-resolved picks receiving a scored outcome.

## Marker

One marker string, identical in all three dossiers: `Coverage caveat (2026-11-24)`.

## Citation count delta

`python3 tools/check_dossier_citations.py`, before and after:

| | files | distinct paths | resolved | allowlisted | unresolved |
|---|---|---|---|---|---|
| before (`origin/main`) | 38 | 80 | 75 | 5 | 0 |
| after (this branch) | 38 | 80 | 75 | 5 | 0 |

Delta: **zero**. Every path cited by the new prose
(`CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md`, `alpha_engine/audit3_tribunal.py`,
`alpha_engine/audit3_selection_alpha.py`, `tools/check_excluded_summary.py`) already resolved in
the dossier set, so no new allowlist entry was needed and none was added.

## No verdict and no tally changed

- `git diff --numstat` for the four documents: `1/0`, `1/0`, `1/0`, `11/0` — **insertions only, zero
  deletions**, so every original character, verdict words included, is intact.
- No dossier contained any tally string before this block (`grep -E "[0-9]+ INVESTABLE"` over
  `docs/audit_review_2026-11-22/` returned nothing), and the same regex over the edited files still
  returns nothing: no tally was added, and `0 INVESTABLE` appears nowhere new.
- `tests/test_edge_research_tally_consistency.py` (which globs `docs/**/*.md`) still passes.

## Verification

- New guard `tests/test_dossier_coverage_caveats.py` (stdlib only; marker, `COVERAGE_LIMITS.md`
  reference, per-class percentage literal, divergent-tally regex, and a one-marker-per-file check).
- Proven **RED** by replacing the marker in `04_FOREX.md` with a placeholder: 3 failed, 3 passed.
  File restored from a backup, marker count back to 1.
- **GREEN:** `python3 -m pytest tests/test_edge_research_tally_consistency.py
  tests/test_check_dossier_citations.py tests/test_coverage_limits_doc.py
  tests/test_dossier_coverage_caveats.py -q` → **45 passed**.
- Registered in `.github/workflows/verification-tests.yml` (pull_request paths, push paths, and the
  pytest invocation) — no new workflow.

## Premises measurement falsified or refined

- The brief's `selection_alpha.covered` **3,190** / `n_universe` **3,500** is the figure in Block 57's
  `COVERAGE_LIMITS.md` (still 3,190 there). The ledger committed on `origin/main` today reads
  **3,188 / 3,500** (91.09%, not 91.14%) after an hourly refresh; per-class sums to 3,188. The
  percentage differences are unchanged at one decimal place. The per-class coverage percentages
  cited in the dossiers come from `COVERAGE_LIMITS.md` and were not re-derived (they need the
  generator, which this block must not run).
- Everything else held: the class→dossier mapping was unambiguous, all three dossiers exist, and
  all cited paths resolved at `origin/main`.
