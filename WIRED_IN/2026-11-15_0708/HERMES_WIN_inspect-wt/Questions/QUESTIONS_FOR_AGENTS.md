# Questions Every Candidate Strategy Must Answer

These are the canonical questions for parallel agents. A candidate that cannot answer all 12 with evidence (numbers + file paths, not adjectives) does not advance. They merge the repo's own promotion gates with the external rigorous-quant checklist.

## A. The 12 mandatory questions

1. **Economic or behavioural justification.** Why should this edge exist, who is on the other side, and why do they keep losing? "The backtest says so" is not an answer.
2. **Benchmark, named explicitly.** What exactly must it beat — SPY total return? BTC hold? 60/40? A risk-free T-bill? And by how much, net of all costs?
3. **Attribution.** Is the return alpha, or a repackaged factor tilt (momentum, value, size, carry, beta)? Show the factor regression.
4. **Multiple-testing survival.** How many configurations has the *project* tried in total? Report the deflated Sharpe and/or White's Reality Check p-value. An uncorrected Sharpe of 1.5 from a 1,000-trial search is noise.
5. **Data hygiene.** Survivorship-free universe? Point-in-time fundamentals? Any look-ahead in feature computation? Prove it with a shuff∅le control.
6. **Parameter stability.** Does the parameter set hold across rolling windows? Report the walk-forward efficiency heatmap; >20% drift between windows is a fail.
7. **Regime dependence.** Does it win in bull / bear / sideways / high-vol / low-vol? Positive expectancy in the majority, or it's a conditional trade that must be pre-registered as such.
8. **Crisis survival.** What happens in the worst 5% of historical windows — 2008, March 2020, the 2022 rate shock, the May-2021 crypto crash? Max drawdown and recovery time, not just Sharpe.
9. **Capacity and liquidity.** At what AUM does the edge disappear? What's the realistic fill at our size, including market impact?
10. **Cost margin of safety.** After spread, commission, slippage, funding/borrow and tax, what fraction of the gross edge survives? Breakeven cost level, and margin = (edge / cost) ≥ 2×.
11. **Kill switch.** What observable condition stops trading automatically, and how fast? A strategy without a defined death condition isn't deployable.
12. **Reproducibility.** Can a second researcher clone the repo, run the frozen config with the fixed seed, and get the same numbers? If not, the result doesn't exist.

## B. Additional questions this audit adds

13. **Which proof step did each *previous* attempt fail at?** (See `harvested_ideas/03_negative_result_diagnosis.md`.) Re-proposing a signal family that already died at step 2 or step 8 is a waste of a worktree.
14. **Is this a new hypothesis or a parameter tweak?** If any parameter changed after seeing results, it is a new hypothesis and must re-enter the pipeline from step 1 with a new `run_id`.
15. **What's the trial count contribution?** Every run increments the project-wide trial count that deflates everyone's Sharpe. Log it in `experiments/`.
16. **Is the failure mode a bug or a market fact?** Shuffle-control failure = bug (fix it, this is good news). Significance failure = market fact (stop). Confusing the two is how years get lost.
17. **Beta or alpha?** If the return is explainable by market exposure, the honest product is a low-cost allocation, not a prediction engine. Say which one you're building.
18. **What would falsify this in 30 days of live data?** Define the forward-test demotion threshold *before* the test starts.
19. **Does the tracker row exist?** No `run_id`, no benchmark, no fees recorded → the pick isn't a prediction, it's an anecdote.
20. **Would you put your own money in at size?** If the honest answer is no, the verdict is near-miss or dead, regardless of the backtest.

## C. Minimum evidence per answer

| Question | Minimum evidence |
|---|---|
| 1, 3 | Written justification + factor regression table |
| 2, 6, 9 | Numeric comparison table with benchmark column |
| 4 | Trial count, deflated Sharpe, WC p-value |
| 5, 12 | Shuffle-control result + reproduction command + seed |
| 7, 8 | Per-regime table + drawdown series |
| 10 | Gross vs net equity curve + breakeven cost |
| 11 | Explicit rule + trigger code path |
| 13–15 | Citation to inventory row + run_id |
| 16–20 | Written verdict in `VERDICT.md` |
