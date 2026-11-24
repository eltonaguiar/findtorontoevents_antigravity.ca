# 2026-11-20 — Ledger population + survivorship fixes on `/audit` money-ready verdict

**Surface:** `findtorontoevents.ca/audit` (via `alpha_engine/money_ready_verdict.py` → `audit_dashboard/data/money_ready_verdict.json`)
**Goal advanced:** Goal #1 (phenomenal per-asset-class performance)
**Type:** Measurement correctness. **No strategy, gate, threshold, or verdict changed.**
**Plan of record:** `docs/AUDIT_SURFACE_CONSOLIDATION_PLAN_2026-11-20.md` (§ P1-6, P1-7)

---

## What was broken

Three defects, all in how the money-ready ledger *reports*, not in how it decides.
None of them required statistics to detect — each was visible in the shipped JSON.

### 1. Two different populations published under comparable names

`n` counted the class's own picks from the JSON source (`closed_picks` /
`dashboard_fallback`). `n_resolved` was `_sizing_n`, sourced from the
`at_signal_outcomes` intrabar overlay. **Different cohorts**, published side by
side with no flag.

A "resolved" subset can never exceed its parent, so `n_resolved > n` is
arithmetically impossible. The shipped file violated it on **5 of 11 classes**:

| Class | `n` | `n_resolved` | Impossible by |
|---|---|---|---|
| COMMODITY | 27 | 234 | +207 |
| FOREX | 458 | 634 | +176 |
| FUTURES | 17 | 62 | +45 |
| EQUITY | 213 | 257 | +44 |
| ETF | 29 | 53 | +24 |

The 2026-11-19 fix had already corrected the same class of bug for `wr` (it
published the overlay's `_sizing_wr` under the class's own name). `n_resolved`
was left behind.

### 2. Survivorship bias in the intrabar ledger

`_intrabar_truth_map()` selected `intrabar_status IN ('TP_HIT','SL_HIT')`,
dropping every `TIME_EXIT` — **1,695 of 6,928 genuinely-resolved trades
(24.6%)**. Trades that hit neither target nor stop are exactly the ones that
decide whether a "2:1 reward:risk" book pays. `wr` was therefore a
decided-only number presented as the class's win rate.

### 3. `TIME_EXIT` on still-open rows

**40,228** rows carried `intrabar_status='TIME_EXIT'` with `closed_at IS NULL`
and `intrabar_pnl_pct=0.0000`. `TIME_EXIT` asserts "closed at the horizon",
which cannot be true for an open position. Those phantom 0.0% break-evens leak
into any aggregation that includes TIME_EXIT.

### Corrected: a claim in the plan doc that was simply wrong

The plan's original **P1-7** asserted the ledger publishes `NOT_READY`/`WATCH`
for under-sampled classes and proposed a new `NO_EVIDENCE` verdict at
`n_resolved < 30`. Verified against the shipped file: **0 violations**.
`MIN_N_CLASS = 100` (`money_ready_verdict.py:155`) already routes every class
below the floor to `INSUFFICIENT_DATA` before any other gate runs. P1-7 is
rewritten as the `n_resolved > n` finding above. No fifth verdict was added.

---

## What changed

### `alpha_engine/money_ready_verdict.py`

- **New `_population_invariant(n, n_resolved, data_source, sizing_source)`.**
  Pure function returning `population_mismatch` + `population_note`. Wired into
  the class results dict. Publishes the violation instead of hiding it. The
  verdict is untouched — it already gates on `_sizing_n`, the honest cohort.

- **`_intrabar_truth_map()` now emits both cohorts.** `n` / `wr` / `pf` /
  `source` are byte-identical to before, so **no previously-published number
  moves**. Added: `n_all`, `wr_all`, `pf_all`, `n_time_exit`,
  `time_exit_share`, `n_ambiguous`, `survivorship_gap_pp`.

  The all-status query guards on `COALESCE(intrabar_horizon_bars,0) > 0` so the
  40k mislabelled open rows (defect 3) cannot dilute `wr_all` toward 0.5.
  Verified safe: applying the same guard to the *decided* cohort changes its row
  count by exactly **0** (5,233 → 5,233).

### Measured effect — the bias runs BOTH ways

Assuming "decided-only always flatters" would have been wrong:

| Class | n | wr | n_all | wr_all | gap (pp) |
|---|---|---|---|---|---|
| ETF | 53 | **3.77%** | 85 | **20.0%** | **−16.2** |
| FOREX | 634 | **31.6%** | 1266 | **41.0%** | **−9.5** |
| COMMODITY | 234 | 40.2% | 316 | 43.0% | −2.9 |
| FUTURES | 62 | 37.1% | 133 | 39.9% | −2.8 |
| CRYPTO | 3726 | 35.8% | 4470 | 38.2% | −2.4 |
| EQUITY | 257 | **60.3%** | 333 | **58.0%** | **+2.4** |

For ETF and FOREX the decided-only cohort was *harsher* than reality. Notable
correction: **FOREX `pf_all` = 0.795**, not 0.640 — still below 1.0, still
unprofitable, but 20% less catastrophic than previously reported. **ETF
`pf_all` = 0.108** — the near-total loss is real and is *not* a survivorship
artefact.

**Consequence for the north star: nothing here makes any class money-ready.**
Zero classes pass. This fix makes the *reporting* honest, which is a
precondition for ever finding a real edge — it does not create one.

---

## Verification

```
$ python3 -m py_compile alpha_engine/money_ready_verdict.py
COMPILE OK

$ python3 -m pytest tests/test_money_ready_ledger_population.py \
                   tests/test_audit2_no_escape_hatch.py -q
14 passed, 1 xfailed in 0.50s
```

The one `xfail` is `test_no_time_exit_with_null_closed_at` (defect 3). It is
deliberately left failing-but-expected because the fix is a production `UPDATE`
and per repo policy that needs explicit owner approval. Suggested backfill:

```sql
UPDATE at_signal_outcomes
   SET intrabar_status = 'OPEN'
 WHERE intrabar_status = 'TIME_EXIT'
   AND closed_at IS NULL;
-- 40,228 rows, 2026-11-20. Run inside a transaction; back up first.
```

Remove the `xfail` marker once that has run.

**Proof the tests are load-bearing:** all four were first run against the
*unmodified* generator and failed with the real defects (5 cohort violations,
40,228 mislabelled rows). They were then retargeted from the shipped JSON to the
generator, so the suite does not go red for an hour waiting on the hourly
publisher.

---

## Not done, deliberately

- **No production mutation.** The 40,228-row backfill is documented, not
  executed.
- **No verdict, threshold, or gate touched.** Waves 3–4 of the plan (one
  resolver, ATR-normalised stops) change what the numbers *say* and need
  separate sign-off.
- **Root cause of the near-zero win rates is unchanged and still open:** every
  strategy hardcodes a fixed-percentage stop with no volatility normalisation
  (FOREX 0.3–0.5%, EQUITY 4.5%, ETF 3.0%). Barrier math says ETF should win
  ~37% against its own stops; observed clean subset 3.8%. **Do not draw strategy
  conclusions from wave-1 data** — current numbers support "no edge is visible
  through a fixed 3% stop", not "no edge exists".
