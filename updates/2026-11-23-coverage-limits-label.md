# 2026-11-23 — COVERAGE-LIMITED label applied to the audit3 ledger surfaces (Block 57)

## What was asked

Block 56 (`CONTEST/ROUND_01_2026-11-23/COVERAGE_BIAS.md`, PR #1108) measured the audit3 ledger's
coverage and returned BIASED, but reported it could not measure the class composition of the
6,111 unscoreable rows. Block 57 was asked to (A) close that gap as far as `origin/main` allows
and record it as an appended amendment, (B) apply an explicit coverage label in a new
`COVERAGE_LIMITS.md` with a machine-readable block, and (C) guard the label with a test wired
into the existing `verification-tests.yml`.

## What was measured in PART A

Re-measured at `origin/main` = `ce214306b5caf6e52d231f13930cc99f0b7349d2` (Block 56 measured at
`85c0c9c3d3c7`; the ledger, denominator, raw dashboard payload and both producers are unchanged
between the two refs). Re-verified: covered 3,190 / universe 3,500 / scored 8,886 / closed 14,997,
and the four rates 91.14% / 59.25% / 35.90% / 21.27% are all unchanged.

Two of Block 56's figures were wrong and are corrected in the amendment:

- scoreable-but-outside-the-3,500-cap is **5,386** (8,886 − 3,500), not 5,696. `5,696 = 5,386 + 310`
  double-counted the price-missing rows inside the universe. The 11,807 non-covered total is right.
- `selection_alpha.by_strategy` has **38** cells, not 39.

Measured in PART A:

- The exclusion taxonomy in code: `invalid_row`, `mirror_duplicate`, `non_performance_exit`,
  `resolver_breakeven_fallback` (from `alpha_engine/resolved_closed_view.py`), plus the overlapping
  dashboard cohorts `integrity_excluded` and `auto_expired` (`audit_trail/dashboard_generator.py:17119`,
  `:17138`). The four canonical reasons sum **exactly** to the 6,111 gap; the two cohorts overlap
  and are not a partition.
- The mechanism for each reason, with file:line, distinguishing "no outcome exists" (auto-expired
  timeouts, missing PnL, fabricated breakeven fallback, cancels/non-fills) from "outcome exists but
  was discarded" (mirror duplicates, corrupt/placeholder/micro-hold/blocked rows inside
  `invalid_row`, integrity contradictions).
- A content search of 5,316 JSON/JSONL files across `audit_exports/`, `reports/`, `data/`,
  `audit_dashboard/data/` and `docs/audit_review_2026-11-22/_raw/`: **no per-class or per-row
  counts of the excluded rows exist**. Only aggregate counts do (the reason table, the two
  cohorts, resolver anomalies, and `denylist_hits.by_class`, which is a different population).
  The rows file `resolved_closed_picks_net.json` is not tracked and is shipped only as
  `rows_embedded: false`.

## What remains UNMEASURED

- Class composition, strategy mix and date distribution of the 6,111 unscoreable rows.
- The split of `invalid_row` (5,917) between no-outcome and discarded-outcome branches.
- Net direction of the outcome selection among those 6,111 rows.
- Alpha of the 310 price-missing rows inside the display universe.
- Per-row covered-vs-uncovered date split.

Artefact that would measure the first four: a shipped `resolved_closed_picks_net.json` whose
excluded rows keep `exclude_reason` + `asset_class`, or the generator embedding
`audit_trail/excluded_cohorts.summarize_excluded()` (already written and tested, not called).

## What label was applied

**`COVERAGE-LIMITED`**, in `CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md`, applying to
`classes[]`, `selection_alpha.by_class`, `selection_alpha.by_slice`,
`selection_alpha.by_strategy`, `selection_alpha.overall`, `selection_alpha.gate`, `segments`
and `cells`: every one is computed over picks that resolved to a determinate outcome and
survived the 3,500-row display-universe cap (3,190 price-covered rows), not over all 14,997
closed picks. Class-gate uncovered: CRYPTO, FOREX, FUTURES.

## Verification

`tests/test_coverage_limits_doc.py` was proven RED by perturbing `scored_rows` 8,886 → 9,999
(`rates.scored_of_closed = 0.5925 does not match the recomputed 0.666733`), then GREEN after
restoring. Required greens: `python3 -m pytest tests/test_edge_research_tally_consistency.py
tests/test_check_dossier_citations.py tests/test_coverage_limits_doc.py -q`.
