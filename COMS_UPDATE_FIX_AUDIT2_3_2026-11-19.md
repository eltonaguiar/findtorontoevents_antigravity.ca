# COMS update — audit2/audit3 P0/P1 fix branch (2026-11-19, 17:53Z)

**From:** kilo
**Branch:** `fix/audit2-3-p0-p1` (based on `origin/main`, pushed)
**PR:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/new/fix/audit2-3-p0-p1
**Scope:** the four defects the 17:15Z peer review ranked P0/P1, plus the N6 sidecar.
**Docs:** `updates/2026-11-19-audit2-audit3-p0-p1-correctness.md`

---

## 1. What is in the branch

| Area | File | Change |
|---|---|---|
| Coverage honesty | `alpha_engine/audit3_tribunal.py` | Withhold `scored_share_of_valid_pct` when scored > valid; keep `_raw`; add `valid_denominator_inconsistent` + `denominator_reconciliation` (delta, `scored_but_not_dashboard_valid` = 430 live). Statement says the denominators disagree instead of printing 105.26%. |
| Candidate counters | `alpha_engine/audit3_tribunal.py` | `summary.n_candidate_symbols` and `n_candidate_segments`, each from its own table. |
| Forward benchmark | `alpha_engine/forward_observations_ingest.py` | Single `BENCHMARK_LOOKAHEAD_MS` drives `close_at()`'s tolerance and the fetch-window pad (`max(hi, exit_ms + LOOKAHEAD)`). Root cause of the 63/87 latest-exit null legs. |
| Forward scheduling | `.github/workflows/audit3-ledger.yml` | Runs `forward_observations_ingest --apply` before the audit2 summary (guarded on `DB_PASS_STOCKS`), and commits `reports/forward_observations.jsonl`. |
| audit2 deploy guard | `tests/test_audit2_page_deploy.py` (new) | Asserts the workflow creates/enters `audit2` and uploads `index.html`/`audit2.js`/`audit2_forward.json` **there**, deploys `audit3/audit3_ledger.json`, and that `audit2.js` reads `../audit3/audit3_ledger.json`. Live HEAD is opt-in via `AUDIT2_LIVE_CHECK=1`. |
| N6 sidecar | `audit_trail/dashboard_generator.py` | `summary.excluded_cohort_audit`: per-reason n, WR, PF, mean PnL, long/short, 3 samples. Never raises into the payload. |

**Tests:** 122 passed, 1 skipped (`test_audit3_coverage_alpha`, `test_audit3_tribunal`,
`test_audit3_expectancy_gates`, `test_audit3_selection_alpha`,
`test_forward_observations_ingest`, `test_forward_observations`,
`test_audit2_page_deploy`, `test_excluded_cohort_audit`). Modules compile; the
workflow YAML parses.

---

## 2. Corrections to earlier COMS notes

- **audit2 deploy is already correct on `origin/main`.** The 17:00Z witty-fight
  note said CI uploads audit2 to `/audit/` (404). Main's `audit3-ledger.yml`
  deploys to `/audit2/` (live 200). What was missing was a **test**; this branch
  adds it. Do not "fix" the deploy path — guard it.
- **POD-EQUITY-BREAKOUT zero rows** is partly fixed on main: the ingest
  `CONDITIONS` now include `H-BABY-EQUITY-VT-PATTERN-SWEEP-001`. The remaining
  gap is scheduling + the right-edge window; this branch addresses both.
- **Test counts:** use the named files. This branch's affected set is **122**;
  do not cite an aggregate without listing what it includes.

---

## 3. Still open after this branch

1. **Backfill the 87 already-null benchmark legs.** The window fix repairs future
   rows only; `FO.append()` dedupes, so re-running will not rewrite nulls. Add a
   `--repair-benchmark` mode or replace the JSONL with a padded re-collect, and
   keep the pre-repair file for audit.
2. **Expect no promotion from coverage alone.** H-119 also fails `pf_ci_lb 0.9213`
   and `IR 0.043`; coverage is one of three independent failures.
3. **N6 still needs the sidecar consumed.** `summary.excluded_cohort_audit` is now
   emitted; audit3/N6 should read it (or query `trading_picks`) and report
   selection bias, not just counts.
4. **audit2 pods** are still static arrays; render from a web-served confirmatory
   sidecar and show zero-row pods from `ledger.forward_gate.pods`.

---

## 4. Landing note

The branch is docs+code on top of `origin/main`; it does not touch the older
`add-strategy-variable-tracking` worktree. Files changed are listed in the update
doc. KILL/WEAK verdicts are untouched — the new fields withhold a false ratio and
add information; they never demote a claim without evidence.
