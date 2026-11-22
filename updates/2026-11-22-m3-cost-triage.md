# M3 — cost-measurement triage of the remaining UNKNOWN rows

**Date:** 2026-11-22 · **Tool extended:** [`tools/equity_cost_measure.py`](../tools/equity_cost_measure.py)
(`--classes-measure`) · **Artifact:** [`reports/equity_cost_measurement/class_cost_20261122.json`](../reports/equity_cost_measurement/class_cost_20261122.json)

Research measurement, not a feature. Read-only, no orders. This item was mostly about
**restraint**: deciding which UNKNOWN rows cost could actually decide, and refusing to
measure the rest.

## Headline

Of the **6 UNKNOWN rows** on the synthesis row set
([`22_FINAL_SYNTHESIS`](../docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md)):

- **0 are COST_ADDRESSABLE** in a way a measurement could move.
- **2 are being carried as "unknown" when the honest label is "cost cannot matter here"**
  (bond momentum, commodity momentum) plus a third that is cost-irrelevant for a
  different reason (FX carry is already NOT_INVESTABLE).
- **1 is ALREADY_SCHEDULED** (FX mean-reversion, `fx-cost-overlap.yml`).
- **2 are BLOCKED_OTHER** on data/provenance, not on cost (FX momentum, commodity
  term-structure carry).
- **1 is genuinely undecidable by cost** (funding carry: cost is *measured*, the missing
  ingredient is a funding regime + capacity + a survivorship-clean universe).

Tally is **recomputed from the rows, not hand-edited**, and is **unchanged**:
**0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN**.

## The triage table (all 6 UNKNOWN rows, with the arithmetic)

Costs are per-side unless marked RT. A row is COST_ADDRESSABLE only if
`gross edge ≈ plausible cost`; if `break-even cost = 0` the strategy loses with free
trading and no cheaper fill can rescue it.

| # | Row | Current label | Triage class | Deciding arithmetic |
|---|---|---|---|---|
| 1 | FX momentum (63d/21d) | UNKNOWN (provenance) | **BLOCKED_OTHER** | Gross itself is **−26.88 bp** (net −36.88 bp). That is a zero-cost *negative* gross, so cost is not the question: the missing fact is a machine-readable report of the −36.88 bp figure, which exists only in Markdown. If reproduced it is a zero-cost kill. |
| 2 | FX mean-reversion (5d/5d) | UNKNOWN | **ALREADY_SCHEDULED** | Gross **+4.30 bp**, break-even **4.3038 bp**. Measured upper-bound FX spread 7.533 bp RT is ~1.75× break-even → KILL at that cost. But the window-clustered CI at **1 bp** is **[−4.32, +11.09]** (includes zero), so cost is necessary but not sufficient. Weekday overlap run is automated in `.github/workflows/fx-cost-overlap.yml` and pending. |
| 3 | Commodity momentum (V1/V2/V3) | UNKNOWN (data-corrupted) | **COST_IRRELEVANT_ZERO_COST_KILL** | Break-even **0 bp/side**: V2 PF 1.114 and V3 PF 1.074 at 5 bp still give CAGR +0.47% and −0.67% vs a **4.32%** T-bill, and V1 is PF 0.757. None clears the hurdle even at zero cost → measuring cost is worthless. (The row stays UNKNOWN only because the *series* are roll-corrupted; buffy's objection was substantiated and closed NO CANDIDATE with two witnesses.) |
| 4 | Bond momentum (B1/B2/B3) | UNKNOWN | **COST_IRRELEVANT_ZERO_COST_KILL** | Break-even **0 bp/side** on all three. B1 PF **1.312** sits beside Sharpe **−0.550** and null **2.0** — the PF-inflation trap. Cost cannot turn a −0.550 Sharpe into an investable one. |
| 5 | Funding carry | UNKNOWN (was MARGINAL) | **BLOCKED_OTHER** (cost already MEASURED) | Crypto cost is measured: pair RT **45.524 bp** @1×. Break-even hold **16.398 d** vs median episode **1.93–2.33 d**. Even at the 30-day net **+2.42% APR vs 4.32%** T-bill it loses to cash. Missing: a ≥16.4 d funding regime, 27–32× capacity, survivorship-clean universe. None of those is a cost. |
| 6 | Commodity term-structure carry | UNKNOWN (BLOCKED_DATA) | **BLOCKED_OTHER** | **Zero second-month contract series on disk.** Roll yield `(front − second)/second` needs two contracts; synthesising one from the front month would invent the signal. Cost is unmeasured but irrelevant until the signal exists. |

Not in the UNKNOWN set but triaged because the brief names them: **FX carry** is
**COST_IRRELEVANT_HURDLE** (break-even **468.5 bp** vs measured ~7.5 bp RT → cost is ~60×
below the margin; it is settled by the 4.32% hurdle, Sharpe −0.126).

## What was measured (COST_ADDRESSABLE)

No UNKNOWN strategy row was COST_ADDRESSABLE. The brief flagged **ETF / INDEX / MEME**
as likely candidates, and those are asset *classes*. I measured their spread distributions
so a future row in those classes does not start from an assumption. Source: **yfinance
1-min bars, `period=5d`, 2026-11-16..20**, fetched **2026-11-22T22:53Z**. Tiingo IEX
returned **HTTP 429** (hourly allocation exhausted); live NBBO is therefore
`BLOCKED_NO_LIVE_NBBO`, not zero.

Median 1-min bar range = a rigorous **UPPER bound** on round-trip quoted spread (bid and
ask both lie inside `[low, high]`). It is **not** the NBBO.

| Class | n names | min | p25 | **median RT** | p75 | p90 | max | max/min |
|---|---|---|---|---|---|---|---|---|
| ETF (14) | 14 | 0.61 | 5.32 | **6.71** | 8.31 | 12.07 | 22.90 | **37.3×** |
| INDEX (alias of ETF, 4) | 4 | 5.59 | 7.75 | **8.03** | 12.07 | 8.31 | 12.07 | 2.16× |
| MEME | 2 | 0.00* | 0.00* | **3.40** | 6.79 | 0.00* | 6.79 | n/a* |
| PENNY_STOCK | 0 | — | — | **BLOCKED** | — | — | — | — |

Per-name ETF RT bp: SHY 0.61, AGG 1.05, TLT 2.51, GLD 5.32, DIA 5.59, XLV 5.78,
XLF 6.11, XLY 7.31, XLE 7.39, IWM 7.75, **SPY 8.31**, QQQ 12.07, XLK 14.21, SOXX 22.90.

\* **MEME caveat, not a result:** SHIB-USD reports 0.00 bp but has only **53 distinct
highs across 7,135 bars** and **84.3% zero-range bars** (DOGE: 791 distinct highs, 10.3%
zero-range). That zero is **tick truncation**, not a zero spread, and must not be quoted
as one. DOGE-USD's 6.79 bp is the only MEME number with real resolution. PEPE-USD returned
no data and is recorded as blocked. **PENNY_STOCK has no instrument in this repo's cache**,
so it stays blocked rather than borrowing an equity number.

### Class arithmetic, stated plainly

- **ETF** median upper bound **6.71 bp RT** (3.36 bp/side) vs the **50 bp RT** flat constant
  used in the ledger → the constant is ~7.5× the measured upper bound. ETF's problem is
  not cost: the `/audit3` ETF point estimate is net −0.0062% at 5.11 bp, so even at a
  near-zero cost it is ≈ 0.
- **INDEX** is an alias: its 4 names are all in the ETF universe, and re-measuring them
  under the INDEX label gives the same per-name numbers (SPY 8.31, QQQ 12.07, IWM 7.75,
  DIA 5.59). INDEX is not a separate class and has no cost model of its own.
- **MEME** is where spread could genuinely dominate, so it is the one place an average
  would hide the answer. What the data shows is that the *tick grid* dominates first:
  with 2 usable names and one truncated to a 53-price grid, a MEME spread number is not
  measurable from 1-min Yahoo bars. Recorded as a limit, not a value.

## REFUSED measurements (first-class result)

| Refused | Why measuring cost cannot change the answer |
|---|---|
| Commodity momentum cost | break-even **0 bp/side** → loses at free trading |
| Bond momentum cost | break-even **0 bp/side** → loses at free trading |
| FX carry cost | break-even **468.5 bp** vs ~7.5 bp measured → 60× margin; decided by the 4.32% hurdle |
| Re-running the M1 equity proof bar at 6.04 bp | the D7 rule is killed on **cost-independent** grounds (null 69.8/71.4th percentile, selection-alpha CI-LB −0.285%) |
| Live NBBO for ETF/MEME | Tiingo IEX **HTTP 429** and US session closed (Sunday) → `BLOCKED_NO_LIVE_NBBO`; substituting zero would be a fabrication |
| Commission for ETF/MEME | `COMMISSION_UNKNOWN`: the 10 bp constant is unsourced; not propagated as measured |
| PENNY_STOCK spread | no penny instrument in the repo cache |
| MEME average spread | 1 of 2 names is tick-truncated; an average would manufacture a number |

## Files touched

- [`tools/equity_cost_measure.py`](../tools/equity_cost_measure.py) — **extended, not
  duplicated**: added class universes, `measure_class()` (per-name distribution + tick-
  truncation diagnostic), `classes_main()` and a `--classes-measure` flag. Default
  behaviour is unchanged.
- [`reports/equity_cost_measurement/class_cost_20261122.json`](../reports/equity_cost_measurement/class_cost_20261122.json) — new artifact.
- [`docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md`](../docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md),
  [`docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md`](../docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md),
  [`docs/audit_review_2026-11-22/`](../docs/audit_review_2026-11-22) class dossiers.

## Note on the M1 artifact

The committed [`equity_cost_20261122.json`](../reports/equity_cost_measurement/equity_cost_20261122.json)
records `n_symbols_with_data: 0` and `top_of_book: SKIPPED_OFFLINE_OR_NO_KEY`, while the M1
write-up quotes 12.07 bp. That is a discrepancy between the quoted numbers and the
committed artifact, reported here rather than silently reconciled. This run's numbers live
in `class_cost_20261122.json` and were read back from it.

**RESOLVED 2026-11-22T23:10Z (provenance repair, diagnosis (a) stale artifact).** The
12.07 bp was real: the yfinance spread loop in `equity_cost_measure.py` was key-gated on
`TIINGO_API_KEY`, so a key-less re-run overwrote the good artifact with
`SKIPPED_OFFLINE_OR_NO_KEY`. The gate is fixed (only `--offline` skips the spread) and the
artifact regenerated: `n_symbols_with_data = 13`, median **12.0749 bp**, per-side
**6.0375 bp**, `provenance_self_check = PASS`, per-name values inline. See
[`2026-11-22-m1-provenance-repair.md`](2026-11-22-m1-provenance-repair.md).
**This triage's conclusion is unaffected:** 0 of the 6 UNKNOWN rows are cost-addressable,
and that rests on the 0 bp/side and 468.5 bp break-evens, the 16.398d holding-period
mismatch, and the missing second-month contract series - none of which depend on 12.07 bp
or on the M1 artifact.

## How verified

- `python3 -c "import py_compile; py_compile.compile('tools/equity_cost_measure.py', doraise=True)"` → ok.
- `python3 tools/equity_cost_measure.py --classes-measure` → wrote `class_cost_20261122.json`;
  per-name distributions read back from the artifact, not recalled.
- `tools/momentum_core.py` was not modified.
