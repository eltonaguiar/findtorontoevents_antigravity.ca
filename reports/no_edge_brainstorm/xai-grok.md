# xai-grok — no-edge brainstorm

1. ROOT CAUSE

The zero-edge outcome is structural, not operational. First, the pipeline treats every public or semi-public feature set as a candidate without an explicit information-edge budget; once latency, dissemination, and crowding are priced in, the residual alpha is negative for any signal observable to a small team. Second, the validation stack never enforced a pre-specified family-wise error rate across the 149-variant sprawl; every “ml_enhanced” variant was accepted or rejected on its own in-sample Sharpe, guaranteeing that the reported tail (PF 6.67) is a multiple-testing artifact. Third, the kill-threshold ratchet was itself fitted on rolling windows whose size was smaller than the typical regime length, so any genuine low-frequency edge was mechanically truncated before it could compound.

2. PER ASSET CLASS

CRYPTO — On-chain order-flow imbalance from exchange-level funding and liquidation cascades. Use 5-minute snapshots of perpetual funding rates plus open-interest changes from the top three venues; compute a signed pressure metric (funding delta × OI delta). Acceptance test: purged walk-forward Sharpe > 0.8 net of 3 bp round-trip on the top-10 liquid coins, 2019–2025, with White’s Reality Check p < 0.05 against 500 random permutations.

EQUITY — Do not trade this class. All retail-accessible factors (value, momentum, earnings) are either arbitraged or require millisecond co-location and direct feeds; any edge that survives the audit’s kill-threshold will be smaller than execution slippage on a small-team budget.

COMMODITY — Term-structure roll yield conditional on inventory surprises. Construct a weekly series of unexpected inventory changes (EIA, USDA) versus the shape of the futures curve (front-minus-second nearby). Acceptance test: long-only roll-yield strategy in the top quintile of positive surprises, held to next inventory release, net of realistic roll and margin costs, deflated Sharpe > 0.6 on 2005–2025 data after CPCV blocking by contract cycle.

FOREX — Do not trade this class. G10 and emerging-market pairs are dominated by central-bank flows and dealer inventory that are invisible to retail data; any statistical regularity collapses once bid-ask bounce and weekend gaps are modeled.

ETF — Overnight versus intraday variance ratio on sector ETFs that embed hard-to-borrow names. Measure the ratio of close-to-open versus open-to-close realized variance; tilt exposure when the ratio exceeds its 90-day median by two standard deviations. Acceptance test: long-short ETF book with 2-day hold, transaction-cost adjusted, minimum 200 independent trades, CPCV-blocked by calendar quarter, deflated Sharpe > 0.7.

BOND — Do not trade this class. Cash Treasuries and futures are dominated by dealer balance-sheet constraints and futures-roll mechanics that require prime-brokerage data feeds unavailable to a small team.

3. METHODOLOGY

Replace the current mining loop with a two-stage gate. Stage one: pre-register at most five feature families per asset class and a single test statistic (e.g., deflated Sharpe). Stage two: run combinatorial purged cross-validation with 20 embargoed blocks sized to the dominant autocorrelation horizon (5 days for crypto, 22 days for commodities). Apply White’s Reality Check and Hansen’s SPA test to the entire pre-registered family; retain only configurations whose p-value survives a 5 % FDR threshold. Enforce a hard minimum of 300 non-overlapping trades per candidate before any live allocation. Any configuration that fails the gate is archived and never re-tested on the same sample.

4. THE 3 HIGHEST-EV MOVES

1. Build the on-chain crypto pressure metric above and run the 300-trade CPCV gate; acceptance = deflated Sharpe > 0.8 and White p < 0.05.  
2. Implement the commodity inventory-surprise roll-yield rule with the same validation stack; acceptance = positive expectancy after full transaction costs and regime-blocked out-of-sample.  
3. Add the ETF overnight-variance-ratio tilt as a 5 % risk sleeve and subject it to the identical minimum-n and multiple-testing filter; acceptance = net Sharpe > 0.7 with turnover below 15× per year.

5. WHAT TO STOP DOING

Kill the ml_enhanced generator and all 149 variants immediately; they are data-mined noise. Remove the kill-threshold ratchet; it is itself an over-fitted filter that destroys sample size. Cease any re-use of the same price or volume series for both signal construction and execution modeling without an explicit latency and dissemination lag.
