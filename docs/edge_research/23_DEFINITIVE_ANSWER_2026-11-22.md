# 23 — The definitive answer: nothing in this programme makes money net of cost

> **CORRECTION NOTE (2026-11-22T23:20Z, superseding the first version of this document).** The first version
> carried an **unresolved row count**: its tally line read
> `0 INVESTABLE / 9 NOT_INVESTABLE / 2 BLOCKED_MISSING_DATA / 3 UNKNOWN = 14 rows`, but its own table below
> contained **ten** NOT_INVESTABLE rows and **two** UNKNOWN rows, and its working text visibly failed to
> identify the third UNKNOWN ("the third is… (recomputed: 14 − 9 − 2 = 3)"). That was a computed total
> standing in for a counted list — the same defect class as a cost figure quoted without its artifact.
> **The settled tally, counted one row per line in the table below, is
> `0 INVESTABLE / 10 NOT_INVESTABLE / 4 UNKNOWN = 14 rows`.** The row count did not change (14 before, 14
> after); two verdicts changed, and they changed *toward* KNOWN uncertainty, not away from it: commodity
> momentum and commodity term-structure carry moved from UNKNOWN to a named, permanently-blocked UNKNOWN
> (`BLOCKED_MISSING_DATA`). They are **relabels of rows that were already UNKNOWN, not removals** — the
> uncertainty moved from "unknown verdict" to "known-but-unmeasurable", and nothing became investable.
> The previous 14-row figure was **the right number of rows for the wrong reason**: 14 is correct, but
> `9/2/3` was never counted, only subtracted, and the `2 BLOCKED` split contradicted the table.
> Docs [15](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md) and
> [22](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md) are corrected to the same line in the same commit.

**Date:** 2026-11-22 · **Programme item:** 51 (closing document) · **Row set:** the 14 rows fixed by
[`22_FINAL_SYNTHESIS_2026-11-22.md`](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:25)

**Sources re-read for this document, not recalled:** [`reports/bond_momentum_20261122.json`](reports/bond_momentum_20261122.json) ·
[`reports/commodity_momentum_20261122.json`](reports/commodity_momentum_20261122.json) ·
[`reports/forex_carry_trend_20261122.json`](reports/forex_carry_trend_20261122.json) (re-executed this session from
[`tools/forex_carry_trend_research.py`](tools/forex_carry_trend_research.py) — byte-identical output) ·
[`reports/equity_cost_measurement/equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json) ·
[`reports/cost_measurement_20261122.json`](reports/cost_measurement_20261122.json) ·
[`reports/cost_measurement_forex/FOREX_COST_20261122.md`](reports/cost_measurement_forex/FOREX_COST_20261122.md) ·
[`reports/no_trade_counterfactual_20261122.json`](reports/no_trade_counterfactual_20261122.json) ·
[`reports/verification_20261122.json`](reports/verification_20261122.json) ·
[`updates/2026-11-22-m3-cost-triage.md`](updates/2026-11-22-m3-cost-triage.md).

---

## 1. The answer

**No: nothing in this programme makes money net of cost, judged against a US 3-month T-bill paying
4.32%** ([`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md:20)): 0 of 14 rows is
investable, 10 are killed, and 4 are still open — 2 of them permanently blocked on data that is not on disk
(the two commodity rows) and 2 open on facts cost measurement cannot supply (FX mean-reversion, funding carry).
The open rows are open for reasons no further cost measurement can address.

## 2. What was proven, with numbers

**Cost, measured.** CRYPTO: taker fee 10 bp/side (Binance, BinanceUS, KuCoin), 26 bp (Kraken); all-in
round trip ≈20.0 bp to ≈52.0 bp, while BTC/USDT top-of-book round-trip spread is 0.00164 bp — the fee
dominates the spread by four orders of magnitude ([`cost_measurement_20261122.json`](reports/cost_measurement_20261122.json)).
FOREX: 7.533 bp round trip for the six USD majors (median of medians), 7.99 bp all-pairs median, sampled at
the Sunday 22:00Z reopen, so an **upper bound** ([`FOREX_COST_20261122.md`](reports/cost_measurement_forex/FOREX_COST_20261122.md)).
EQUITY: 12.0749 bp round trip upper bound, **6.0375 bp per side**, Corwin-Schultz 1.5033 bp,
`provenance_self_check = PASS` over 13 names ([`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json)).
Class context: ETF median RT upper bound **6.7122 bp** over 14 names (SHY 0.6144 … SOXX 22.9049), INDEX
(alias of ETF, 4 names) **8.0325 bp** (SPY 8.3139 / QQQ 12.0749 / IWM 7.7512 / DIA 5.5896), MEME only
DOGE-USD quotable at **6.7938 bp** (SHIB 0.00 bp is tick-truncated, 84.3% zero-range bars, and PEPE-USD has
no data; PENNY_STOCK has no instrument). These are **supported by the committed artifact**
[`class_cost_20261122.json`](reports/equity_cost_measurement/class_cost_20261122.json) (commit `87a2e0cbe2f`,
yfinance 1-min bars, 2026-11-16..20, fetched 2026-11-22T22:59Z) and are the same numbers recorded in
[`2026-11-22-m3-cost-triage.md`](updates/2026-11-22-m3-cost-triage.md). They are a rigorous **upper bound**
(median 1-min bar range), **not** the NBBO, and they are context, not a verdict: no row below is decided by them.
An earlier version of this document said the artifact had empty `classes`; that was wrong, and the tripwire
[`tests/test_m1_cost_provenance.py`](tests/test_m1_cost_provenance.py) now checks class figures against it.

**The zero-cost kills.** These lose money with free trading, so no fill improvement can rescue them:
crypto intraday mean-reversion (`breakeven_cost_bp = 0.0`, PF 0.815 at 0 bp); commodity momentum V1/V2/V3
(`breakeven_bp_per_side_sharpe_zero = 0.0` each; V1 PF 0.757, V2 1.114, V3 1.074 at 5 bp/side, CAGR −7.13%
/ +0.47% / −0.67% against 4.32%); bond momentum B1/B2/B3 (0 bp/side each); and FX momentum at a **−26.88 bp
gross** ([`forex_carry_trend_20261122.json`](reports/forex_carry_trend_20261122.json)).

**The hurdle arithmetic.** Required return is `rf + 1.114 × vol` (rf 4.32%, the 1.114 being the bar to beat
SPY). A 30%-vol strategy must earn 37.7% a year to clear it; none tested does.

**The live record.** 10,968 resolved picks over 278 days (2026-02-17 → 2026-11-22), mean **−0.1524%** per
trade, win rate **43.14%**, sum **−1,671.5%**, per-trade Sharpe −0.037, against SPY **+1.81%** and T-bills
**+3.29%** over the identical window ([`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`](docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md:181-190);
figures present in [`no_trade_counterfactual_20261122.json`](reports/no_trade_counterfactual_20261122.json), the SPY figure in the doc only).
The system lost money in a window where cash made money.

## 3. What was refused, and why

Eight measurements were deliberately **refused** ([`2026-11-22-m3-cost-triage.md`](updates/2026-11-22-m3-cost-triage.md:90-101)):
commodity-momentum cost and bond-momentum cost (break-even **0 bp/side** → nothing to measure), FX carry
cost (break-even **468.5 bp** vs ~7.5 bp measured → 60× margin, decided by the hurdle), re-running the
equity proof bar at 6.04 bp (already killed on cost-independent grounds), live NBBO for ETF/MEME
(Tiingo IEX HTTP 429, US session closed → `BLOCKED_NO_LIVE_NBBO`, not zero), ETF/MEME commission
(`COMMISSION_UNKNOWN`), PENNY_STOCK spread (no instrument), and a MEME average spread (one of two names is
tick-truncated; an average would manufacture a number).

**Refusing to measure a zero-cost kill is a result, not an omission.** When break-even cost is 0 bp/side,
the cost term cannot flip the sign, so a measurement would change no verdict and its absence blocks
nothing. Cost measurement is now exhausted as a lever: 0 of the 6 open rows is cost-addressable.

## 4. What remains genuinely unknown

Four rows, none blocked on effort, all of them relabels of rows that were already UNKNOWN:

- **FX mean-reversion** (`ALREADY_SCHEDULED`), UNKNOWN: break-even 4.3038 bp; the window-clustered CI at 1 bp
  is [−4.32, +11.09] and includes zero, so cost is necessary but not sufficient. A weekday London/NY-overlap
  run is automated in [`.github/workflows/fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml) and pending.
- **Funding carry** (`BLOCKED_OTHER`), UNKNOWN, cost already measured at 45.524 bp round trip: needs a funding
  regime persisting ≥16.398 days (median episode 1.93–2.33 d), 27–32× more capacity, and a
  survivorship-clean universe.
- **Commodity momentum (V1/V2/V3)**, UNKNOWN (`BLOCKED_MISSING_DATA`): counted as ONE row for the family
  (convention below); §5.
- **Commodity term-structure carry**, UNKNOWN (`BLOCKED_MISSING_DATA`): §5.

## 5. The two commodity rows: BLOCKED_MISSING_DATA, permanently

**Commodity momentum.** The front-month continuous series are roll-corrupted, and the objection was
substantiated rather than withdrawn: `CL=F` has a negative close (−37.63, 2020-04-20) that makes
`pct_change` meaningless, `ZC=F` prints ≈−23.6% on 07-15 in three separate years, and `NG=F` has recurring
same-month-day spikes across six years (55–163 moves > 8%)
([`20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md`](docs/edge_research/20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md:116-132)).
Two independent witnesses closed the class **NO CANDIDATE**. A hand-built roll methodology chosen after
seeing the prices it must explain would be a signal manufactured by the analyst, not found in the data, so
none was attempted. **To reopen:** roll-adjusted, back-adjusted continuous futures series built from
individual contract months with an explicit, pre-declared roll rule, plus commission and slippage charged
per contract.

**Commodity term-structure carry.** There is **zero second-month contract series on disk**, and roll yield
`(front − second)/second` needs two contracts at the same date. Synthesising the second would invent the
signal outright. **To reopen:** a genuine futures curve (at least two simultaneous contract months per
commodity per date) for a multi-year history.

## 6. The validation system's own verdict

The gate that would certify a survivor cannot certify anything. It hard-codes ineligibility for any pod not
marked `pre_registered` ([`alpha_engine/audit3_tribunal.py:1642`](alpha_engine/audit3_tribunal.py:1642)),
**9 of 12 pods are `observe`**, the one `pre_registered` pod has zero forward rows, and all 430 forward rows
belong to H-119, which has no pod and is marked non-promotable
([`03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md`](docs/edge_research/03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md:100-130)).
**Zero ledger rows exist on any pod's own hypothesis.**

The audit surfaces also disagree with one another: ledger **8,769** / dashboard **8,827** / live `/audit`
**8,816** / local regen **10,968**, across four digests (`63609da5…`, `ed25b59c…`, `e346e65f…`,
`c0942d9e…`), with the live digest drifting to `5a6ff492…` (8,792 rows) inside the same session with no
one changing anything ([`21_VERIFICATION_AND_CI_GUARD_2026-11-22.md`](docs/edge_research/21_VERIFICATION_AND_CI_GUARD_2026-11-22.md:86-101)).
The audit3 digest is **`NOT_REPRODUCIBLE_BY_DESIGN`**: it hashes the post-dedup, post-exclusion, post-cost-model
row set after writing, so it identifies a snapshot, not a dataset version.

## 7. The single most important finding

**Cost was assumed for 11 of 12 asset classes for the entire life of the programme.** When it was finally
measured, the answers did not change but the reasons did. EQUITY came in at 6.0375 bp/side against an
assumed 25 bp/side — a quarter of the assumption, a fourth of the excuse removed — and the breakout rule
still failed: the random-entry null sits at the 69.8th/71.4th percentile and selection alpha is negative
with a CI lower bound of −0.285%, and at the measured cost the pod's null is the 10.2nd percentile with an
excess-CAGR CI of [−46.32%, +32.31%]
([`22_FINAL_SYNTHESIS_2026-11-22.md`](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:131)). That is the honest
shape of the result: **measuring cost honestly did not find an edge, it removed the excuse.** The cheapest
possible version of every strategy was tried, and the cheapest possible version still lost.

## 8. What would have to be true for an investable strategy to appear

All of the following at once: a random-entry null ≥ 95; a 95% CI lower bound on excess return > 0; CAGR
above `4.32% + 1.114 × vol`; deflation for the number of trials attempted; a point-in-time universe that
includes delisted names; and cost **measured** rather than assumed. **No candidate in this programme meets
even the first condition** — the best null percentile on any surviving row is funding carry's, and it is not a random-entry null on a claimed edge.

---

## The final accounting

Counted from the row verdicts, one row per line, not hand-edited and not subtracted. 14 rows.

**Commodity-row convention (adopted, and applied everywhere in this document, doc 15 and doc 22):** a
*variant set* is **one row** when its members share one dataset, one artefact and one verdict and are only
different parameterisations of the same strategy. So commodity momentum V1/V2/V3 is **one** row, bond
momentum B1/B2/B3 is **one** row, and the N1 rules R1/R2/R3 are **three** rows because they are three
different strategies on three different universes. This is why the commodity family cannot be counted once
as "blocked" and once as "unknown": it is a single row whose verdict is `UNKNOWN` with the qualifier
`BLOCKED_MISSING_DATA`. The qualifier explains *why* it is unknown; it is not a fourth verdict category and
it removes no row from the UNKNOWN count.

| # | Row | Final verdict | Basis | Change in this pass | Driven by |
|---|---|---|---|---|---|
| 1 | FX momentum (63d/21d) | **NOT_INVESTABLE** | gross −26.88 bp, net −36.88 bp, null 0.0 pct, n=4,092 (`forex_carry_trend_20261122.json`, re-executed byte-identical) | UNKNOWN → NOT_INVESTABLE | interpretation |
| 2 | FX mean-reversion (5d/5d) | **UNKNOWN** | break-even 4.3038 bp; clustered CI at 1 bp [−4.32, +11.09] | none | — |
| 3 | Equity breakout | **NOT_INVESTABLE** | null 69.8/71.4 pct; alpha CI-LB −0.285%; PF 0.9917 @25 bp/side | none | — |
| 4 | FX carry (quintile) | **NOT_INVESTABLE** | Sharpe −0.126 vs 4.32%; break-even 468.5 bp; null 98.2 | none | — |
| 5 | Cross-venue basis | **NOT_INVESTABLE** | 0.00% of 720 minutes above the 40.48 bp measured threshold | none | — |
| 6 | 12-1 momentum L/S | **NOT_INVESTABLE** | null 1.6; CAGR −25.45%; maxDD −82.3% | none | — |
| 7 | Crypto intraday mean-rev | **NOT_INVESTABLE** | PF 0.815 @0 bp; break-even 0 bp; null 0.0 | none | — |
| 8 | Commodity momentum V1/V2/V3 | **UNKNOWN** (`BLOCKED_MISSING_DATA`) | `reports/commodity_momentum_20261122.json` results V1/V2/V3 verdict KILL at break-even **0 bp/side** (V1 PF 0.757, V2 1.114, V3 1.074), but the 7 front-month series carry roll artifacts substantiated on disk (CL=F 17 moves >8%, ZC=F −13.1% on 07-15-2022 and −16.8% on 07-17-2023, NG=F 92 moves >8%); two independent witnesses NO CANDIDATE | UNKNOWN → UNKNOWN (relabelled with its block reason) | interpretation |
| 9 | Bond momentum B1/B2/B3 | **NOT_INVESTABLE** | `reports/bond_momentum_20261122.json`: B1 PF 1.312 beside Sharpe −0.550, maxDD −5.81%, null 2.0; B2 PF 0.743, Sharpe −1.699; B3 PF 0.737, Sharpe −1.063, skew −1.452; break-even **0 bp/side** on all three (free trading still loses to 4.32%) | UNKNOWN → NOT_INVESTABLE | interpretation |
| 10 | Funding carry | **UNKNOWN** | `reports/funding_carry_20261122.json`: break-even 16.398 d vs 1.93–2.33 d episode; pair RT 45.524 bp; +2.42% APR @30 d vs 4.32% | none | — |
| 11 | Commodity term-structure carry | **UNKNOWN** (`BLOCKED_MISSING_DATA`) | `reports/commodity_carry_20261122.json`: zero second-month contract series on disk; roll yield needs two contracts | UNKNOWN → UNKNOWN (relabelled with its block reason) | interpretation |
| 12 | N1 R1 multi-asset momentum | **NOT_INVESTABLE** | null 61.2; excess vs SPY +0.97 pp | none | — |
| 13 | N1 R2 sector momentum | **NOT_INVESTABLE** | null 35.4; excess −11.3 pp | none | — |
| 14 | N1 R3 SPY 200-day trend | **NOT_INVESTABLE** | null 53.4; excess −6.8 pp | none | — |

TALLY: 0 INVESTABLE / 10 NOT_INVESTABLE / 4 UNKNOWN (14 rows)

(The first version of this document printed `0 / 9 NOT_INVESTABLE / 2 BLOCKED_MISSING_DATA / 3 UNKNOWN`, which
was a subtraction, not a count, and disagreed with its own table. `BLOCKED_MISSING_DATA` is a qualifier on
UNKNOWN, not a separate bucket, so the two commodity rows are inside the 4 UNKNOWN. Doc 15 and doc 22 carry
the same line.)

### How many rows moved, and why

**2 rows changed classification: 0 measurement-driven, 2 interpretation-driven** (commodity momentum and
commodity term-structure carry, both UNKNOWN → UNKNOWN with a block qualifier). **0 rows became investable and
0 rows left the UNKNOWN bucket** — the row count is unchanged at 14 and the UNKNOWN count is unchanged at 4.
Bond momentum and FX momentum were already NOT_INVESTABLE in the table this document inherited.

- **Bond momentum, UNKNOWN → NOT_INVESTABLE** is a *clarification*, not a new measurement: break-even is
  0 bp/side, so cost measurement was never capable of changing the answer, and the earlier UNKNOWN was
  over-cautious on the wrong dimension. An honest label applied to the wrong dimension is still a defect.
  B1's PF **1.312** must never be quoted without Sharpe **−0.550** and maxDD **−5.81%** beside it: the
  denominator counts only closed losing trades while the equity curve bleeds, and 10.2% of months sit in
  cash (time in market 89.8%). Against a 4.32% T-bill, a −0.550 Sharpe is a loss at any cost.
- **FX momentum, UNKNOWN → NOT_INVESTABLE**: the −26.88 bp gross is now reproduced from its own harness
  (byte-identical JSON), so the provenance hole is closed. The move is interpretation-driven because the
  number itself did not change; what changed is that it can be re-executed.
- **Commodity momentum and commodity term-structure carry → BLOCKED_MISSING_DATA**: a relabel of rows that
  were already not investable-or-testable, on data that is absent rather than unexamined.

No row moved on a new measurement in this pass. The only measurement-driven moves in the programme were
earlier and are already recorded (M1 equity, M2 FX).
