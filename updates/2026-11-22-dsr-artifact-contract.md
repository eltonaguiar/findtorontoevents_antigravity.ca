# The DSR artifact is a live gate input, not a report — and my fix almost changed what the system trades

**Date:** 2026-11-22
**Files:** `tools/deflated_sharpe.py`, `tests/test_dsr_artifact_contract.py`,
`reports/deflated_sharpe_corrected_2026-11-22.json`
**Related:** `updates/2026-11-22-dsr-tool-four-defects-fixed.md` (T6)

---

## What I nearly shipped

T6 fixed four real defects in `tools/deflated_sharpe.py` and regenerated
`tools/deflated_sharpe_results.json`. I treated that regeneration as a consequence of
the fix.

It wasn't. **`tools/deflated_sharpe_results.json` is an input to production pick
filtering**, not a report:

```python
# alpha_engine/eagle_gates.py -> _load_dsr_noise()
# alpha_engine/dsr_pick_filter.py -> get_dsr_survivors() / get_dsr_noise()
for entry in d.get("all_strategies", []):
    if not entry.get("survives", False):
        noise.add(entry["key"])          # <-- this set SUPPRESSES picks
```

Both modules build a "noise set" from `survives == False` and use it to block picks.
Changing what `survives` means changes what gets traded.

## The measured delta

Comparing the artifact before my change against the corrected one:

| | strategies | survive | **noise set** |
|---|---|---|---|
| before (2026-06-06, `annual_trades=2190`) | 45 | 29 | **16** |
| corrected (2026-11-22, measured rates) | 55 | 0 | **55** |

**21 previously-tradeable strategies flip to noise**, including the ones the old
artifact ranked *highest*:

```
luxalgo_confluence          (old: dsr 15.0783, "survives": true)
macd_rsi_m048               (old: dsr 13.5319, Sharpe_ann 43.93)
basket_corr_gate_mut        (old: dsr  9.4324)
quality-minus-junk          (old: dsr  9.3848)
crypto-momentum-scout, crypto_liquidity_wick_reversal_v1,
clone_hl_copy_lb_None, adx-trend-scout, forex-rsi-ema-scout,
donchian-stock-breakout, ema-ribbon-momentum-scout, mtf-align-scout,
price-accel-scout, intermarket-flow-scout, drawdown_recovery_rsi_eth,
atio-bb-squeeze-scout, cci-crypto-reversal, ... (21 total)
```

Deploying that inside a bug-fix commit would have **silently suppressed 21 strategies'
picks**. Nobody would have connected it to a DSR tooling fix, and the symptom would
have looked like "those strategies stopped emitting".

Note the cause is mostly **not** the gate threshold. Re-applying the *old* `z > 0` rule
to the *corrected* numbers also yields 1 survivor / 54 noise. The dominant change is
the **inflated Sharpe** (defect 3: hardcoded `annual_trades=2190`, a 46.8× multiplier).
Correcting arithmetic is what reclassifies the strategies; the 95% gate only moves the
last one.

## The fix: separate the correction from the enforcement

1. **The live artifact was restored** to its pre-change contents (`survives: 29/45`,
   `annual_trades: 2190`). Verified by hash: `eagle_gates._load_dsr_noise()` returns
   **16** strategies, `dsr_pick_filter.get_dsr_survivors()` returns **29** — identical
   to pre-change, and `luxalgo_confluence` remains tradeable.

2. **Corrected results now go to a review path by default:**
   `reports/deflated_sharpe_corrected_<date>.json`. Writing the live artifact requires
   an explicit `--deploy` flag.

3. The tool prints, on every non-deploy run:

   > `::notice::WROTE TO A REVIEW PATH. tools/deflated_sharpe_results.json (read by
   > the live pick gates) was NOT touched. Deploying the corrected artefact changes
   > the DSR noise set from 16 to 55 strategies — a policy decision that needs review,
   > not a side effect of a bug fix.`

**A tooling fix must not change what the system trades.** The corrected maths is right;
deploying it is a decision for the operator, with the 21-strategy list in front of them.

## Regression tests pinning it

`tests/test_dsr_artifact_contract.py` — 8 tests:

| test | pins |
|---|---|
| `test_live_artifact_has_the_fields_consumers_read` | `key`/`survives`/`trades` cannot vanish from the artifact |
| `test_summary_matches_the_rows` | summary counts cannot drift from the rows |
| `test_both_consumers_compute_the_same_noise_set` | `eagle_gates` and `dsr_pick_filter` cannot disagree |
| `test_noise_set_is_not_everything` | fails loudly if **all** strategies become noise — with a message saying that is a deliberate policy decision, not a silent outcome |
| `test_default_run_targets_a_review_path_not_the_live_file` | a bare run cannot write the live file |
| `test_deploy_flag_targets_the_live_file` | `--deploy` does |
| `test_live_artifact_untouched_by_a_dry_run` | end-to-end byte-hash check |
| `test_corrected_artifact_is_a_distinct_file_when_present` | corrected output carries `semantics` + `headline_withdrawn`, and is not *less* harsh than live |

```
python3 -m pytest tests/test_dsr_artifact_contract.py -q
  8 passed
```

## The general lesson

The repo's Wire-Up Rule exists for this shape of error in the other direction — a module
with no caller is inert. This is the mirror image: **a module with a caller is load-bearing,
and changing its output is a production change.** A file under `tools/` that something in
`alpha_engine/` reads at pick time is not tooling. Before regenerating any artifact next
time, the first question is "who reads this, and what do they do with it" — not "is the
new number correct".

## What is still open

Whether to deploy the corrected artifact. It would block 21 strategies whose measured
edge was created by a 46.8× annualisation error. That is very likely the right call, but
it is the operator's, and it is one command (`--deploy`) once agreed.

Zero capital sanctioned. Not investment advice.
