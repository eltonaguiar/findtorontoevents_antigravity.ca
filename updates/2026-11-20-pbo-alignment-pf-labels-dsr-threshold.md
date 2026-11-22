# PBO aligned by exit time, PF always carries its denominator, DSR threshold decided

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)

Three follow-ups to #1017: the PBO misalignment I found but did not fix, the PF
labelling rule I adopted but had not enforced, and the DSR threshold I was asked
to decide.

## 1. PBO matrices are now aligned by exit timestamp

**What was broken.** Both callers built the `(T x S)` matrix from each strategy's
*own* pick sequence: `tools/run_anti_overfit_audit.py` did `cols = [v[:T] for v in
eligible.values()]`, and `tools/anti_overfit_audit_sidecar.py` did
`np.asarray(strat_returns[s][-min_len:])`. Neither `v[:T]` nor `[-T:]` places a
pick by *date*. Two strategies that traded in different months were stacked so
that row 0 held A's January trade beside B's March trade, and every CPCV split
therefore compared eras. The PBO logit was partly measuring the calendar.
Nothing was fabricated — the numbers were just not about the same time.

**What changed.** `alpha_engine/anti_overfit_validator.py` gains
`align_returns_by_period(series_by_strategy, min_obs, period, min_rows)`: it
parses each pick's exit timestamp, floors it to a day, aggregates mean return per
(strategy, period), and builds one matrix over the **union of periods** with
`0.0` where a strategy held nothing that period ("no position, no P&L"). It
escalates day -> week -> month when there are too few rows for CPCV, and reports
which rungs it used. Unparseable timestamps are **dropped and counted**, never
guessed.

`cpcv_pbo()` gains `period_index=`: the real period stamps become the fold
`pred_times`/`eval_times`, and the purge embargo is derived from the median
spacing between rows instead of assuming a daily grid. A length mismatch or an
unsorted index raises.

Both callers now pass timestamps end to end: `run_anti_overfit_audit.py` carries
`(closed_at, return)` per pick and reports `matrix=133x12 aligned by exit ts (D,
coverage 24.75%)`; the sidecar selects `closed_at` in `fetch_strategy_series()`
and publishes the alignment block in `anti_overfit_audit.json`
(`portfolio_diagnostics.alignment`).

**What this changed in the numbers.** `kimi_riseoftheclaw` PBO went **0.286 ->
0.143** on the same ledger: same strategies, same picks, different rows. And
`luxalgo_filters` and `alpha_engine` used to report a PBO at all; now they
correctly report `n/a`, because after alignment only one strategy in each has
>= 30 timestamped picks. The old numbers existed because misaligned sequences
always yield enough rows.

## 2. Every published PF now carries its denominator

**What was broken.** CRYPTO was published at PF **1.31**, **0.83** and **0.26**.
All three are the same formula on different populations, and no reader could tell
which was the class figure. A PF without `n` and its cost treatment is not a
measurement.

**What changed.** `alpha_engine/pf_basis.py` is the single renderer:
`format_pf(0.8339, 6874, cost_bps=9.85) -> "PF 0.83 (n=6,874, net 9.8bp)"`, plus
`pf_record()` for JSON (`pf_label`, `pf_n`, `pf_cost_bps`, `pf_basis`,
`pf_population`). An unmeasured cost stays `None` — never `0.0`, because "not
measured" and "free" are different claims.

Wired into every surface that publishes a PF: `audit_trail/dashboard_generator.py`
(asset-class health and system stats, plus the canonical stub),
`alpha_engine/money_ready_verdict.py` (`_class_stats` and the class verdict,
including `policy_clean_pf_label`), `alpha_engine/audit3_tribunal.py` (`pf_n`,
`pf_basis`, `pf_cost_pct`, `pf_label`), and
`tools/anti_overfit_audit_sidecar.py` (per-strategy). The dashboard template now
displays `(n=...)` beside PF at every sample size — previously only below n=30,
so the tile showed a bare ratio exactly when the sample was large enough to
matter.

`tools/pf_label_audit.py` holds the enumerated list of publishing surfaces and
verifies each emits a denominator: **6/6**. It deliberately does not scan the ~60
backtest/scraper scripts that compute a PF for their own report and publish no
class figure.

## 3. DSR threshold: stays 0.95

Measured across the 80 scored strategies: 6 pass at 0.99, 6 at 0.95, 7 at 0.90,
7 at 0.50 -> 0.70, and 10 at 0.50. Median DSR **0.0033**, p75 **0.0**.

Lowering the gate to 0.50 — the module's own "almost certainly overfit" line —
converts 4 of 74 failures. The threshold is not the binding constraint, so it
stays at 0.95 rather than being tuned until the build goes green. Full reasoning,
including the consequence (the audit-dashboard job stays red until the book
changes) and the actual lever (demote the uncertified strategies rather than
lower the bar), is in `reports/dsr_threshold_decision_2026-11-20.md`.

## Verification

```
python3 -m pytest tests/test_pbo_alignment_2026_11_20.py \
                    tests/test_pf_basis_2026_11_20.py \
                    tests/test_anti_overfit_validator.py \
                    tests/test_anti_overfit_gate_2026_11_20.py -q   -> 29 passed
python3 tools/anti_overfit_audit_sidecar.py --check-only --gate   -> exit 2 (74/80)
python3 tools/run_anti_overfit_audit.py --top 3 --B 200 --gate    -> exit 2 (3/3)
python3 tools/pf_label_audit.py                                   -> 6/6 labelled
python3 tools/crypto_pf_reconcile.py                              -> table regenerated
```

The alignment tests pin the bug directly: with A trading in January and B in
February, **no matrix row** may contain a non-zero value for both, and a pick
dated 2026-01-05T23:00 must land in the same row as 2026-01-05T01:00. The PF
tests pin that an unset cost never renders as `net 0.0bp`, and that both
publishers actually emit `pf_label`.

## Limits

- Alignment aggregates to a period, so two picks inside one day collapse to their
  mean. That is the correct resolution for cross-strategy comparison but it is a
  resolution choice, recorded in `info["period"]` and `info["coverage_pct"]` on
  every run rather than hidden.
- Zero-filling absence as 0.0 makes a rarely-trading strategy look flat, not
  risky. PBO compares columns; it still cannot tell a strategy that was
  deliberately flat from one that was not deployed.
- `tools/pf_label_audit.py` is a source-marker audit, not a proof: it checks that
  the renderer is used near a PF site, not that the label equals the value.
- The PF labels describe the cohort each surface counts. They do not reconcile
  the cohorts to each other; `tools/crypto_pf_reconcile.py` does that for CRYPTO.
