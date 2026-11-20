# P0.5 trial count, regime-at-entry stamp, corrected cost gate

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)

## 1. What was broken — the promotion gate applied no multiplicity correction

`alpha_engine/money_ready_verdict.py` defines `NB_TRIALS_BY_CLASS` (M-061a) with a
comment stating that `nb_trials` "must reflect the actual number of independent
strategies/systems tested per class" and that "nb_trials=1 applies zero correction
and is statistically meaningless for real-money readiness".

`_dsr_gate()` then did exactly that:

```python
# nb_trials=1 — we're testing the class aggregate, not a selected-best strategy
dsr = deflated_sharpe_ratio(..., nb_trials=1, ...)
```

So the constant existed, was documented as mandatory, and was never read. Every
class was evaluated as if it were the *only* strategy ever tested, which is the
single most favourable possible assumption for a deflated Sharpe.

This was the real content of the P0.5 item: not "add a counter", but "the gate
already had the count wired to a literal".

## 2. What changed

**`alpha_engine/trial_counter.py` (new).** A persistent, atomic (tmp + `os.replace`)
JSON counter at `reports/trial_counter.json` holding per-family counts and a
`total`. `effective_n_trials(local, family)` returns
`max(local, global_total, family_total, 1)` — a local run can never *lower* the
figure, so the correction is monotone-conservative: more trials can only make
promotion harder. Missing/corrupt file degrades to `local` rather than raising.

**`money_ready_verdict._dsr_gate()`** now takes `asset_class`, reads
`NB_TRIALS_BY_CLASS`, and raises it through `effective_n_trials`. The count is
hoisted above the import guard so **every** return path (not importable, n too
small, zero variance, non-finite DSR, normal) reports `nb_trials` — the first
attempt reported it on one path only and the tests caught the `KeyError`.
Call site passes `asset_class=ac`.

The counter file is deliberately **not** seeded: `effective_n_trials` returns the
class constant until real trial counts are recorded, so this change does not
invent a number. Populate with
`trial_counter.record(n, "<CLASS>")` from the harness that actually runs trials.

**`alpha_engine/entry_regime.py` (new).** Pure `classify_regime(closes, index)` →
`regime_trend` (close vs 200d SMA), `regime_vol` + `regime_vol_percentile`
(20d realised vol ranked against its own history), `regime_bars_available`, and
`stamp_regime_at_entry(pick, closes, index)` adding `at_entry_*` fields. Uses
only bars up to `index` — tested by appending future bars and asserting the past
classification is byte-identical. This is the missing field behind the peer's
"did 65% of exits hit the time cap in one regime?" question; it was unanswerable
because trade rows carried no regime at entry.

**`alpha_engine/cost_gate.py` (new).** The first pass compared the *full*
reversion distance `|s|·σ` against round-trip cost. Exiting at `|s_exit|`
captures only `(|s_entry|-|s_exit|)/|s_entry|` of it — 60% at the 1.25/0.5
calibration — so the edge was overstated by 1/0.6 ≈ **67%**. `captured_fraction`,
`captured_edge_bps` (fraction in, bps out) and `should_trade` implement the
corrected comparison.

## 3. Bug found by the tests themselves

`captured_edge_bps` was first written as `... * sigma_eq_pct * 100` while
documented as taking a percent, so a 2% σ produced 1.5 bps instead of 150 bps —
a 100× understatement of the very edge the gate exists to measure. The unit was
made explicit as a *fraction* with `* 10_000`, and a test pins 150 bps at
σ=2%, s=1.25 so the regression cannot return.

## 4. Verification

From a clean worktree at `origin/main` (`0560523e551`):

```
python3 -m pytest tests/test_profit_program_math_2026_11_20.py \
                 tests/test_profit_program_policies_2026_11_20.py -q
16 passed
```

- `money_ready_verdict.py` compiles (`py_compile`, `doraise=True`).
- Direct call: `_dsr_gate([0.004,-0.002,0.006]*40, asset_class="CRYPTO")` →
  `nb_trials: 14` (was 1).
- Monotone test: CRYPTO (14) never scores *higher* DSR than COMMODITY (3).
- Regime test: appending future bars leaves a past classification unchanged.
- Counter test: local 3 vs global 670 → 670; missing file → local, floor 1.

## 5. Not done / limits

- The counter file is empty, so today the gate uses `NB_TRIALS_BY_CLASS` only.
  The measured distinct strategy/source keys in `dashboard_data.json` are
  CRYPTO 11, EQUITY 7, FOREX 5, ETF 5, BOND 3, COMMODITY 2 — below the constants
  for CRYPTO (14) and BOND (3 vs 3). Reconciling the two counts is open work;
  the constant is the conservative choice and was left untouched.
- `regime_at_entry` is implemented but not yet *applied* to historical picks:
  the dashboard rows carry no entry timestamp (`entry_time` is empty on the
  sampled row, only `closed_at`), so stamping the full resolved book needs an
  entry-time source first.
