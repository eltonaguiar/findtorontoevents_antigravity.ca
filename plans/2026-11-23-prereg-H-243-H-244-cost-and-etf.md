# Pre-registration — H-243 (cost-of-record re-measurement) and H-244 (ETF universe)

**Filed:** 2026-11-23, BEFORE the first run of either variant. M-107.
**Parent:** H-242 (44-name, 10-year, 10bp/side) — `reports/h242_pit_10y_2026-11-23.md`.

## Why these two, and what they can and cannot do

H-242 passed its CI gate at 10 bp/side. Two questions follow, and neither may be answered by looking
at the data first:

1. **H-243 — does the pass survive the cost we actually measured?** The cost reconcile of record is
   **4.0124 bp round trip** (range 0.9756–7.3804, 2× stress 8.0248) on the same 191 names. Charging
   20 bp RT was conservative. Re-running at the record cost can only *raise* the mean return; it
   cannot create an edge that was not there. It is a sensitivity, not a new discovery, and it will be
   reported as such.
2. **H-244 — is the effect US-equity-specific?** The same rule on the harness's 10-name ETF universe
   (`per_class_edge_harness.UNIVERSES["ETF"]`, frozen since 2026-11-22). If cross-sectional momentum
   is a real factor it should appear in ETFs; if it appears only in single names, it is a
   small-cap/liquidity artifact and should be named one.

## Frozen design (both)

- Rule: `xsmom(lookback=126, top_k=3, rebal=21)`, long-only, weights go FLAT when a name leaves the
  top 3 (the harness raises if exposure ever exceeds 1).
- Windows: **W10 = 2016-11-21..2026-11-20** (primary, same as H-242) and W5 = 2021-11-22..2026-11-19
  (comparability control).
- Estimator: moving-block bootstrap (harness `block_bootstrap`, 2,000 resamples), 95% interval.
- Benchmark: SPY for both.

## H-243 specifics

- Universe: the 44-name PIT list (`reports/pit_equity_universe_20261122.json`), unchanged.
- Cost: **2.0062 bp per side** (= 4.0124 RT). No other parameter moves.
- Verdict vocabulary:
  - `PASSES_AT_RECORD_COST` — W10 CI-LB > 0 at record cost **and** the mean rises by no more than the
    cost saving accounts for (i.e. no unexplained jump).
  - `FAILS_EVEN_AT_RECORD_COST` — W10 CI-LB <= 0.
- It is explicitly **not** a new trial for edge purposes: it re-measures one already-spent trial at a
  lower cost. It is still counted in N, because counting honestly means counting, not choosing.

## H-244 specifics

- Universe: **10 ETFs** — SPY, QQQ, IWM, EFA, EEM, TLT, GLD, XLE, XLF, SMH. Frozen; no substitutions
  after seeing a result. Breadth is 10, so top-3 is 30% of the universe and the book is concentrated;
  that is a known handicap of the cell, recorded now rather than after it fails.
- Cost: **20 bp RT** (harness ETF cost) as primary; **4.0124 bp RT** reported alongside.
- Verdict vocabulary:
  - `PASSES_W10` — W10 CI-LB > 0 at 20 bp RT.
  - `PASSES_ONLY_AT_RECORD_COST` — fails at 20 bp RT, passes at 4.0124.
  - `FAILS` — CI-LB <= 0 at both.

## What both explicitly cannot do

Neither clears the multiplicity gate. H-242's deflated Sharpe is computed in the same artefact batch,
and both variants add trials. A pass here is a *consistent-direction* result, never a promotion.
