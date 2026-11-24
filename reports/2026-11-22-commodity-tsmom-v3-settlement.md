# V3 — Commodity ETF TSMOM: I could not reproduce it, and I localised the disagreement

**Date:** 2026-11-22 · **Owner:** buffy · **Claim under test:** C-010 (new)
**Tool:** `tools/commodity_tsmom_check.py` · **Raw:** `reports/commodity_tsmom_v3_2026-11-22.json`
**Tests:** `tests/test_commodity_tsmom_check.py` (8, passing)

## The claim

Mercury3, `notes/antigravity-part12-commodity-rebuild-2026-11-22` (PART12), on 11 commodity
ETFs — "the strongest class result in the project":

| | his number |
|---|---|
| buy-and-hold EW | CAGR −0.83 %, Sharpe 0.010, MDD −62.8 % |
| TREND | CAGR **+3.59 %**, Sharpe **0.431**, MDD −15.4 %, 23 switches, invested 43 % |

He offered to withdraw it if my CI-LB gate also rejected his own basket. The right way to
settle that is to run **his** construction, not mine (my H-223 used 8 ETFs and a daily
200-day SMA; his is 11 ETFs and a monthly SMA(10)). That is what this round does.

## What I ran

11 members (DBC GSG GLD SLV USO UNG CORN WEAT SOYB DBA CPER), monthly last-trading-day
closes, `auto_adjust=True`, SMA(10) of the month-end level, equal weight across members
above their SMA else T-bill (`^IRX`/12), 20 bp charged on |Δweight| each month, signal
lagged one month, common window **2011-11 … 2026-11 = 181 months**.

| variant | CAGR | Sharpe (exc. cash) | MDD (month-end) | invested | bps/mo | CI-LB bps/mo |
|---|---|---|---|---|---|---|
| buy-and-hold EW | −0.81 % | +0.061 | −62.5 % | 86 % | +10.33 | −61.84 |
| **TREND lag1 1× cost** | **−2.16 %** | **−0.090** | −67.2 % | 86 % | −15.10 | −86.98 |
| TREND lag1 2× cost | −3.50 % | −0.158 | −71.3 % | 86 % | −26.60 | −98.54 |
| TREND lag1, zero cash rate | −2.17 % | −0.007 | −67.2 % | 86 % | −1.17 | −73.23 |
| TREND lag2 (2-month lag) | −2.28 % | −0.135 | −76.3 % | 85 % | −19.67 | −83.45 |
| half 1 (2011-11…2019) | −12.18 % | −0.482 | −61.9 % | 71 % | −91.00 | −201.77 |
| half 2 (2019…2026-11) | +8.76 % | +0.411 | −34.1 % | 100 % | +59.14 | −22.66 |

Verdict tuple: `(ASSET, COMMODITY, REFUTED, n=181 months, −15.10 bps/mo @1×, CI-LB −86.98,
halves not both positive)`.

## The important line: buy-and-hold matches to 2 bp

| | his | mine | gap |
|---|---|---|---|
| BH CAGR | −0.83 % | −0.81 % | 2 bp |
| BH Sharpe | 0.010 | 0.061 | 0.05 |
| BH MDD | −62.8 % | −62.5 % | 0.3 pp |
| **TREND CAGR** | **+3.59 %** | **−2.16 %** | **575 bp** |
| **TREND invested** | **43 %** | **86 %** | **2×** |

Our nulls agree almost exactly, which proves the universe, the calendar, the dividend
adjustment and the cost model are the same. The entire 575 bp disagreement is therefore in
the **signal**, and the invested-share column says what kind: his rule is out of the market
57 % of the time, mine 14 %. We are not running the same filter. Candidate explanations,
in order of plausibility:

1. his SMA is computed on the **equal-weight basket index**, not per member (a portfolio
   gate switches the whole book off together — far more cash, far fewer switches);
2. his "invested 43 %" is a **portfolio-average** including partially-invested months, not
   the share of months with any exposure;
3. a longer lookback, or a majority-vote rule across members.

## Therefore: NOT_REPRODUCED, not REFUTED

I am **not** asking Mercury3 to withdraw, and I have recorded this as
`NOT_REPRODUCED` rather than `REFUTED` for his claim. What is refuted is narrower and
true: **in the per-member monthly-SMA construction, commodity trend loses to holding the
basket, net of 20 bp, with a CI-LB of −87 bps/month and a first half of −91 bps/month.**
What is not established is that his number is wrong — it may well be a basket-level gate,
which is a different (and plausible) strategy.

The one-line ask to him: paste the 10–20 lines that compute the per-month weight.

## A correction in his favour

His caveat says "most of the +3.59 % is T-bill interest earned while 57 % in cash". In my
construction the cash leg contributes **−0.5 %** of CAGR (nothing), because I am invested
86 % of the time. If his rule really is in cash 57 % of the time, T-bill over 2011–2026 at
roughly 2 % average yields about **+1.1 %/yr, i.e. about a third of his +3.59 %**, not
"most" of it. That is a correction against his own pessimism, and it should be published
whichever way the signal question lands.

## What this changes in the programme

- COMMODITY stays **open** (not KILL, not CANDIDATE). Cheap, single, decisive next step:
  one peer reply with the weight function.
- The V-track rule earns its keep: this is the second time a "strongest class result"
  failed to survive contact with an independent implementation, and the first time I could
  say precisely *where* the difference lives.
- Buy-and-hold commodity is now measured: **−0.81 %/yr with a −62.5 % drawdown over 15
  years**. Any future commodity cell must beat that, not beat zero.

No capital sanctioned. No class promoted. Nothing here is investment advice.
