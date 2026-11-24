# 27 — Post-cost reconciliation: three costs measured, zero states moved

**Date:** 2026-11-23 · **Re-runs the eligibility gate** of
[`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:176-195) against newly
measured class costs. **Default action is NO CHANGE:** a row moves only if the evidence forces it.

**New evidence re-read for this document, not recalled** (from committed blobs, never the shared working tree):
[`reports/cost_measurement_new_classes/class_cost_new_20261123.json`](reports/cost_measurement_new_classes/class_cost_new_20261123.json)
at commit `7379044` ("research(cost): measure BOND/COMMODITY/PENNY spread upper bounds"),
[`updates/2026-11-23-new-class-cost-measurement.md`](updates/2026-11-23-new-class-cost-measurement.md), and the
break-even sources named in doc 23.

---

## 1. The three UNKNOWN rows, verbatim

From [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:181), `:187`, `:190` on `origin/main`:

| Doc 23 line | Row | Verdict as written | Blocker |
|---|---|---|---|
| 181 | FX mean-reversion (5d/5d) | **UNKNOWN** | `ALREADY_SCHEDULED` — break-even 4.3038 bp; clustered CI at 1 bp [−4.32, +11.09] includes zero |
| 187 | Commodity momentum V1/V2/V3 | **UNKNOWN** (`BLOCKED_MISSING_DATA`) | roll-corrupted front-month continuous series; two independent witnesses NO CANDIDATE |
| 190 | Commodity term-structure carry | **UNKNOWN** (`BLOCKED_MISSING_DATA`) | zero second-month contract series on disk; roll yield needs two contracts |

(Four rows were UNKNOWN when the correction note was written and three remain after funding carry moved; the
current count of three is what the tally line at doc 23 `:195` states.)

## 2. Does the new cost measurement remove the blocker?

Three class costs were measured at `2026-11-23T01:42:40Z` (Sunday night, US equities/bond ETFs closed):

- **BOND:** median RT **1.2125 bp** (per-side ≈0.61 bp), 10/10 names, `MEASURED_FROM_LAST_SESSION`
  [`class_cost_new_20261123.json:558`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:558).
  Range 0.5442 bp (JNK) … 2.5126 bp (TLT). Corwin-Schultz median RT is 0.0724 bp and is unusable as a point
  estimate (several names floor at 0.0, TLH is negative) [`class_cost_new_20261123.json:556`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:556).
- **COMMODITY_FUTURES:** median RT **6.3182 bp** (per-side ≈3.16 bp), 7/7 names, `MEASURED_UPPER_BOUND`,
  measured LIVE on the front-month `=F` series [`class_cost_new_20261123.json:989`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:989).
  Range 2.0572 bp (ZS=F) … 9.6041 bp (SI=F).
- **COMMODITY_ETF_PROXY:** **5.3234 bp**, 7/7, `ETF_PROXY_ONLY` [`class_cost_new_20261123.json:1411`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:1411)
  — an ETF wrapper measurement that **cannot** substitute for the futures cost.
- **PENNY_STOCK:** **21.2974 bp**, 7/8 (TELL blocked `empty`, not zeroed), `MEASURED_FROM_LAST_SESSION`,
  convenience sample with downward survivor bias [`class_cost_new_20261123.json:1844`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:1844).

Every figure is a **median 1-min bar range = a rigorous upper bound on the round-trip quoted spread**
(bid and ask both lie inside `[low, high]`), **not** the NBBO; per-side ≈ half. A zero-range bar on a closed
market is **truncation, not a zero spread**.

## 3. The reconciliation table

| Class / row | Old state | New evidence | Blocker removed? | New state | Why |
|---|---|---|---|---|---|
| FX mean-reversion (row 2) | UNKNOWN (`ALREADY_SCHEDULED`) | FOREX cost already measured, 7.533 bp RT upper bound [`23_DEFINITIVE_ANSWER_2026-11-22.md:51-52`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:51) | **NO** | **UNKNOWN** | Its blocker is a pending weekday-overlap run (cron `48 13 * * 1-5` in [`fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml:38)), not a missing cost. The new measurements are BOND/COMMODITY/PENNY, not FOREX. Nothing changed. |
| Commodity momentum V1/V2/V3 (row 8) | UNKNOWN (`BLOCKED_MISSING_DATA`) | COMMODITY_FUTURES 6.3182 bp RT upper bound, front-month, live | **NO** | **UNKNOWN** (`BLOCKED_MISSING_DATA`) | The blocker is the absence of roll-adjusted continuous futures with a pre-declared roll rule [`23_DEFINITIVE_ANSWER_2026-11-22.md:112-120`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:112). A front-month spread measurement supplies neither a price series nor a roll rule; the artifact's own caveat says so [`2026-11-23-new-class-cost-measurement.md:52-56`](updates/2026-11-23-new-class-cost-measurement.md:52). |
| Commodity term-structure carry (row 11) | UNKNOWN (`BLOCKED_MISSING_DATA`) | COMMODITY_FUTURES 6.3182 bp RT upper bound | **NO** | **UNKNOWN** (`BLOCKED_MISSING_DATA`) | Reopening needs a genuine futures curve with ≥2 simultaneous contract months [`23_DEFINITIVE_ANSWER_2026-11-22.md:123-126`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:123). One front-month spread does not create a second month. |
| Bond momentum B1/B2/B3 (row 9) | **NOT_INVESTABLE** (already) | BOND 1.2125 bp RT upper bound | n/a (not a UNKNOWN row) | **NOT_INVESTABLE** (unchanged) | Confirmed from the table, not assumed: [`23_DEFINITIVE_ANSWER_2026-11-22.md:188`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:188) prints **NOT_INVESTABLE**, on break-even 0 bp/side (free trading still loses to 4.32%). The cost is now measured; the verdict was already cost-independent. |

### The commodity-momentum question, answered deliberately

Its break-even is 0 bp/side [`23_DEFINITIVE_ANSWER_2026-11-22.md:67`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:67), so with `net = gross − 2·cost` any measured cost > 0 makes net strictly worse. That arithmetic is *not* enough to move the row, and the reason is the adversarial objection itself: **the 0 bp/side break-even was computed from the same roll-corrupted series the row is blocked on.** A break-even of zero derived from `CL=F`'s −37.63 print and `ZC=F`'s −23.6% roll days is not trustworthy evidence that the strategy is unprofitable on valid data; it is evidence that the data is invalid. Promoting UNKNOWN → NOT_INVESTABLE on it would compare a reliable cost against an unreliable gross, and would convert a *data* block into a *strategy* verdict without ever measuring the strategy. The honest states are `UNKNOWN` (gross never measured on valid data) or `BLOCKED_MISSING_DATA` (it cannot be), and it is already the latter. **The row does not move.**

The same objection applies with more force to term-structure carry, which has no return estimate at all.

## 4. Tally

**TALLY UNCHANGED: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)**

Three class costs are now measured (BOND 1.2125 bp, COMMODITY_FUTURES 6.3182 bp, PENNY_STOCK 21.2974 bp RT, all upper bounds) but **no row's state moved**: none of the three UNKNOWN rows was blocked on cost, and the one row whose class was measured (bond momentum) was already NOT_INVESTABLE. No document was edited.

## 5. What the measurements do buy

They convert three classes from "UNKNOWN by absence of data" to "cost is known", which is a **precondition** for any future honest test, and they make each reopening requirement numeric:

- **BOND:** a live-session NBBO (the upper bound is 1.2125 bp RT; a strategy must clear `gross > 2·~0.61 bp ≈ 1.2 bp` RT) plus a window spanning more than one rate regime. To trade rates directly, a Treasury futures curve.
- **COMMODITY:** a roll-adjusted continuous curve with per-contract history (so roll cost is measurable) plus a front-month NBBO plus a strategy with positive gross at 0 bp. With cost ≈3.16 bp/side, a valid-data strategy needs > ~6.32 bp RT of gross just to break even on spread. The ETF proxy (5.3234 bp) does not satisfy this.
- **PENNY:** a point-in-time universe including delisted names (to remove survivor bias) plus a live NBBO. 21.2974 bp RT is a *floor-ish* estimate, biased low.

## 6. Ranked-list verdict

**Still 0 entries.** The four gates that have always excluded every row are unchanged: (1) a random-entry null ≥ 95, (2) a 95% CI lower bound on excess return > 0, (3) CAGR above `4.32% + 1.114 × vol`, (4) deflation for trials plus a point-in-time universe and measured cost [`23_DEFINITIVE_ANSWER_2026-11-22.md:157-162`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:157). More costs are measured, but **no class has a CI on net return**, so gate 2 cannot be met by a cost number. The best null percentile on any surviving row is funding carry's, and it is not a random-entry null on a claimed edge.

## 7. Stale statements flagged for follow-up (NOT edited here)

The new measurements contradict these "cost is UNMEASURED" statements. They are listed for a follow-up edit; this task deliberately touches only this one file.

| file:line | Statement now stale | Now |
|---|---|---|
| `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:78` | BOND row: cost **UNMEASURED** | BOND 1.2125 bp RT upper bound [`class_cost_new_20261123.json:558`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:558) |
| `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:79` | COMMODITY row: cost **UNMEASURED** | COMMODITY_FUTURES 6.3182 bp RT upper bound (front month only; roll cost still unmeasured) [`class_cost_new_20261123.json:989`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:989) |
| `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:83` | PENNY_STOCK: **UNMEASURED** (30 bp constant charged) | PENNY_STOCK 21.2974 bp RT, convenience sample, survivor-biased low [`class_cost_new_20261123.json:1844`](reports/cost_measurement_new_classes/class_cost_new_20261123.json:1844) |
| `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:89` | "Blunt count: 11 of the 12 classes have `UNMEASURED` transaction cost." | At least BOND, COMMODITY and PENNY_STOCK now have measured upper bounds; the count is no longer 11 |
| `docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:38` | Commodity term-structure carry: `n/a (cost UNMEASURED)` | COMMODITY_FUTURES cost now measured (the *data* block is unchanged) |
| `docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:76` | Commodity carry: "cost `UNMEASURED`; test not runnable." | Cost now measured; still not runnable (no second month) |
| `docs/preregistration/HML_VALUE_TEST_2026-11-22.md:48` | `UNMEASURED = {"BOND", "COMMODITY", "EQUITY", "ETF", "FUTURES"}` | BOND and COMMODITY have measured upper bounds now; EQUITY/ETF were measured in the M3 pass (12.0749 bp RT) |

Note the M3 pass already measured EQUITY/ETF/INDEX/MEME, so some of these lines were arguably stale before this
document; they are flagged, not adjudicated, here.

## 8. UNMEASURED / refused

- **Roll cost of commodity futures:** `UNMEASURED` — needs per-contract history. Only the front-month *spread* was measured.
- **Commodity term-structure carry return:** `UNMEASURED` — no futures curve exists on disk.
- **Commodity momentum gross return on valid data:** `UNMEASURED` — the only series are roll-corrupted.
- **Live NBBO for BOND / PENNY_STOCK:** `UNMEASURED` — Sunday-night sample; figures are last-session bar-range upper bounds, not NBBO.
- **PENNY_STOCK point-in-time, survivorship-free cost:** `UNMEASURED` — no point-in-time penny universe exists; 21.2974 bp is a biased-low convenience estimate.
- **Treasury (non-ETF) cost:** `UNMEASURED` — BOND is a bond-ETF spread, not the cost of trading Treasuries or a bond mutual fund.
- **FX mean-reversion net return:** `UNMEASURED` pending the weekday-overlap run; the new costs do not pertain to FOREX.
