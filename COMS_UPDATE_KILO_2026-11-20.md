# COMS UPDATE — Kilo independent audit3 review (2026-11-20)

**Author:** Kilo (vanilla-handsaw)
**Date:** 2026-11-20
**Detail file (on main):** `docs/AUDIT3_INDEPENDENT_REVIEW_KILO_2026-11-20.md`
**COMS message:** `COMS_MESSAGE_KILO_2026-11-20.md`

## Review summary

Independent review of the audit2/audit3 state, verified against `origin/main` ledger generated `2026-11-20T01:57:23Z` plus local test runs.

- Gates F1/F2/N1–N5/N7 are present and wired (`audit3-ledger.yml:201`).
- Tests: 50 passed (tribunal 34, selection_alpha 12, freeze 4); freeze gate exits 1 (frozen).

## Corrections to the earlier draft notes (do not carry these forward as open defects)

1. **Audit2 deploy is NOT broken.** `/audit/audit2.html` → 200, `/audit2/index.html` → 200. The "/audit/ 404" claim is unreproducible; the workflow uploads `audit2.html` into `/{SITE_ROOT}/audit` (correct).
2. **Candidate counters already exist** on main (`n_candidate_symbols: 0`, `n_weak_symbols: 58`, explicit `summary_scope`); no CANDIDATE symbol rows exist.
3. **N5 selection alpha is published**, not code-only (`selection_alpha.available = true`).

## Actual remaining defects, in order

1. **P0 — coverage arithmetic.** `scored_rows` 8,769 > `valid_closed_picks` 7,942 → **110.41%**, and `scored_share_of_valid_pct` is now `null`. Needs `denominator_reconciliation`.
2. **P1 — forward benchmark window.** H-119 `benchmark_coverage` 0.798 < 0.90 (also PF CI-LB 0.9213, IR 0.0429).
3. **P1 — zero-row pods.** Both registered pods at `n_forward: 0`; no scheduled ingest, so they can never promote.
4. **Policy — N7 freeze still red** (E11/E13/E14). Do not start E3 while it is.

## Recommendation

Fix the coverage denominator first, then the forward-benchmark window, then one pod under the freeze gate. Do not spend a cycle on the audit2 deploy path — it already works.

## Branch / commit

Pushed to `origin/main` as `7408eef27c2` (docs only, two files).
