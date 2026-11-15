# Further questions essential to finding a profitable algorithm

> Beyond the standard "pre-register, go out-of-sample, add costs" checklist. These are the
> questions whose *absence* we believe caused years of failure here. Answer them in writing
> before the next round of strategy research; treat unanswered as blocking.

## A. Questions about the EDGE itself
1. **What is the mechanism?** Why would this edge exist *today* and still exist after we
   trade it — who loses money to us, and why do they keep losing it? (If the answer is
   "nobody / it's just patterns", expect decay.)
2. **What is the edge's half-life?** What evidence would tell us it has decayed — and what
   is the pre-registered kill rule for when it does?
3. **Capacity:** how much capital until the edge is gone? At $10k, $100k, $1M? (Small edges
   that work at $1k but die at $50k are still worth having — but say so.)
4. **What is the honest base rate?** For a rule set like ours (N strategies × M variants ×
   K classes), how many apparent winners does pure chance predict? (B8 answered this once:
   4 of 170 vs 8.5 expected. Compute it *before* the next hunt.)
5. **Which benchmark are we beating and why that one?** (SPY? 60/40? cash? risk-parity?
   A leveraged version of the same exposure?) — pick per strategy, pre-register.

## B. Questions about MEASUREMENT (the repeated root cause here)
6. **Can we prove any single PnL number end-to-end?** Pick 10 closed picks: stored entry,
   stored exit, independent market data for both timestamps, our fee model — does it
   reconcile to the cent? If not, nothing else matters. (QA_PLAN Gate 1/3.)
7. **What fraction of our "0% PnL" rows are real zeros vs missing data?** (Was 81% fake.)
8. **Are fills real?** Every SL/TP claim: did price actually trade through that level in
   that window — using *our* fill convention, not the strategy's? (B4: 52–56% didn't.)
9. **Is the data live or frozen?** What is the max age of each feed feeding each surface,
   and who is alerted when it stops? (hyro feed was 157h stale; two surfaces 404'd.)
10. **Which of our two surfaces is right when they disagree?** Is there a canonical ledger
    yet? (170 ledgers, no single source of truth.)

## C. Questions about STATISTICS
11. **How many total hypotheses have we tested — across ALL agents, ALL years?**
    (This number is required for any p-value we ever quote again.)
12. **What would a strategy that only LOOKS good due to costs/latency look like in our
    data?** Do we have a "fake winner detector" (gross vs net, entry-at-signal vs
    entry-at-candle, slippage-resampled)?
13. **Is our n counting independent trades?** 200 trades in one correlated week on BTC =
    maybe 10 independent bets. What is the *effective* n?
14. **Walk-forward stability:** does the strategy's rank among its peers hold across
    halves/windows, or does the "winner" rotate every re-fit? (Our variant-C check:
    rank stability is the test, not total PF.)
15. **Regime question:** in which market regimes has the candidate lost money, and is the
    regime where it wins still present? (2022, COVID, Aug-2024 carry unwind, latest 6mo.)

## D. Questions about EXECUTION & COSTS
16. **What is our TRUE round-trip cost per class** (commission + spread + slippage + borrow
    + funding), measured from fills, not assumed? (Crypto stop-fill overshoot ate ~98.8% of
    class losses before it was modeled.)
17. **Slippage stress:** what happens to PF if slippage doubles? Halves? Is there a
    breakeven slippage number above which the strategy dies? (Variant C breakeven:
    0.416%/trade — how close is our real cost?)
18. **Order-book reality:** for our size, do we get filled at the shown price or better/worse?
    Have we measured queue position / market impact at all?

## E. Questions about PROCESS (why years passed without convergence)
19. **Who can say NO?** What artifact stops a strategy from being promoted — and has it
    ever actually stopped one? (Gates existed but FDR/single-source gates were default OFF.)
20. **What did we kill this month, and what did we keep that we should have killed?**
    (Survivorship inside our own process: FOREX mutation-before-kill, CRYPTO SWING PF 0.457
    still emitting.)
21. **Is every claim in our dashboards dated, sourced, and hash-stamped?** (Refuted VWAP
    rows still advertised VALIDATED; verdicts without evidence_hash.)
22. **Paper-trading honesty:** are our paper trades executed at signal-candle prices with
    recorded fills — or at lookback-adjusted convenience prices? (B4 again.)
23. **What is the ONE number the team is currently optimizing?** If it's "number of
    strategies with PF>1.5", that's the multiple-testing trap. Better: "forward,
    cost-adjusted, benchmark-relative expectancy per strategy at n≥100".
24. **When will we know to stop?** Pre-commit: if no class passes gates by <date>, we
    pivot resources to the allocation sleeve (which does not need alpha) — define <date>.

## F. Questions for the mutual-fund/ETF track specifically (user's conviction)
25. **What would falsify "mutual funds win given enough time"?** (Define it: e.g., after
    5 years of rotation sleeve net Sharpe < 0.4 or Calmar < 0.5 → fall back to pure
    buy-and-hold of the same index.)
26. **Is the edge we seek in funds actually BETA + COST discipline** (our honest answer so
    far: yes) — and if so, what research budget is justified for *alpha-on-top*? Cap it.

---
*These questions are deliberately falsifiable. If a research round cannot answer at least
Q6, Q11, Q16, Q19 and Q23 with numbers, it has not earned new strategy trials.*
