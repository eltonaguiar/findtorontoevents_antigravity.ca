# New-class cost measurement (BOND, COMMODITY, PENNY_STOCK) — 2026-11-23

**Measured at:** `2026-11-23T01:42:40Z` (Sunday night, US equities/bond ETFs closed).
**Artifact:** `reports/cost_measurement_new_classes/class_cost_new_20261123.json`
**Tool:** `tools/equity_cost_measure.py --classes-measure-new` (extends the M3 class
measurement; reuses `measure_spread()` and `corwin_schultz()` unchanged).
**Programme context:** `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` — this
measurement targets three of the UNKNOWN rows, which were UNKNOWN by *absence of data*.

## ⚠️ Sunday-night caveat (read first)

It is ~01:42Z on a Sunday. US bond ETFs, equities and penny stocks **do not trade**.
For those classes the 1-min bars are the **last session's** (2026-11-16..2026-11-20) and
every figure is labelled `MEASURED_FROM_LAST_SESSION`. A zero-range bar at this hour is
**truncation, not a zero spread**. The one exception is commodity **futures** (`=F`),
which trade ~24/5: their sample is **live** (last bar `2026-11-23 01:32Z`).

Every bp figure below is the **median 1-min bar range = a rigorous UPPER bound on the
round-trip quoted spread** (bid and ask both lie inside `[low, high]`). It is **not**
the NBBO. Per-side ≈ half the round-trip figure.

## What was measured

| Class | Status | Median RT (upper bound) | ≈ per side | n | Per-name range (min … max) | Freshness |
|---|---|---|---|---|---|---|
| BOND | `MEASURED_FROM_LAST_SESSION` | **1.2125 bp** | 0.61 bp | 10/10 | 0.5442 (JNK) … 2.5126 (TLT) | last session |
| COMMODITY_FUTURES | `MEASURED_UPPER_BOUND` | **6.3182 bp** | 3.16 bp | 7/7 | 2.0572 (ZS=F) … 9.6041 (SI=F) | **live** |
| COMMODITY_ETF_PROXY | `ETF_PROXY_ONLY` | **5.3234 bp** | 2.66 bp | 7/7 | 1.6526 (DBC) … 10.5969 (SLV) | last session |
| PENNY_STOCK | `MEASURED_FROM_LAST_SESSION` | **21.2974 bp** | 10.65 bp | 7/8 | 6.2697 (SIRI) … 92.644 (PLUG) | last session |

- **BOND** universe = the 10 bond ETFs the item-34 rule trades (`TLT, IEF, SHY, TLH, AGG,
  BND, LQD, TIP, JNK, HYG`), from `docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md` §0.2.
- **COMMODITY_FUTURES** universe = the 7 continuous front-month futures the item-33 rule
  ranks (`CL, GC, HG, NG, SI, ZC, ZS =F`), from `tools/commodity_momentum.py`.
- **COMMODITY_ETF_PROXY** universe is a convenience selection of liquid commodity ETFs
  (GLD/SLV/USO/DBC/DBA/UNG/CPER) chosen by this task — **not** a repo file.
- **PENNY_STOCK** universe is a convenience sample (`SIRI, F, NIO, LCID, PLUG, RIG, TELL,
  GPRO`) constructed by this task. `TELL` returned no data and is recorded as **blocked
  (`empty`), not zeroed**; no repo penny-universe file exists.

No name in any of the four classes was flagged `suspect` by the tick-truncation
diagnostic this run, so nothing was excluded from a median. The exclusion path exists and
is exercised by SHIB in the MEME class (below).

## What each number does and does not mean

- **BOND (1.2125 bp RT, upper bound).** This is the cost of **bond-ETF exposure**. It is
  **not** the cost of trading Treasuries directly, and **not** the cost of a bond mutual
  fund (which trades at NAV, no intraday spread). Corwin-Schultz is unusable as a point
  estimate here: several names floor at 0.0 (IEF/SHY/TIP/JNK) and some are negative
  (TLH −0.32). The bar-range bound is the honest number.
- **COMMODITY_FUTURES (6.3182 bp RT, upper bound, live).** This is the **front-month
  contract's** spread. It is **not** the roll cost: the repo has only a single continuous
  front-month series per symbol, so roll yield `(front − second)/second` cannot be
  computed. The class's documented blocker is the **roll-adjusted continuous curve**, and
  this measurement does **not** unblock it.
- **COMMODITY_ETF_PROXY (5.3234 bp RT).** This measures the **ETF wrapper only**. GLD's
  spread is not gold futures' spread, and no roll cost appears here. It answers "what
  would commodity exposure via an ETF cost", nothing more. Treating it as the futures
  cost would be exactly the silent substitution this file exists to prevent.
- **PENNY_STOCK (21.2974 bp RT).** Convenience sample, **not point-in-time**. Survivor
  selection (only names still listed and liquid) biases this estimate **downward**; real
  penny trading costs are likely higher. Wide dispersion (6 bp … 93 bp) is the point:
  a single class average would hide it.

## Does the verdict change? No — and here is the arithmetic

Bond momentum and commodity momentum both have a **0 bp/side break-even**. With
`net = gross − 2·cost`:

- break-even cost `c*` solves `net(c*) = 0` ⇒ `c* = gross / 2`.
- Both families already have `gross ≤ 0` at zero cost (even free trading fails to clear
  the 4.32% T-bill), so `c* ≤ 0`.
- The measured cost is strictly positive (BOND ≥ 0.54 bp RT, COMMODITY_FUTURES ≥ 2.06 bp RT),
  so `cost > 0 ≥ c*` ⇒ `net(cost) < 0`, strictly worse than at zero cost.

A newly measured cost therefore **cannot** rescue either strategy: `0 bp < measured cost`
⇒ net is negative at any measured cost. The value of the measurement is that it converts
"UNKNOWN by absence of data" into **NOT_INVESTABLE on evidence** and lets the reopening
requirement be stated precisely. No verdict in any existing document was changed.

## Reopening requirement (if a real test is ever wanted)

- **BOND:** a live-session NBBO (not a bar-range bound), a strategy whose zero-cost
  break-even exceeds the measured cost (`gross > 2·~0.61 bp ≈ 1.2 bp RT`), and a window
  spanning more than one rate regime. To trade rates directly, a Treasury futures curve.
- **COMMODITY:** a **roll-adjusted continuous futures curve** (per-contract history so
  roll cost is measurable) plus a front-month NBBO, plus a strategy with positive gross at
  0 bp. The ETF proxy does not satisfy this.
- **PENNY:** a **point-in-time** penny universe including delisted names (to remove
  survivor bias) plus a live NBBO.

## Reproducibility / what did not change

`--classes-measure` was re-run and the existing classes' medians were compared to the
committed artifact: **ETF 6.7122 bp and INDEX 8.0325 bp are byte-identical**; EQUITY
**12.0749 bp RT / 6.0375 bp per side** and **MEME DOGE 6.7938 bp** are unchanged in the
committed artifacts (the MEME median itself moved 3.3969→3.4998 only because DOGE's live
24/7 bars changed between runs — crypto input variance, not a code change; SHIB's 0.0 is
still flagged `suspect` and is still the reason a naive MEME median is meaningless).
The M3 artifact was restored to its committed content afterward.
