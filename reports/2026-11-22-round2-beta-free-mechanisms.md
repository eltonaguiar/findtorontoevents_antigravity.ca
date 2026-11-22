# Round 2 — repairing the commodity class and removing beta from the cells

**Date:** 2026-11-22 · **Cells:** 40 (was 34) · **Trials declared:** 29 · **PBO (CSCV): 0.345**
**Window:** 2012-01-03 → 2026-11-21 (price cells) · 2021-01-01 → 2026-11-22 (funding cell, 2,152 days)

Round 1 ended with EQUITY as the only class clearing every gate. Two questions
were left open, both about *me* rather than the market:

1. COMMODITY was `DATA_INTEGRITY_FAIL` because I scored raw futures. Was the class
   bad, or was my series bad?
2. Every cell was long-only, so every one of them was partly a bet on its own
   universe rising. Was the benchmark gate measuring skill, or beta?

Both were answered by adding pre-registered cells (`H-223`…`H-228`, frozen in
`reports/hypothesis_registry.json` **before** the first run).

## 1. COMMODITY: the series was bad, and the class still has no edge

`H-223`/`H-224` measure the class on **investable ETFs** (GLD, SLV, CPER, DBA,
USO, UNG, CORN, WEAT). An ETF's NAV absorbs the roll, so the price series has no
roll gap and the return is what a holder actually earns — including the contango
that USO/UNG holders eat. All 8 series loaded.

| cell | n | PF | daily bps | CI-LB | CI-LB @2× | verdict |
|---|---|---|---|---|---|---|
| H-223 TSMOM 12-1 ETF basket | 179 | 1.09 | 0.361 | **−1.324** | −1.9 | REFUTED_OR_WEAK |
| H-224 xsmom top-3 6m ETF | 179 | 1.11 | 1.114 | **−2.785** | −3.4 | REFUTED_OR_WEAK |

So the repair made the measurement honest and left the answer unchanged:
commodity trend-following, at monthly rebalance and 15 bps round trip, does not
produce a positive lower bound over 2012–2026. The futures cells keep their
`DATA_INTEGRITY_FAIL` label (CL=F printed a negative price; ZC=F jumps −23.6 % on
July 15 in three separate years) — they are still not evidence of anything.

Note what this does **not** say: it does not refute commodity *carry* (roll yield),
which is the documented commodity edge and needs futures curves this repo does not
have. It refutes my trend proxies, which is what the cells actually tested.

## 2. Beta-free cells: dollar-neutral momentum does not survive either

| cell | class | n | PF | daily bps | CI-LB | halves | verdict |
|---|---|---|---|---|---|---|---|
| H-226 long-3/short-3 6m | EQUITY | 179 | 1.32 | 1.79 | **−0.75** | [1.57, 2.01] | REFUTED_OR_WEAK |
| H-227 long-2/short-2 3m | CRYPTO | 147 | 0.92 | −1.27 | **−5.90** | [−2.18, −0.36] | REFUTED_OR_WEAK |

Both have positive point estimates in at least the equity case, and both fail the
lower bound. `H-227` is outright negative: shorting the losers of a 6-coin
universe has been a losing trade in every half of the sample — in crypto the
loser tends to bounce.

This is the useful negative result. It says the equity momentum result (`H-201`)
is **not** purely a market-neutral factor: stripping the market leg removes most
of the measured edge, so `H-201` carries real beta. It must be sold that way.

## 3. Funding carry: the first cell with a real mechanism and a real cost cliff

The OKX archive here covers only 9 months — 8 monthly buckets, `INSUFFICIENT_N`.
`ccxt` was already a dependency, so `tools/fetch_funding_history.py` pulls the
perpetual funding history directly: **32,350 settlements, 2021-01-01 → 2026-11-22**,
2,152 daily observations for `H-228` (delta-neutral perp/spot, equal weight over
BTC, ETH, BNB, SOL, XRP).

| drag (bps/day) | mean bps/day | annualised | Sharpe | verdict |
|---|---|---|---|---|
| 0.00 | 1.925 | **+7.28 %** | 3.42 | (gross, not a claim) |
| 0.25 | 1.675 | +6.37 % | 2.53 | |
| 0.50 | 1.425 | +5.24 % | 2.09 | |
| **1.00 (pre-registered)** | **0.925** | **+3.43 %** | **1.65** | **FAILS_2X_COST** |
| 2.00 (2× variant) | −0.075 | −0.27 % | −0.13 | |

Registered result: `n=71` monthly buckets, PF **2.07**, CI-LB **+0.143 bps**,
halves **[+1.504, +0.346]**, CI-LB @2× **−0.857**. It clears the lower bound and
both halves at 1× drag and dies at 2×. **Verdict: `FAILS_2X_COST`.**

The honest reading: funding is the only crypto return stream in this repo that is
not beta, it is positive in both halves of five years, and its entire result sits
inside a cost assumption I chose rather than measured. The 1 bps/day drag was
meant to cover margin rebalancing; a book that simply leaves collateral posted
does not pay it. **I am not moving the registered number to make the cell pass** —
the registered verdict stands at 1 bps/day, and the sensitivity table is published
so a reader can see exactly what assumption their view depends on.

Known gate limitation, recorded rather than exploited: `G6` compares a cell to
buy-and-hold of its own benchmark. For a delta-neutral cell that statistic is
meaningless (it scores −6.8 bps/day against BTC simply because BTC rose). A
market-neutral cell should be scored against cash plus its leverage constraint.
That is a **new gate (`G6c`), not applied retroactively to this round's verdict**.

## 4. The headline nobody wants: EQUITY no longer passes

Adding three cells raised the declared trial count from 23 to 29, which raises the
expected-maximum Sharpe that `G4` deflates against (0.04173 → 0.04695 daily).
`H-201` moved from `dsr 0.9749` to **`dsr 0.9469`** — below the 0.95 bar.

| cell | n | PF | daily bps | CI-LB | CI-LB @2× | halves | excess | DSR | verdict |
|---|---|---|---|---|---|---|---|---|---|
| H-201 xsmom top-3 6m | 179 | 2.74 | 11.521 | 7.246 | 7.002 | [9.991, 13.051] | **+5.784** | **0.9469** | **FAILS_MULTIPLICITY** |

Everything else about the cell is unchanged and strong: the cost stress, the split
halves, the benchmark excess and the lower bound all hold. It fails one gate, by
0.003. Two honest readings, and I will not choose the flattering one silently:

- **Conservative:** at the true cumulative trial count the desk has run, an
  observed Sharpe this good is not yet distinguishable from the best of 29
  zero-skill tries at 95 % confidence. Verdict: not proven.
- **Mechanistic:** the trial penalty assumes the 29 trials were independent draws
  at the same thing. They were 10 asset classes × different mechanisms, and the
  DSR penalises the desk for having searched wide — which is exactly the
  behaviour M-107 exists to make honest. The penalty is correct to apply.

Either way: **no class currently passes every gate.** The prior claim that EQUITY
passes was true at 23 trials and is not true at 29. That is what the gate is for.

## 5. Multiplicity is getting worse, and that is information

PBO(CSCV) rose 0.08 → **0.345** as cells were added. Still below 0.5, so the
selection process is not yet picking the in-sample winner reliably, but it is no
longer near-zero. Forty cells over ten classes is a search, and the report should
read like one.

## 6. What this round changes about the plan

1. **Stop adding long-only variants.** They are beta with extra steps and the
   benchmark gate rejects them for the right reason.
2. **The two live candidates are different in kind:** `H-201` (equity cross-sectional
   momentum, beta-bearing, fails multiplicity by 0.003) and `H-228` (funding carry,
   market-neutral, fails 2× cost). Neither is money.
3. **Measure the cost assumption instead of asserting it** — for funding carry that
   means an actual margin-rebalancing schedule, not a constant drag.
4. **G6c for market-neutral cells** must be registered before the next sweep, not
   after seeing that it would help.

Full table: `reports/2026-11-22-per-class-edge-results.md` · JSON:
`reports/per_class_edge_2026-11-22.json` · Carry sensitivity:
`reports/funding_carry_sensitivity_2026-11-22.json`
