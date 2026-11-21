# Strategy crosswalk — the DSR trial-count bracket is closed at 695

**Date:** 2026-11-21
**Scope:** `tools/strategy_crosswalk.py` (new), `tests/test_strategy_crosswalk.py` (new),
`tools/trial_population_reconcile.py`, comment-only change to
`alpha_engine/money_ready_verdict.py`
**Status:** closed and verified; `NB_TRIALS_BY_CLASS` values unchanged; no verdict flips

## What was broken

DSR deflates the best observed statistic by the number of trials `N` and is
monotone decreasing in `N`, so the trial count alone decides pass/fail. Two
artifacts both claim to report it:

| artifact | distinct (class, strategy) |
|---|---|
| `audit3_ledger.json :: cells` | 342 |
| `pf_registry :: by_asset_class_strategy_policy_clean_net` | 695 |
| shared / audit3-only / pf-only | 124 / 218 / 571 |
| union | 913 |

`tools/trial_population_reconcile.py` could only report a bracket `[695, 913]`.
A bracket on a number that decides the verdict is not a defensible resting
state, so it was left as an explicit placeholder pending a crosswalk.

## Root cause (in code, not inferred)

`tools/build_pf_registry.py`:

```python
def _strategy(row):
    return _norm(row.get("source_system") or row.get("strategy"))
```

The registry keys each row by the **emission engine** when the pick carries one
and falls back to the strategy string only when it does not. audit3 keys on the
pick's own `strategy` string. The two artifacts are therefore two **granularities
of the same picks**, not two taxonomies of different ones — and comparing label
sets 1:1 manufactures disagreement that is really collapsing:

- `CRYPTO / copy_trader_clones` — one registry cell, **7** distinct strategies
- `FUTURES / multi_asset_scanner` — one cell, **4** strategies
- `EQUITY / regime_terminal` — one cell, **3** strategies

## What the crosswalk measured

`tools/strategy_crosswalk.py` rebuilds the registry from the same rows the
builder reads (`load_rows()` → `classify_rows()` → `_is_policy_excluded`),
derives `source_system → {strategy}` per pick, and splits audit3's 342 pairs:

| bucket | count | meaning |
|---|---|---|
| DIRECT | 124 | registry cell under its own name |
| COLLAPSED | 13 | in the book, filed under another label |
| ABSENT | 205 | nowhere in the policy-clean book |

The load-bearing result is **ABSENT = 205**, not "218 synonyms". The working
hypothesis was that most of the apparent drift would be naming. The measurement
refuted it: those 205 strategies are scored by audit3 but never enter the
policy-clean book, so they were **never candidates** in the selection that DSR
corrects.

Grains, for the record: engine-grain cells **695**, distinct strategy strings
**690**, plus **6** unnamed `(class, label)` buckets = **696**, union with audit3
at strategy grain **897**.

## Decision — and the trap I walked into

I adopted the 696 strategy-grain numbers class by class (CRYPTO 627, ETF 15,
FUTURES 6, …). `tests/test_dsr_trial_baselines.py::test_baseline_never_exceeds_the_search_space_actually_tested`
rejected it:

```
ETF     cells 12  mapped 15
FUTURES cells  3  mapped  6
```

**The test is right and I was wrong.** DSR deflates the best **cell** of
`by_asset_class_strategy_policy_clean_net`; the candidates available for
selection are those cells. A cell that internally contains 7 strategy strings is
still one candidate in the comparison that produced the best statistic, so
deflating by 7 inflates `N` past the number of tests actually available. The
finer grain counts sub-features *inside* a candidate, not additional candidates.

**Closed definition:** one trial = one distinct cell of
`by_asset_class_strategy_policy_clean_net` → **695** total, per class CRYPTO 629,
FOREX 18, EQUITY 19, ETF 12, COMMODITY 9, FUTURES 3, BOND 2, MEME/PENNY/CHEAP 1.

The bracket therefore closes at the **lower** end — 695, not 913 — but not
because the lower end was convenient: the union double-counted by mixing grains,
and 205 of its 218 extra pairs were never in the book at all. `NB_TRIALS_BY_CLASS`
keeps its existing values; the closure is that they are now *demonstrated* rather
than assumed. The 696 strategy grain is recorded in the report as a diagnostic
only, with the reason it must not be adopted.

## Verification

- **Reproduction:** 695 shipped cells = 695 rebuilt, 0 missing, 0 extra;
  `--require-reproduction` exits 2 otherwise.
- **No verdict flips:** all classes at their existing `N` — CRYPTO DSR 0.9287
  (FAIL, breakpoint 348), COMMODITY 0.0000, FOREX 0.0000, BOND/EQUITY/ETF/FUTURES
  non-estimable (too few returns).
- **Tests:** `tests/test_strategy_crosswalk.py` 5 passed; the affected suite
  (`test_dsr_trial_baselines`, `test_dsr_baseline_skip`,
  `test_profit_program_math_2026_11_20`) passes with the cell-grain values.
- **`tools/dsr_trial_baseline_report.py --strict`** — every class `ok`, no OVER.
- **`tools/trial_population_reconcile.py`** no longer presents the union as a
  live bracket; it points at the crosswalk as the closure.

## A self-inflicted error, recorded

Two, both caught before commit:

1. **Wrong population.** The first crosswalk draft ran without
   `PF_REGISTRY_INCLUDE_OUTCOMES=1`, so it never ingested the ~25k
   `at_pick_outcomes` rows the shipped registry depends on and rebuilt only 65
   cells against 695. Every figure from that run was meaningless and its 290
   "ABSENT" pairs were an artefact of missing input. Hence the reproduction guard.
2. **Wrong dict.** Adopting the numbers via `re.search(r'("CRYPTO": )(\d+)')`
   matched the **first** occurrence in `money_ready_verdict.py` — `SLIPPAGE_BPS`,
   not `NB_TRIALS_BY_CLASS` — rewriting CRYPTO slippage 15.0 → 627.0 plus four
   other classes. Caught in the diff, file restored from HEAD, edit reapplied
   anchored on the enclosing declaration. Anchor constant patches on the
   declaration, never on a bare key that appears in several dicts.

## Residual limitations

- The closure describes the registry **as built with `PF_REGISTRY_INCLUDE_OUTCOMES=1`**
  (23,651 of 34,115 raw rows). Without that gate the tool reports the rebuild
  mismatch instead of a number.
- The recount analysed 23,732 policy-clean rows vs the shipped 23,651 — the input
  advanced between 11:05Z and 22:52Z. The cell set is byte-identical, so counts
  are unaffected.
- audit3's 205 absent strategies are not individually attributed (policy
  exclusion vs never-closed). Under the cell-grain definition this no longer
  affects `N`, but it remains an open question about what audit3 scores.
