# 2026-11-19 — Intraday money-path stop, forward-evidence panel, POSITION pod

## What was broken / missing

1. **A measured bleed was documented but not acted on.** The BH-corrected slice
   scan found two pre-committable slices that lose to simply holding the same
   instrument over the same window:

   | slice | alpha/pick | 95% CI | n | q |
   |---|---|---|---|---|
   | `class_tf:CRYPTO/INTRADAY` | −0.155% | [−0.260, −0.053] | 1,581 | 0.015 |
   | `class_tf:ETF/INTRADAY` | −0.265% | [−0.488, −0.033] | 256 | 0.073 |

   Both still carried full money-path status, so the largest measured loss in the
   book was being sized.

2. **`/audit3` computed the forward gate and rendered none of it.** `forward_gate`
   appeared zero times in `audit_dashboard/audit3.html` even though the tribunal
   enforces it (`enforced: true`, 430 forward rows, fingerprint `5771c6fac172ca46`).
   The strongest promotion gate was invisible on the page that exists to explain
   promotion.

3. **No POSITION-timeframe hypothesis existed**, so the only positive
   pre-committable slice (`class_tf:CRYPTO/POSITION` +2.006%/pick, n=145, q=0.001)
   had nothing to accrue forward rows against.

## What changed

* **`alpha_engine/intraday_stop.py`** (new) — one policy source: `SHADOW_ONLY =
  {CRYPTO/INTRADAY, ETF/INTRADAY}`, `annotate_pick()`, `annotate_picks()`,
  `annotate_buckets()`, `alpha_effect()`, CLI for both the payload and the
  alpha-rows sidecar. Rows are annotated, never deleted:
  `money_path` / `shadow` / `shadow_reason`.
* **`audit_trail/dashboard_generator.py`** — one call after the existing sports
  leak guard annotates `active`, `smart_picks`, `recent_closed` and writes a
  `payload["intraday_stop"]` summary. `smart_picks` is the sizing list, so its
  shadow rows are **moved into `picks.shadow_picks`** (still in the payload,
  still tracked); `active` keeps every row, flagged, for research.
* **`audit_dashboard/audit3.html`** — new **Forward Evidence** tab: ledger row
  count, fingerprint, enforced flag, per-pod forward n vs min n with progress,
  eligibility and reason, and the hypothesis clocks, all read from the
  `forward_gate` block that was already in `audit3_ledger.json`. A **G8 forward
  evidence** row was also added to the overview gate list so the gate is visible
  where the promotion story is told.
* **`reports/hypothesis_registry.json`** — **H-144** `position_timeframe_selection`
  (CRYPTO), status `FORWARD_SHADOW`, with the post-hoc disclosure written into
  `data_sample_lock`: the motivating slice was measured on the same ledger the
  tribunal judges, so only rows closed after 2026-11-19 may judge it.
* **`reports/audit3_confirmatory.json`** — **POD-CRYPTO-POSITION**, status
  **`observe`** (not `pre_registered`), so `_pod_for()` cannot confer
  confirmatory status on it; it accumulates shadow rows only.
* **`reports/intraday_stop_effect_2026-11-19.json`** — the measured effect below.

## Measured effect (live, 2026-11-19 book)

`python3 alpha_engine/audit3_selection_alpha.py --picks ... --rows-out` then
`python3 alpha_engine/intraday_stop.py --rows ... --json-out ...`:

| book | mean selection alpha/pick |
|---|---|
| without the stop | **−0.1306%** (n=2,475) |
| with the stop | **−0.0159%** (n=638) |
| improvement | **+0.1147%/pick** |

Per class after the stop: CRYPTO kept n=388 at **−0.1894%** (still negative),
ETF kept n=10 at +3.5997% (sample too small to claim anything), EQUITY unchanged
at +0.114% (n=240).

**The stop removes ~88% of the measured bleed and does not make the book
profitable.** CRYPTO's remaining SWING/POSITION mix is still negative; `tf:SWING`
was −1.603%/pick in the scan but did **not** survive BH (q>0.10), so it stays
measured, not filtered. The next cut has to be earned the same way.

## Verification

* `pytest tests/test_intraday_stop.py` — 6 passed (policy scope, no row loss,
  bucket counts, sizing-list partition, idempotent second pass, alpha effect
  arithmetic).
* `pytest tests/test_intraday_stop.py tests/test_audit3_tribunal.py
  tests/test_audit3_expectancy_gates.py tests/test_audit3_forward_gate.py
  tests/test_audit3_enforcement.py tests/test_alpha_slice_scan.py
  tests/test_audit3_selection_alpha.py` — 92 passed.
* Generator edit applied at a unique anchor; `python -c "import
  alpha_engine.intraday_stop"` used by the wiring is import-guarded for direct
  script execution.
* Live run produced the table above (`rows_scored: 2475`), so the evidence file is
  a real measurement, not a fixture.

## COMS handoff (same day)

The eight uncommitted COMS handoff files were preserved on
`rescue/coms-handoff-2026-11-19` (`af94122`), **not merged**. Two exclusions:
`config/api_model_roster.json` was a probe artifact (one provider, 3 models) that
would have deleted the 984-line roster, and `audit3_tribunal.py` would have
reverted main's G8 repeated-looks + N1-N4 gates. Its real contributions were
forward-ported: G9 selection alpha is now an actual promotion gate and DSR uses
the global trial count. That branch is the other agent's work to merge.

## Limits (read before quoting)

* The stop is enforced **in the payload**, not in the DB `money_ready` generator,
  which groups by symbol/class and has no timeframe column. Any consumer that
  ignores `money_path` still sees shadow rows.
* `smart_picks` partitioning is new behaviour: a consumer that assumed
  `smart_picks` contained every high-conviction pick will now see fewer rows and
  must read `shadow_picks` for the rest.
* H-144's ingestion condition (timeframe-keyed in `classify()`) lives on the COMS
  rescue branch because it extends that branch's `classify()` signature; until
  that branch merges, H-144 accrues **0** forward rows. Its pod clock will read
  `n_forward: 0, eligible: false` — correct, not broken.
* Mean alpha is a per-pick average, not a portfolio return, and the shadow book
  is not cost-adjusted beyond the measured class slippage.
