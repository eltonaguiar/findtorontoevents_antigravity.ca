# HML pre-registration — collateral treatment stated explicitly

**Date:** 2026-11-23
**Scope:** one documentation amendment to `docs/preregistration/HML_VALUE_TEST_2026-11-22.md`, plus the merge of its PR. No code, no research, no result.

## What was ambiguous

The benchmark section of the HML pre-registration said the benchmark is "committed capital including cash collateral" but never said what the collateral earns. That left the hurdle movable after the fact: a run could credit collateral at the policy rate in the benchmark, or ignore it, and either choice would be defensible from the old wording. For a short-leg book that posts collateral, the interest on that cash is the whole difference between a fair bar and a flattering one.

## What was changed

- Stated two named cases in the benchmark section:
  - `COLLATERAL_BASE` — collateral earns the policy rate, 4.32% annualised `[SRC: tools/capacity_model.py:49]`; the benchmark is the long-leg return plus the short-leg return plus collateral interest.
  - `COLLATERAL_CONSERVATIVE` — collateral earns 0%; because a zero-yield benchmark under-credits cash, the forgone interest is booked as an explicit cost charged to the strategy: `forgone_collateral_interest = 0.0432 × collateral_notional × (days / 365)`, so `net_conservative = gross_strategy − turnover_cost − forgone_collateral_interest`.
- Named `COLLATERAL_CONSERVATIVE` as the headline for the go/no-go decision, on the ground that it is the only case that cannot flatter the strategy.
- Added a sentence stating the kill rule is applied to both cases and that a pass in only one case is not a pass.
- Added a symbolic worked example (`$100,000` committed, 50% collateral, 30 days) showing the arithmetic only — explicitly not a measured result.
- Repaired a stale programme tally figure from `0 / 10 / 4` to the settled `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` with a source marker and as-of date.
- Marked the two literature HML ranges (`25–42 bp`, `50–70 bp`) `UNMEASURED`, since no citation for them exists in this repo.
- Added an appendix carrying the eight dossier headings and a Provenance footer the doc linter requires, recording the amendment and its UTC timestamp.

## What was deliberately NOT changed

- The kill-rule threshold: it is still written as `≤ 4.3%`, with the existing note that `4.32%` is the binding bar. No number in the kill rule moved.
- The out-of-sample methodology, the blockers, and every existing result/claim.
- Other documents' tallies. Only the HML document's stale figure was touched.

## How it was verified

- `python3 tools/doc_source_lint.py` on the amended file → `1/1 clean` (PASS), and the same on the merged blob.
- `python3 -m pytest tests/test_edge_research_tally_consistency.py -q` → `19 passed`, run in a temporary tree seeded with the branch's `docs/edge_research` (the tally test and those docs are not on `main`).
- The amendment commit `13f8bbe6bb79430dc9745eeb4aa599812b2bd3c1` was built with a temporary index: `git show --stat` lists exactly one file, and its parent is `8df189f317c`.
- PR #1065 was `MERGEABLE` / `CLEAN` at merge time and merged with a merge commit, no admin bypass and no force. Merge commit `935097798d2bf1e9da2d6671b2a67ff695888aab`.
- From the merged `origin/main` tree: `git merge-base --is-ancestor 13f8bbe origin/main` exits 0, `git ls-tree origin/main docs/preregistration/` lists the file (blob `776cce3d`), and the merged blob is byte-identical (sha256 `e77f3605…`) to the reviewed file.

## What was not established

- No citation for the `25–42 bp` / `50–70 bp` HML ranges exists in this repo → `UNMEASURED`.
- The "three independent sources" for PEAD decay are named only in the document's own prose, with no citation list in the repo to verify them → left as an operator premise.
- The collateral notional split (e.g. 50% in the worked example) is illustrative arithmetic, not a measurement.
