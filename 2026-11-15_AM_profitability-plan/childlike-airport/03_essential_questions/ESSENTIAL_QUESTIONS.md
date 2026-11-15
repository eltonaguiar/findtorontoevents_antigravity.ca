# 03 — Essential Questions to Find a Profitable (or Robust) Algorithm

Answer these with evidence (data queries, logs, reproducible notebooks), not intuition. A “no/unknown” on P0 questions blocks deployment.

## P0 — Truth & measurement (if wrong, nothing else matters)
1. **Is every PnL number correct?** For a random, stratified sample per class, do recomputed returns from verified entry/exit (or NAV) marks match stored PnL after unit normalization?
2. **What do 0% and blanks mean?** Per pick: flat market, stale/unquoted mark, unresolved lifecycle, coercion bug, or bad reference? (Disposition rates by class/strategy/source.)
3. **Are fills realistic?** Do TP/SL/expiry outcomes survive intrabar/next-bar/gap-aware replay with adverse assumptions? What % of “wins” would be losses under conservative fills?
4. **Is there leakage or look-ahead?** Any same-bar/signal-bar entry, future data in features/labels, survivorship-biased universes, or post-hoc universe selection?
5. **Are timestamps, timezones, and calendars correct?** Session boundaries, holidays, next-NAV (MF), contract rolls, funding timestamps aligned?
6. **What is the canonical cohort?** Can we reproduce headline WR/PF/n from a single deduped, provenance-tagged dataset (with filter hash)?

## P0 — Economics & benchmark
7. **Net of *all* costs, is expectancy positive?** Fees, spread, slippage, market impact, funding, borrow, roll, taxes/turnover — per class and per sleeve.
8. **What is the correct benchmark/hurdle?** Does it beat SPY/total-market/T-bill/risk-matched blend **on a risk-adjusted, net basis** (not just raw return)?
9. **Is it alpha or beta/regime luck?** Decompose vs market factor(s); does edge persist in bear/sideways/high-vol subperiods?
10. **Is the sample meaningful?** Effective-N, trade independence (clustered bets?), and concentration (top symbol/strategy/day/source contribution).

## P1 — Statistical validity
11. **Would this survive multiple testing?** DSR (with true trial count), PBO/CSCV, and adjusted p-values; what happens to “best” strategies after selection bias correction?
12. **Is performance stable?** Walk-forward/OOS consistency, parameter sensitivity (± small perturbations), and decay over time.
13. **What is the capacity?** At what AUM/liquidity does impact/slippage erase the edge? (Especially crypto small-caps, FX/ETF spreads, event markets.)
14. **Tail & drawdown profile?** Max DD, ulcer/index, CVaR/ES, worst streak, time-underwater — can we survive the worst plausible path?

## P1 — Implementation & operations
15. **Can we execute it as specified?** Latency, partial fills, rejects, borrow/short availability, margin/PDT, market hours/halts.
16. **Data quality & provenance:** point-in-time? vendor revisions? corporate actions/splits/dividends/NAV adjustments correct?
17. **What exactly triggers a trade and an exit?** Fully specified, versioned rules (no discretion) with auditable signals.
18. **Monitoring & kill-switches:** What live metrics trip halt/demote (drift, slippage vs model, DD, staleness, reconciliation breaks)?

## P2 — Product/strategy choice
19. **Which 1–2 sleeves merit focus now?** Rank by (expected net edge × confidence) / (complexity × data risk × time-to-proof); rotate out after repeated nulls.
20. **Allocation vs prediction:** For each dollar, is expected risk-adjusted outcome higher in low-cost beta/TAA or in this active signal after all frictions and uncertainty?
21. **Prediction markets specifically:** Do we have timestamped, net, capacity-aware records showing copied entries beat a fair baseline after fees/limits and adverse selection?
22. **Mutual funds:** Can we support next-NAV, fee/constraint-aware, benchmark-relative evaluation — and are we claiming allocation discipline rather than intraday alpha?
23. **What would falsify this fastest?** Pre-define the cheapest, highest-power test that would kill the hypothesis (and run it before building more).

## Minimum “profitable algorithm” evidence package
- Pre-registered hypothesis & universe; frozen params; canonical dataset hash.
- Gross & net returns, benchmark-relative; n, effective-N, horizon.
- Risk: Sharpe/Sortino/Calmar, MDD, CVaR, exposure/concentration.
- Validity: OOS/walk-forward, DSR/PBO, multiple-testing accounting, stability.
- Execution realism: fills/costs/slippage sensitivity.
- Forward: paper/live-shadow track record with kill criteria met/not met.
