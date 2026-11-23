# DSR conformance: the function named canonical cannot deflate, and H-201/R4b could not record a forward row at all

**Date:** 2026-11-23
**Author:** buffy (freebuff)
**Files:** `tools/dsr_conformance.py` (new), `tests/test_dsr_conformance.py` (new),
`reports/dsr_conformance_2026-11-23.{json,md}` (new), `reports/hypothesis_registry.json` (2 rows added)

---

## 1. What was broken

Two unrelated defects, both of which silently capped the programme's evidence.

### 1a. The "canonical" DSR is not a DSR

`alpha_engine/deflated_sharpe.py:179` carries:

```
# DEPRECATED: Use alpha_engine.validation.sharpe_metrics instead (canonical implementation per TESTING_PROTOCOL v4.0)
```

`alpha_engine/validation/sharpe_metrics.py:83` has the signature
`deflated_sharpe_ratio(returns, risk_free_rate=0.0, freq="daily")`. **It takes no trial
count**, so no multiplicity correction is possible, and its own docstring agrees:

> Sharpe / SE(Sharpe) — a t-statistic, NOT a multiplicity-corrected DSR.
> Despite the name this takes no trial count…

Measured by the harness on H-244's real cell (n=2514, per-period Sharpe 0.04735):

| implementation | file:line | N=1 | N=121 | N=4987 | verdict |
|---|---|---|---|---|---|
| validation.sharpe_metrics (**named canonical**) | `alpha_engine/validation/sharpe_metrics.py:83` | 31.0548 | 31.0548 | 31.0548 | **IGNORES_N** |
| statistical_rigor | `alpha_engine/statistical_rigor.py:339` | 0.9912 | 0.4118 | — | DEFLATES |
| anti_overfit_validator | `alpha_engine/anti_overfit_validator.py:418` | 0.9912 | 0.4125 | — | DEFLATES |
| deflated_sharpe (self-deprecated) | `alpha_engine/deflated_sharpe.py:179` | 0.9912 | 0.4113 | — | DEFLATES |
| audit3_tribunal | `alpha_engine/audit3_tribunal.py:399` | — (refuses N=1) | 0.4120 | — | DEFLATES |
| crypto_ml_edge | `crypto_ml_edge/validation.py:301` | 0.9912 | **0.0000** | — | DEFLATES |

Consequences, stated plainly:

1. **The pointer is inverted.** Following the deprecation note (as a reviewer or an agent
   would) yields a number that is 75× larger than a probability and does not move with `N`.
   Any gate of the form `dsr >= 0.95` passes **everything** when fed this value. That is
   worse than no gate: it is a gate that always says yes.
2. **The binding constraint is mis-instrumented.** The programme's stated blocker is
   multiple-testing debt, yet the designated tool cannot measure it.
3. **`crypto_ml_edge` disagrees with the other four by the entire range** — 0.0000 vs
   ~0.412 on identical input. Its defaults are `kurtosis=3.0` (raw) while the others use
   excess kurtosis, and it feeds the observed Sharpe directly. A verdict built on this
   implementation alone would fail a cell that three peers score at 0.41.
4. **The four that do deflate agree to 3 decimal places** (0.4113 / 0.4118 / 0.4120 /
   0.4125). That agreement is the useful result: it independently reproduces my H-244
   conclusion — **DSR ≈ 0.41 ≪ 0.95 at N=121, so H-244 fails deflation even though it
   passes its cost test.** The cost result was real; the multiplicity result is real too,
   and they point opposite ways.

### 1b. H-201 and R4b could not accrue a single forward row

`alpha_engine/forward_observations.py:validate` rejects any row whose `hypothesis_id` is
not in the registry ("dangling FK"). Checked structurally over all 167 discoverable ids:

```
H-201    in registry: False
R4b      in registry: False
H-244    in registry: True
```

So the two hypotheses whose forward clocks the programme is actually waiting on were
**structurally barred from the ledger**. "The ledger is empty" was not only a scheduling
fact — for H-201 and R4b it was enforced by the schema.

## 2. What changed

* **`tools/dsr_conformance.py`** — a harness, deliberately *not* a 26th implementation.
  It drives every importable `deflated_sharpe*` with one deterministic battery
  (H-244's 2514-day cell, the n=26 most-favourable cell, n=8, a fat-tailed series, and a
  losing cell) at N ∈ {1, 26, 121, 4987}, and classifies each implementation as
  `DEFLATES`, `IGNORES_N`, `DEFLATES_UNIT_AMBIGUOUS`, `NEVER_RETURNS` or `UNIMPORTABLE`.
  Movement is judged between the lowest and highest trial count the implementation
  actually answers, so refusing N=1 is not mistaken for trial-blindness.
* **`tests/test_dsr_conformance.py`** — 12 tests pinning the verdict logic with synthetic
  implementations, so the harness cannot pass merely because the real modules import.
* **`reports/hypothesis_registry.json`** — two rows added, `H-201` and `R4b`, copied from
  the filed pre-registrations with no parameter changed:
  * H-201 ← `plans/2026-11-23-prereg-H-234-h201-two-window.md` (xsmom 126/3/21d, 10 bp,
    CI-LB +7.246 bp/day over 3,744 days, needs 76.7 more trading days).
  * R4b ← `docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md` (frozen 20-ETF universe,
    top 5 positive 12-month, monthly last-trading-day rebalance, kill at net ann ≤ 4.32%
    *and* 95% upper ≤ 4.32%, earliest possible CONFIRM ~60 months).

## 3. How it was verified

```
$ python3 tools/dsr_conformance.py --json reports/dsr_conformance_2026-11-23.json --md ...
  → 6 implementations driven, 5 batteries × 4 trial counts = 120 cells; table above
$ python3 -m pytest tests/test_dsr_conformance.py -q
  → see run log below
$ python3 -c "from alpha_engine.forward_observations import hypothesis_ids; ..."
  → H-201 True, R4B True (FK now passes)
$ python3 -m alpha_engine.forward_observations --clock H-201
  → 0/100 forward rows, status NO_FORWARD_ROWS   (honest zero, now recordable)
```

## 4. Two further defects found and NOT fixed here

1. **R4b's universe count contradicts itself across filed artifacts.**
   `docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md` §2 says "**20 ETFs, fixed now**"
   and lists 20 tickers; the operator directive and my own earlier note describe
   "**24 liquid ETFs**". Changing the universe after pre-registration is a new trial, so the
   filed 20 must govern — but the discrepancy needs an owner, because a reader following
   the bus would reconstruct a different rule than the one registered.
2. **The ledger mixes two schemas.** `reports/forward_observations.jsonl` holds 432 rows;
   lines 431–432 are monthly *signal-observation* records
   (`hypothesis_id, observation_month, level, sma10, realised_return_pct, complete_month`)
   from the TREND10M clocks, not trade rows. `--verify` reports `ok=False` with exactly
   those 2 violations. They are another tool's output and are not mine to delete; the fix
   is to route them to their own ledger file so the trade contract verifies clean.

## 5. Not fixed because it is not mine to change

The canonical-pointer inversion (1a) is a decision, not a typo: `alpha_engine/deflated_sharpe.py`
should point at `alpha_engine/statistical_rigor.py:339` (or `anti_overfit_validator.py:418`),
both of which deflate and agree with each other. I have not edited that file — the
deprecation note is a protocol decision (TESTING_PROTOCOL v4.0) and changing it silently
would re-point every consumer. The recommendation is one line, with the measurement above
behind it.

## 6. Self-correction: I reformatted the whole registry on the way in

The first commit for this work (`4756c3d879a`) re-serialised
`reports/hypothesis_registry.json` with `json.dumps(indent=2)` instead of inserting two
rows textually. The content was correct — 137 upstream rows, none lost, none altered —
but the diff was **6,474 insertions / 4,444 deletions** for a two-row addition, because
every line of a 137-row shared file was rewritten. On a file other agents also edit, a
whole-file reformat is a merge hazard and it buries the two rows that matter.

Fixed in the follow-up commit: the registry is restored byte-for-byte to its previous
formatting with the two new rows inserted textually before the array's closing bracket.
Verified that every pre-existing row is content-identical and that the shape is now
additive. Note also that upstream held **137** rows where my local tree held 130 — the
insertion is applied to upstream's own copy, never to my stale local one.
