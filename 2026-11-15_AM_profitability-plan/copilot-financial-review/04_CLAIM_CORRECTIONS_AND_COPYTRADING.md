# Claim corrections, copytrading diagnosis and essential questions

## Corrections to the supplied November narrative

- Historical final_v4's **0/23 PROVED** is an attributed report conclusion about its tested family. This review did not rerun23hypotheses. It does not prove profitable strategies cannot exist anywhere.
- Current reviewed verdict has **zero money-ready classes**, but pooled WR~40%/IC~0 cannot be assigned to every model/horizon. Equity's published WR59.2% with PF0.9392 illustrates why a high hit rate is insufficient.
- Old n/PF/WR values must retain their date/cohort/cost definitions. Registry, verdict and recency sidecars disagree because they are not interchangeable evidence sets. See [current tables](./PROFITABILITY_FRAMEWORK.md).
- ETF coverage is not zero: actual emitters/workflows and recent open records exist. Whether it provides clean admissible returns is a different question.
- Mutual funds are not "no historical work": metadata/universe and legacy NAV-table consumers exist. A current complete production selector/execution path is **not established**, and diagnostic scripts can mutate tables.
- Equity index funds may earn a long-run risk premium but can suffer large losses and fail to beat cash/inflation/SPY. No universal probability/lowest-risk ranking follows from their wrapper or a10-year hold.
- Bond/carry/commodity risk depends on duration, credit, contract, leverage and liquidity; "ballast" is not a guaranteed hedge.
- Kelly/ATR/drawdown halts cannot rescue zero expectancy or guarantee gap-free fills. Missing Kelly inputs must not silently become old optimistic defaults.
- Adequate holding time, operating plumbing and a surviving hypothesis are different milestones; increasing scanner frequency is not increasing independent evidence.

## Why "we copied Kalshi/Polymarket winners" remains unestablished here

The most actionable verified finding is **product/lifecycle mismatch**, not an unproved universal bot explanation.

At the frozen source pin, the scheduled prediction-market orchestrator calls agents and merges underlying crypto consensus; emitted category defaults to crypto. The Kalshi agent maps series to USDT symbols. A separate BTC binary-token sidecar exists, but hardcodes dry-run and is not called by the shown orchestrator.

Relevant source references are compiled in [the full coverage map](./ASSET_CLASS_COVERAGE.md):

- `prediction_market_agents/orchestrator.py:47-49,89-127,272-274`
- `prediction_market_agents/kalshi_signal_agent.py:50-89`
- `prediction_market_agents/polymarket_btc_updown_agent.py:279-285`

Thus this path can be **a prediction-market-informed BTC strategy**, not replicated Polymarket token trades or Kalshi contract settlements. Those experiments need different benchmarks and cannot borrow event-contract payout claims.

Copytrader sources also mix wallet/leader snapshots with `reverse_engineered_multi_asset` technical rules. A wallet showing a position is not a complete observable trade lifecycle. Before attributing failure, reconstruct:

`leader information available -> follower decision -> executable follower quote/fill -> full hedged exposure -> exit/settlement -> all costs -> account NAV`.

If the first unavailable edge is leader entry/exit, follower data cannot establish copy fidelity. If the follower's rule is merely recreated from an indicator, label it reimplementation, not copy execution.

## Structural mechanisms worth testing, not assumed verdicts

Closed event-contract trading redistributes contract payoffs, before fees and collateral/funding effects; it does not inherit equity growth. This does **not** prove no trader can have positive expected return. Hedges, information and liquidity can have economic value. Other participants' losses are not evidence that this repo's exact implementation failed for the same reason.

Potential blockers: spread/fees, delayed copying, adverse selection, stale odds, unobserved hedges, partial fills, settlement ambiguities, concentration, survivorship/leader selection and inadequate capital/depth. Quantify each on the actual venue/contract/cohort.

For a simplified$1YES payoff held to settlement, modeled expectancy is `p - price - fees` per contract, before funding and other cashflows. A60%accurate forecast buying at70c loses10c in expectation before fees. Forecast skill is not price advantage. Accurate calibration, Brier/log loss, CLV and latency-aware net PnL answer different questions.

Maker-only/HFT is not the sole conceivable profitable mechanism; makers can also be adversely selected. Any slow informational candidate still needs independent calibration and executable net-price advantage. Live access, eligibility and trading authority are outside this review.

## Essential additional questions

1. Is the target absolute nominal profit, inflation-adjusted gain, SPY outperformance, passive outperformance or risk reduction? At what horizon/currency?
2. What persistent economic mechanism pays the strategy, and who rationally takes the other side?
3. What exact instrument/payoff is traded, versus merely used as a signal?
4. What information was available before each first executable decision? What was published/revised later?
5. Can the complete account be reconstructed without inventing fills, exits, costs or missing legs?
6. Does the same-period passive/cash/SPY result include total return and identical flow/funding assumptions?
7. Is the advantage more than factor beta, cash allocation, favorable exposure or one concentrated market?
8. How many variants/data views were tried across all machines, including failures and discarded runs?
9. What is the effective independent information and power to detect the minimum useful edge?
10. Can an independent implementation/vendor reproduce the result, and what data remain disputed?
11. How does the strategy behave at realistic spread/lag/size, provider outages and gaps?
12. What are capacity, margin, liquidation, borrow/roll/funding and worst joint exposures?
13. How sensitive are results to prespecified cost and parameter neighborhoods without retuning?
14. Which frozen future observation would falsify it, and who can block/retire it independently?
15. How long must a low-frequency paper experiment run, and who prevents resetting after losses?
16. What costs/taxes/access restrictions differ for actual share classes and investor currencies?
17. For copying, are leader selection/full-book histories truly PIT and follower fills replicable?
18. For event contracts, are resolution, voids, settlement and legal/API access unambiguous?
19. Can the team reproduce a negative result without relabeling it as an encouraging candidate?
20. What evidence—not an AI vote or green workflow—permits progression to the next stage?

**Scope:** public-source research and paper-design review. **Pass:** signals versus contracts distinguished. **Warnings:** incomplete source lifecycles and microstructure evidence. **Blocked:** live venue/account access, orders and capital admission. **Mitigation:** reconstruct a complete read-only lifecycle, then review any shadow implementation separately.

Prediction-market signals are informational inputs, not investment advice.
