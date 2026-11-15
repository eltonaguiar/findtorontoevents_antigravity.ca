# Pick Justification — Why These Picks

**Package:** WIRED_IN/2026-11-15_0135/inspect-wt
**Author:** inspect-wt · **Date:** 2026-11-15

---

## The picks, ranked, with probabilities

| # | Pick | P(success)* | Why this, here |
|---|------|-------------|----------------|
| 1 | **MF/ETF allocation sleeve** (monthly dual-momentum rotation) | 60–70% for positive net return with MDD ≤ 20% over 10y; ~25–35% to beat SPY full-cycle | The only path that needs **no alpha** — beta capture + cost discipline works even though the prediction system doesn't. Backtested in-repo, reproducible, benchmark-relative. This is what "solid MF picks" honestly means: monthly overweight/underweight recommendations on a verifiable clock, never a TP/SL pick. |
| 2 | **Variant-C strategy selection** (top-6 by trailing PF, n≥20, PF>1.3, monthly) | pilot passes T2 gates ≈ 30–40% (bootstrap P(PF≥1.15)=71%, P(total>0)=91.6%) | The **only** procedure in the repo that beats a randomization null after correction: 0/800 → p<0.0013, Bonferroni-surviving p<0.005, +98.7pp over 8 true walk-forward months, 4 consecutive improving months (Jul 0.50 → Nov 1.72). Reproduced **exactly twice** by independent peers (quant-audit, finpredict-v2). Trades where the measured cost margin lives: ETF+equity. |
| 3 | **EQUITY RSI(2) short mean-reversion trial** (pre-registered) | 25–35% (SubQ 10–25% band; ours slightly higher on cost-margin evidence) | Equity is the **only class with a measured positive cost margin** (3.23× round-trip cost vs mean +0.323%, n=738) and short-horizon reversal is one of the few retail-reachable effects with academic replication. It gets ONE trial with a trial ID — not a reopen, because #773 proved the current equity edge is beta (`NO_ALPHA_BETA`, t=1.05). |
| 4 | **CRYPTO vol-targeted trend** (BTC/ETH, conditional) | 20–30% | The only class where (a) execution is API-native, (b) data is free and dual-sourced, (c) a fill model exists. Cleanest place to prove the *process* works — even if the process's answer ends up "no". Conditional on fill-fidelity gates + killing the −328.6pp SWING emission. |

\* probabilities are subjective, stated before the forward data arrives, updated by it — method
documented in `final_v4/inspect-wt/03_risk_management/risk_management.html`.

---

## Why these and not the rest — the justification logic

**1. Benchmark-relative, not absolute.** Every pick is judged against its real alternative:
SPY B&H, 60/40, AGG+cash, or class beta. This was the correction demanded after the Nov-14
analysis ("positive PnL" is not a goal — outperforming the risk-matched benchmark is). The
sleeve's honest selling point is *drawdown reduction* (2022: +2.3% vs SPY −19.5%; COVID:
−0.8% vs −19.9%), explicitly NOT full-cycle return (8.2% vs 12.8% — that's the point of ballast).

**2. Evidence hierarchy.** A pick advances only if it survives, in order: measurement truth
(PnL verified) → cost/fill model → pre-registered split-sample/walk-forward → independent peer
reproduction → forward paper ≥24 months. Variant C cleared steps 1–4; the sleeve cleared the
backtest step; equity RSI(2) and crypto trend are at step 3 with gates fixed in advance.

**3. The cost arithmetic decides where alpha is even possible.** Measured breakeven margins:
equity 3.23× cost (only positive margin), crypto 0.58× pre-fix → ~0.80 post-fix (still negative),
FOREX structurally negative at retail spreads, COMMODITY blocked at 422% cost/PnL. You cannot
pick a class whose cost structure eats the reachable edge — this single test eliminated half
the board before any signal question was asked.

**4. Multiple-testing honesty.** The repo runs a 646-strategy universe; at p=5%, ~32 "winners"
exist by chance alone, and the live anti-overfit audit flags 69/80 (86%) OVERFIT_LIKELY. So a
pick must beat **both** the market null and the selection null. Variant C's randomization test
does exactly that (random strategy selection as null); nothing else in the repo does.

**5. Mutual funds are an allocation class, structurally.** NAV priced once daily makes intraday
TP/SL picks impossible (peer consensus, adopted). But that constraint is also why the class is
pick #1: the honest answer — capture equity/bond risk premia cheaply, rebalance monthly, keep
cash+fees discipline — works *without* the prediction system. SubQ agrees on the split: active
selection beats index after costs P(yes)=0.03; simple rotation beats cash+fees P(yes)=0.99.

---

## What would make us drop a pick (kill criteria, pre-registered)

- **Sleeve:** MDD > 20% intracycle, or 3 consecutive months negative excess vs 60/40 → fall
  back to plain 60/40.
- **Variant C:** any month PF < 0.5 twice consecutively, or 3-month rolling PF < 1.0 → stop
  and re-audit (July's PF 0.50 / −45.9pp month is the known failure mode); realized costs
  > 0.416%/trade → halt.
- **Equity trial:** fail the excess-Sharpe-vs-SPY gate at n=500 → class returns to
  measurement-baseline-only; **no re-run with different thresholds** (that's the B8 trap).
- **Crypto:** fill model unfixable, or gate miss at n=100, or failure to beat B&H BTC
  risk-adjusted → dead; no threshold shopping.
