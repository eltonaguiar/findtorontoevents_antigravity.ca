# Essential Questions to Find a Profitable Algorithm

Ask these of every candidate strategy:

1. What is the economic or behavioral reason this edge should exist and persist?
2. After realistic costs and slippage, does it still have positive expectancy?
3. Does it beat the simple buy-and-hold benchmark of the same asset on a clean out-of-sample or forward period?
4. What is the information coefficient (or equivalent predictive power)? Is it distinguishable from zero?
5. How many independent observations (trades or periods) support the result? (n < 100 is weak; n ≥ 500 is more convincing.)
6. What is the maximum drawdown, and can the strategy survive it without forced liquidation or behavioral breakdown?
7. How sensitive is the result to small changes in parameters or data? (Overfit test.)
8. What is the probability of ruin under the proposed position sizing?
9. Has this idea been published or widely known for years? If yes, why hasn't the edge been arbitraged away?
10. Can we pre-register the exact rules and success criteria before seeing the out-of-sample results?
11. What would cause us to kill this strategy permanently?
12. Is the data free of look-ahead, survivorship, and fill biases?

If a strategy cannot answer most of these convincingly, it is not ready for capital.
