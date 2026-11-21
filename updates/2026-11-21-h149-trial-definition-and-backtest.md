# H-149 registration fix, trial-count reconciliation, and the EQUITY backtest

**Date:** 2026-11-21 · **Branch:** `fix/dsr-baselines-h146-key-scrub-2026-11-21`
**Follows:** `updates/2026-11-21-consult-multi-key-scrub-dsr-baselines.md`

Three things, in dependency order: the hypothesis id had to be corrected before a
PR could describe it, the trial-count definition had to be settled before any
backtest's significance meant anything, and only then could the backtest run.

---

## 1. What was broken — the registered id collided

The EQUITY mid-cap gross profitability hypothesis was registered as `H-146`
against `origin/main`, where the highest committed id was `H-145`. That was
correct at the moment of registration.

After registering, the main working tree turned out to hold an **uncommitted**
block from another agent covering `H-144`…`H-148`, in which `H-146` is the ETF
`execution_cost_gate` — the draft that already existed in
`plans/2026-11-20-residual-mean-reversion-hypotheses.md` and in
`sql/profit_program_schema.sql`. Had that block landed, two different hypotheses
would have shared one id. Registry rules forbid reuse.

The same block already carries **duplicate ids of its own**: `H-144` twice
(CRYPTO `position_timeframe_selection`, committed, and ETF
`residual_mean_reversion`) and `H-145` twice (ETF `exit_geometry_time_exit` and
COMMODITY `calendar_spread_reversion`). Flagged, not fixed — it is not mine to
renumber.

**Changed:** the entry moved to `H-149` = max id observed across `origin/main`,
this branch, and the dirty working tree, plus one. The hypothesis, its
acceptance criteria, its economic prior and its `banned_check` are byte-for-byte
unchanged; only `id` moved. `updates/2026-11-21-consult-multi-key-scrub-dsr-baselines.md`
§3 was corrected in the same commit so the record does not point at the wrong id.

**Verified:** `reports/hypothesis_registry.json` parses; the entry reports
`id=H-149`; `grep -c H-146` on the branch returns 0 outside the raw panel
evidence, which is a historical transcript and is left as-is.

---

## 2. What was broken — neither artifact's cell count is a trial count

The DSR baselines committed earlier were raised from `pf_registry`
`by_asset_class_strategy_policy_clean_net`, on the reasoning that `audit3`'s
`cells` array was a *filtered subset* of that population (audit3 keeps only cells
passing an n/significance filter, so it should under-count). That reasoning was
**untested**. Now it has been tested and it is **wrong**:

| quantity | count |
|---|---|
| audit3 `cells` rows | 367 |
| audit3 distinct (class, strategy) | 342 |
| pf_registry policy-clean (class, strategy) | 695 |
| shared | **124** |
| **audit3-only** (pf_registry does not carry) | **218** |
| **pf-only** (audit3 does not score) | **571** |
| union | 913 |

The two artifacts are not at different filter settings of one population. They
are **two taxonomies**: `pf_registry` derives strategy names from
`at_raw_picks.source_system`, while `audit3` uses the pipeline's own `strategy`
strings. Only 124 of 913 pairs (13.6%) overlap. Per class they disagree in both
directions: `EQUITY` has 54 audit3 labels vs 19 pf labels, `CRYPTO` has 210 vs
629. The "3× disagreement" I reported earlier is not a filter artefact — it is
this mismatch.

### The decision

**Primary N = distinct (asset_class, strategy) in
`pf_registry.by_asset_class_strategy_policy_clean_net`.** Rationale: DSR deflates
the selection that produced the *reported* statistic, and that statistic is
computed from `pf_registry` (`alpha_engine/money_ready_verdict.py` reads that
book). Trials that never entered the book the verdict reads did not contribute
to the maximum being deflated.

**Upper bound N_union = 913** (CRYPTO 737, EQUITY 67, ETF 49, FOREX 30,
COMMODITY 11, BOND 13, FUTURES 3), reported on every run as a sensitivity. It is
the count to adopt if a crosswalk proves the audit3-only labels are genuinely
distinct strategies rather than renamed duplicates.

So the honest statement is a **bracket [695, 913]**, not a number. The primary is
the lower end because it is internally consistent with the deflated statistic;
the union is the conservative end. Raising N can only kill a class — DSR is
monotone decreasing in N — so the open question can never flatter a verdict.

`NB_TRIALS_BY_CLASS` is **left at the primary values** (629/18/9/19/12/2/3):
adopting the union would change EQUITY 19→67 and ETF 12→49, and is therefore a
separate, verdict-affecting change that should not ride along inside a
measurement fix. **Recorded as the open follow-up.**

**New tool:** `tools/trial_population_reconcile.py`. It reduces audit3's
direction/namespace-split rows to `(class, strategy)` pairs (367 rows collapse
2.07× onto 342 pairs, which is what proves the splits are subdivisions and not
extra trials), compares against `pf_registry`, and asserts the subset property.
`--strict` exits 1 on taxonomy drift, so the drift cannot be assumed away in CI.
Run twice → byte-identical output.

**Report:** `reports/2026-11-21-trial-population-reconciliation.md` +
`reports/trial_population_2026-11-21.json`.

---

## 3. The H-149 backtest — built, run, UNTESTED

**New tool:** `tools/h149_midcap_gross_profitability.py`.

- Fundamentals come from **SEC XBRL `companyfacts`**, not `yfinance`, because
  XBRL carries a `filed` date per fact and `yfinance` does not. The
  pre-registered look-ahead rule — a fact is usable only if `filed` is
  **strictly before** the rebalance date — is therefore actually implementable.
  (This is the same caveat `tools/backtest_piotroski_fscore.py` admits in its own
  docstring.)
- Universe: random sample of SEC filers (seed 149), filtered at each rebalance to
  point-in-time market cap $2B–$10B using `dei` shares × that day's close. Not an
  index list, so constituent churn cannot leak.
- `tools/edge_stability_harness.py` is imported **unmodified** from its file path;
  its own `_windows()` / `_window_eff()` do the bucketing. `--self-check` asserts
  `EFF_MIN=0.30`, `MIN_WINDOW_N=80`, `MIN_STABLE_WINDOWS=3` are still the
  published values, and the tool **refuses to report a verdict** if they are not.
  Verified passing.

**Result:**

| measure | value |
|---|---|
| SEC filers in pool / sampled | 10,399 / 150 |
| names with usable fundamentals and prices | 47 |
| rebalances used / skipped as sparse | 93 / 27 |
| records | 556 |
| windows at 14d | 91 |
| windows meeting `MIN_WINDOW_N=80` | **0** |
| windows scored | **0** |
| **verdict** | **UNTESTED** |

556 records over 91 windows is **6.1 per window** against a floor of 80, and the
harness needs ≥15 winners *and* ≥15 losers inside a window before it will compute
an eff. So every window returned `None`: there is nothing to read in either
direction. **Data gap = 6,724 records; 13.1× the current name count** (~600 names
through the fundamentals filter, or a 15-year history).

**The one real economic signal in the run:** the bottom decile also returned
+1.2506% per 40 days, against +1.4218% for the top decile. Both legs made money,
so the top-decile return is market drift, not selection. The part attributable to
the signal is the long/short spread, **+0.1712% per 40 days** — a twelfth of the
drift and *below the 20 bp round-trip cost*. The cost-survival figures (0.879 at
20 bp, 0.757 at the 40 bp stress) are therefore **not evidence**: they measure the
fraction of a beta-driven return that survives cost.

### Declared spec deviations

Four of the pre-registered spec elements were **not** implemented literally:
annual 10-K instead of quarterly statements; full cross-section scored with the
top **decile** reported instead of a top-quintile book; 40 trading days instead
of the 20–60 calendar-day exit clock; month-end close instead of next-open entry.
All four are recorded in the registry entry and in the report §1.

They are declared because a deviation found later reads as p-hacking. They are
also, in this case, **inert**: the run produced no scorable window, so no
significance depends on which spec was followed, and nothing was rescued by the
drift. The literal spec remains untested and is the next required run.

**Report:** `reports/h149_midcap_gross_profitability_2026-11-21.md` + `.json`.
Registry `result` block updated with the run, the gap, and the deviations.

---

## Verification actually run

| check | result |
|---|---|
| `tools/trial_population_reconcile.py` twice → `cmp` | byte-identical (deterministic) |
| `trial_population_reconcile.py --strict` | exit 1 — correctly flags the 218-pair taxonomy drift |
| `h149_midcap_gross_profitability.py --self-check` | exit 0, `unmodified=True` |
| `pytest tests/test_profit_program_math_2026_11_20.py tests/test_money_ready_verdict.py tests/test_hypothesis_status.py` | **81 passed** |
| registry JSON parse + `id`/`status` readback | `H-149` / `UNTESTED` |
| conflict-marker scan | clean |

## Not done / next

- `NB_TRIALS_BY_CLASS` still holds the primary values; adopting the union
  (EQUITY 19→67, ETF 12→49) is a verdict-affecting change and needs its own flip
  report.
- The strategy-name **crosswalk** (`at_raw_picks.source_system` ↔ pipeline
  `strategy`) is the real fix for the bracketed N. Until it exists the bracket
  cannot be closed.
- The two duplicate ids in the other agent's uncommitted block are flagged, not
  fixed.
- Live `/audit` verification still needs a deploy publishing the merged artifacts.
- The audit2 single-cost-rule fix and its unsourced slippage percentages remain
  untouched.
