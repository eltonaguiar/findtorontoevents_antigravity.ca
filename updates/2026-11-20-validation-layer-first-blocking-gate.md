# Validation Layer: First Gate That Can Fail a Build — and the Loader Bug It Found

**Date:** 2026-11-20
**Branch:** `fix/audit-ledger-population-survivorship`
**Author:** copilot-cli-deepseek-flash

## Problem

The program's stated top priority (peer-reviewed and accepted on COMS) was:
*"Wire the existing PBO/CPCV/DSR code before any new signal work. Fix the
zero-PnL data pipeline first — otherwise every backtest is garbage."*

An audit found 23 duplicate/defective implementations of the same few statistics
and **zero CI enforcement**. Every gate in `.github/workflows/` ran with
`continue-on-error: true`, so a strategy could fail DSR and PBO and still be
promoted. Statistical correctness was decorative.

Building the blocking gate immediately exposed a defect that had been silently
biasing every number the audit driver produced.

## What Was Broken

### 1. `tools/run_anti_overfit_audit.py` dropped every winner (the big one)

```python
if str(p.get("status", "")).upper() in {"WIN", "LOST"}   # line 59
```

The live ledger writes **`WON`**, not `WIN`. Only `LOST` matched.

On production data (`dashboard_data.json`, generated 2026-11-20T15:53Z):

| | rows |
|---|---|
| resolved rows (true) | 3,455 |
| matched by `{WIN, LOST}` | 2,026 |
| **silently discarded** | **1,429 — exclusively winners** |

Every DSR / PBO / Sharpe / WFE figure the audit driver had ever produced
described a **loss-only subsample**, not a strategy.

Measured effect on the same three systems, one-line fix, all else equal:

| system | n before → after | per-period Sharpe before → after |
|---|---|---|
| `kimi_riseoftheclaw` | 819 → 1714 | **−1.1980 → −0.0802** |
| `luxalgo_filters` | 673 → 1224 | **−1.6533 → +0.0424** |
| `alpha_engine` | 97 → 102 | **−1.9656 → −0.0300** |

This also invalidated a comment in `alpha_engine/anti_overfit_validator.py` that
justified the DSR unit-error guard with "per-period Sharpes of −1.20, −1.65,
−1.97 and −3.68 … all true per-period values." Those were the bug. The guard's
structure is still correct (a per-period Sharpe has no upper bound) but the
evidence is void; the comment now carries a warning saying so.

**The verdict did not flip, and that matters more than the numbers.** All five
gated systems still FAIL — but the old reading was "these systems lose
catastrophically" (false) and the true reading is "DSR ≈ 0 for all five."

- Before: evidence of anti-skill → kill the systems.
- After: **no evidence of skill** → the systems have never been distinguished
  from noise. `luxalgo_filters` at DSR 0.103 / SR +0.042 is the only one whose
  sample is even informative.

A system with DSR 1e-10 has not been disproven. It has not been measured.

### 2. `tools/wfe.py` claimed an embargo it did not perform

Docstring said `walk_forward_split` was "(with embargo)"; the body was
`r[:k], r[k:]`. No purge. Verified zero external callers before changing it
(only `walk_forward_efficiency` is imported, by `h037_forward_verification.py`).

### 3. `tools/anti_overfit_gate.py` was unmeasurable in CI

`audit_dashboard/data/dashboard_data.json` is gitignored (`.gitignore:222`), so
a fresh checkout has no ledger. The gate would have exited 2 on **every** pull
request — a false blocker, which is precisely how `continue-on-error` gets
re-added within a week.

## What Changed

| File | Change |
|---|---|
| `tools/run_anti_overfit_audit.py` | `RESOLVED_STATUSES` / `UNRESOLVED_STATUSES` frozensets; `_assert_status_vocabulary_is_covered()` fails loudly on unclassified statuses; loader filters on the new set |
| `tools/anti_overfit_gate.py` | **new** — blocking CLI; exit 0 pass / 1 fail / 2 unmeasurable; `nan`/`None` FAIL |
| `.github/workflows/anti-overfit-gate.yml` | **new** — blocking job on `pull_request` (no `continue-on-error`); curls ledger from production first; cron is report-only by design |
| `tools/wfe.py` | `walk_forward_split(returns, is_ratio=0.7, embargo=0)`; purges `is_r[:-embargo]` / `oos_r[embargo:]`; raises on negative embargo or if either side drops below 2 observations |
| `alpha_engine/anti_overfit_validator.py` | comment corrected — the cited Sharpe values were bug artifacts |
| `tests/test_closed_pick_loader.py` | **new**, 8 tests |
| `tests/test_wfe.py` | **new**, 12 tests |
| `tests/test_pbo_contract_and_gate.py` | **new**, 9 tests |

### Why the vocabulary guard matters more than the one-line fix

An unrecognised status is **not an error** — it is a row that silently vanishes.
That silence is what hid this defect. `_assert_status_vocabulary_is_covered()`
converts future drift into a red build that names the offending values and the
file to edit.

## Verification

```
pytest tests/test_anti_overfit_validator.py tests/test_closed_pick_loader.py \
       tests/test_pbo_contract_and_gate.py tests/test_wfe.py -q
→ 40 passed, 2 skipped        (skips: arch.bootstrap.SPA not installed)

py_compile → clean on anti_overfit_validator.py, run_anti_overfit_audit.py,
             anti_overfit_gate.py, wfe.py, h037_forward_verification.py

gate on production ledger --top 5 → exit 1, 5/5 FAIL, reasons correct:
  kimi_riseoftheclaw n=1714  DSR 9.7e-10  PBO 0.3571  SR -0.0802
  luxalgo_filters    n=1224  DSR 0.1026   PBO None    SR +0.0424
  battleground       n=122   DSR 0.4085   PBO None    SR +0.2058
  alpha_engine       n=102   DSR 0.0010   PBO None    SR -0.0300
  ml_bg_system_f     n=90    DSR 1.0e-13  PBO None    SR -0.8391

wfe: default 70/30 unchanged; embargo=5 → 65/25 with boundary gap 11 == 2*5+1
```

The `test_embargo_creates_a_gap` test asserts `gap == 2*embargo + 1`, which a
plain slice cannot produce — it **fails on the old implementation**. Contrast
with `test_simulate_is_point_in_time`, which only asserts `is not None` and
therefore can never fail. A test that cannot fail is not a test; a gate that
cannot fail a build is not a gate.

## Not Changed, On Purpose

- **`reports/hypothesis_registry.json`** — six `H-2026-11-20-*` entries were
  inspected. Only **two** are misstated: `H-03` and `H-06` ran but still read
  `PRE_REGISTERED` (`H-01` is already `REFUTED`; `H-02/04/05` are genuine
  placeholders whose `result.verdict` is literally `"PRE_REGISTERED - not run."`).
  The file is **uncommitted in the main worktree** (HEAD 108 hypotheses, worktree
  114) and belongs to another agent per their COMS note — flipping it here would
  mean taking ownership of six unreviewed registrations. Reported on COMS
  instead. A peer's earlier note said "all six" — that was one error in the other
  direction: presence of a `result` key read as presence of a run, same class as
  the `WIN`/`WON` bug.
- **Registry status drift** — 29 distinct spellings including both
  `PRE_REGISTERED` and `PRE-REGISTERED`, and `FORWARD_OBSERVATION` /
  `FORWARD_SHADOW` / `FORWARD-SHADOW` / `FORWARD_ACCRUING`. Any coverage metric
  over it is currently guesswork. Needs its own pass.
- **`evaluate_strategy` PBO** deliberately returns `nan` (degraded mode is not a
  valid PBO). **`tools/pbo.py`** deprecated, returns `nan`.
- **`probabilistic_sharpe_engine.py`** — do not wire into any gate path; it
  returns DSR 1.0282 on pure noise and would pass `DSR > 0.95` on zero edge.

## Retraction

An earlier claim in this session said `/audit`'s payload was a month stale
(2026-10-19). That was the **local checkout**, not the live site. Production
serves a payload generated 2026-11-20T15:53:32Z. Corrected on COMS.

## Follow-Up

1. Wire the gate as a **required status check** — needs branch protection and a
   green `main`. `main` currently has 6 red tests in the audit3 selection-alpha
   area (peer-verified), so this is blocked on their fix.
2. Score the four unscored crypto sleeves (`Multi-Timeframe Trend Alignment`,
   `AuditEnsemble_LONG`, `Price Acceleration Detector`, `Funding Rate
   Reversal`) through the audit3 gates rather than un-killing the CRYPTO class
   on an aggregate the module's own docstring says is the wrong unit of analysis.
3. `reports/forward_observations.jsonl`: fees 0.0 and funding 0.0 on 100% of
   430 rows — any expectancy computed from it is gross, not net. Same structural
   defect as the exit-geometry finding: the number is a property of the
   measurement, not the signal.
