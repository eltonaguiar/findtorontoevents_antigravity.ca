# Edge candidates — anything positive net of cost? Value? PEAD?

**Date:** 2026-11-22 · **Scope:** answers from this programme's own artifacts only.
Read-only. Not investment advice. Any figure below is traceable to the cited document;
a field the programme never measured is written `UNKNOWN`, never guessed.

## The one-line answer

**No: this programme holds ZERO strategies with a positive net-of-cost result that
survives the null/CI/hurdle bar.** TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows) —
counted from doc 23's 14 row verdicts; the UNKNOWN list further below predates that count and still
enumerates six, two of which doc 23 classes NOT_INVESTABLE. No `UNKNOWN` row is a "yes" either. **VALUE stocks and
post-earnings-announcement drift (PEAD) were never reviewed as strategy families in this
round** (the 22-doc review's 14 rows do not include either), so for them the honest answer
is `UNKNOWN` with no universe, sample, or bp/trade to report.

Source of truth: [`22_FINAL_SYNTHESIS_2026-11-22.md`](edge_research/22_FINAL_SYNTHESIS_2026-11-22.md)
and [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md).

## Why "no positive net-of-cost candidate" is not a formality

The hurdle is **T-bills at 4.32%**, and the requirement is `required = rf + 1.114 × vol`,
never zero. So a strategy needs a *positive* PF **and** a null percentile ≥ 95 **and** a
bootstrap CI on excess return whose lower bound is > 0 **and** a CAGR above that hurdle.
Several rows have PF > 1 and still fail:

| Strategy | PF (cost basis) | Sharpe | maxDD | Decisive kill |
|---|---|---|---|---|
| Equity breakout | 1.2865 @ 0 bp / 1.2206 @ 5 bp / 0.9917 @ 25 bp | 0.493 (N=20) | −77.0% | random-entry null **69.8th** pct, selection-alpha CI-LB **−0.285%** |
| Bond momentum B1 | **1.312 @ 5 bp (assumed)** | **−0.550** | n/a | null **2.0**; PF inflated by cash-drag denominator |
| Commodity momentum V2 | 1.114 @ 5 bp (assumed) | n/a | n/a | break-even **0 bp/side**; data-corrupted (roll artifacts) |
| N1 R1 12-month momentum | no PF | 0.590 | n/a | null **61.2** despite CAGR 18.05% vs 4.32% |
| N1 R2 sector momentum | no PF | n/a | n/a | null **35.4**; excess vs SPY **−11.3 pp** |
| N1 R3 SPY 200-day | no PF | n/a | n/a | null **53.4**; loses to SPY buy-and-hold |

**PF is never quoted without Sharpe and max drawdown** here on purpose: bond B1's PF 1.312
sits beside a Sharpe of −0.550, which is exactly the inflation trap.

## The 6 UNKNOWN rows (not "yes", just undecided)

| Row | What it is | Decisive number | Why still UNKNOWN |
|---|---|---|---|
| 1 | FX momentum (63d/21d) | mean net −36.88 bp, gross −26.88 bp | figures exist only in Markdown; no machine-readable R21 report |
| 2 | FX mean-reversion (5d/5d) | gross +4.30 bp, net −5.70 @ 10 bp, break-even **4.3038 bp** | measured FX upper-bound cost ~7.5-8 bp is ~1.75-1.9× break-even; clustered CI at 1 bp includes zero |
| 8 | Commodity momentum | break-even **0 bp/side** | data-corrupted: roll artifacts (`CL=F` negative close etc.) |
| 9 | Bond momentum | break-even **0 bp/side** | ETF dividend-adjustment method `UNMEASURED` |
| 10 | Funding carry | break-even hold **16.398 d** vs median episode 1.93-2.33 d | premium real but no positive CI at a hold that occurs; survivorship UNSAFE |
| 11 | Commodity term-structure carry | **zero second-month contract series** | `BLOCKED_DATA` |

## VALUE stocks

- **Reviewed as a family in this round?** No. No row in the 14-row synthesis is a value
  strategy.
- **Universe / sample n / net bp-per-trade / trial count / survives deflation?**
  `UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN`.
- **What exists in the repo:** value tooling (`tools/value_screener.py`,
  `tests/test_value_backtest.py`, `tests/test_value_screener.py`) exists as code, but it is
  **not part of this profitability programme's reviewed results** and I did not run it here.
  Its output would be a new experiment needing the same null, CI, hurdle and multiple-
  testing deflation applied above — I will not quote an unrun number as evidence.

## PEAD (post-earnings-announcement drift)

- **Reviewed as a family in this round?** No.
- **Universe / sample n / net bp-per-trade / trial count / survives deflation?**
  `UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN / UNKNOWN`.
- **What exists in the repo:** PEAD code and tests (`tools/eq1_pead_backtest.py`,
  `tools/h010_pead_research.py`, `tools/pead_shadow_runner.py`,
  `tests/test_equity_pead_strategy.py`, `tests/test_m009_pead_equity.py`,
  `tests/test_h010_pead_research.py`). These are **not** part of this programme's reviewed
  artifacts, and no PEAD result appears in the 22-doc review. Quoting their numbers without
  running them under the same bar would repeat exactly the provenance defect this round is
  trying to eliminate.

## What would turn either into a real candidate

For VALUE or PEAD to move off `UNKNOWN` it needs, in one artifact: a stated universe, the
sample n, net bp/trade at a **measured** cost, the trial count (how many variants were
tried), a random-entry or matched-factor null percentile, a bootstrap CI on excess return
vs the 4.32% hurdle, and a deflation for the trial count. Until then neither is a candidate
and neither is a kill.
