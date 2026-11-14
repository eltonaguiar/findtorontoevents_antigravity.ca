# Peer review — `research/profitability/` (23 candidates, v1–v4)

**Verdict: CONFIRMED. This is the strongest statistical work in the repository, and its negative
result is correct.**

## What it did

23 pre-registered candidates across four locked protocols, spanning crypto TSMOM, RSI(2) on equities
and sectors, cross-sectional momentum and reversal on 30 crypto pairs and 50 ETFs, country rotation,
and crypto funding carry. Gates set before results: OOS Sharpe, DSR at cumulative N, bootstrap 5th
percentile, PBO/SPA, cost and execution-lag stress.

## Why the negative result is credible

1. **It killed its own winner.** H10 mechanically passed every gate (Sharpe 1.83, CAGR 22.0%, DSR 0.978
   at N=12, p=0.00194) and was then downgraded by its own adversarial review for a contaminated OOS,
   effective N≈38 (DSR 0.9365), ex-best-day (0.8993), 2-day lag (0.696), and the fact that ~83% of
   capital sat in T-bills during a high-rate regime. Publishing that downgrade against its own result
   is the behaviour of an honest program.
2. **Its VWAP falsification matches mine.** It reports Sharpe 3.76 → ~1.18 (t=0.91, p=0.18), CSCV PBO
   0.84–0.97, 61% of trades breaching stops intrabar (PF 0.81, −17.4%), OOS 7.18 months rather than
   22. I reached the same conclusion by a different route (the implied 1.84%/yr volatility on a
   40%-sized 4h crypto book). Two independent refutations landing on the same verdict is the strongest
   form of corroboration available here.
3. **It states the economic significance problem.** v4's funding carry has DSR 1.0 and Sharpe 6.4–14.2
   *on notional*, but at realistic capital it returns 3.7–4.1% against 4.5% cash, and the only variant
   clearing cash (BTC-only, 4.8%) has 10 rebalances. Recognising that a high Sharpe on a low-vol
   carry is not an equity-beating edge is precisely the error its peers made and it avoided.

## Where it agrees with this analysis

| Question | Their answer | My measurement |
|---|---|---|
| Is any candidate proved? | No — 0/23 | No — no class above water after costs |
| Is RSI(2) on equities an edge? | H7 1.50 Sharpe vs 18.6% B&H; H10 downgraded | EQUITY +2.9pp margin, t=1.52 — candidate only |
| Is crypto directional tradeable? | H3 −0.00, H4 0.06, H13 −0.18, H14 −0.36, H15 0.20, H20 −0.08 | CRYPTO PF 0.768, −837.8pp |
| Does the dashboard's PF mean anything? | No (VWAP artifact) | No (exit-mix artifact) |

## Where I would push back

- **The 23-candidate count is too low for the claim "the retrospective hypothesis space is exhausted."**
  My own 40-trial search independently produced 0 passes, so the conclusion happens to hold, but 23
  candidates across 4 families is not exhaustion — the 170-ledger benchmark in
  `audit_dashboard/data/benchmark_ledger_proof.json` shows this repo has tried far more than 23
  configurations, and those trials count toward the same multiple-testing budget.
- **v3/v4 were not independently replicated** (their own SCORECARD says so, 8/10). Their negative
  results are probably right but rest on a single implementation.
- **The capital-efficiency framing deserves one more iteration for carry.** "3.7% vs 4.5% cash at 1.5×
  capital" assumes spot+perp consumes 2× capital. A perp-only short-funding-harvest (no spot leg)
  halves the capital drag, which is the difference between sub-cash and useful. That is a modelling
  choice, not a data limitation, and it is worth one run.

## Bottom line

If any future claim in this repo says "this is profitable", the first question should be whether it
would survive the program's gates. On the evidence, none of the 23 candidates or the 170 benchmark
ledgers would.
