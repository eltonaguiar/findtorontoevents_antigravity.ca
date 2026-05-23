# Prompt Critique

## Summary Verdict
`NEEDS_SCAFFOLDING`

The prompt has a strong foundation with detailed context, clear data, and a structured output format. However, it lacks specific constraints and examples to guide the engines toward consistent outputs. Without additional scaffolding, there is a risk of divergent interpretations of "strategy variants" and "signal-emission paths," leading to varied or speculative responses.

## Suggested Rewrites
- **Original:** "propose 3-5 concrete, implementable strategy variants OR signal-emission paths that translate the academic edge into live `/audit` picks."
  - **Fix:** "Propose 3-5 concrete, implementable strategy variants for FUTURES trading that translate the academic edge (e.g., low MDD in long-only backtest) into live `/audit` picks. Focus on time-series momentum or trend-following approaches, avoiding speculative or untested methodologies."
    - **Reason:** Narrows the scope to specific types of strategies (momentum/trend-following) to reduce variance in engine outputs and aligns with the provided backtest context.
- **Original:** "Must explain why the academic edge (MDD 6.57% long-only) hasn't materialized in live emitters."
  - **Fix:** "Must explain why the academic edge (MDD 6.57% long-only) hasn't materialized in live emitters, focusing on potential issues like data discrepancies, transaction costs, slippage, or signal decay in real-time environments."
    - **Reason:** Provides specific failure modes to consider, reducing the likelihood of vague or speculative explanations.
- **Original:** JSON schema field `"thesis": "<1-sentence why this should work>"`
  - **Fix:** `"thesis": "<1-sentence explanation of why this strategy should replicate or improve upon the academic backtest edge (e.g., low MDD or high WR)>"`
    - **Reason:** Ties the thesis explicitly to the provided backtest results, ensuring relevance and consistency across responses.

## Overlooked Topics (Consider Adding)
- **Execution Costs and Slippage:** The prompt does not mention transaction costs or slippage, which are critical in translating academic backtests to live trading. Adding a requirement to estimate or account for these in the strategy proposals would ground the responses in practical realities.
- **Risk Management Rules:** The prompt does not ask for specific position sizing or stop-loss rules in the strategies, which could lead to incomplete or unrealistic proposals. Including a requirement for basic risk controls would improve implementability.
- **Backtest Period Sensitivity:** The prompt does not ask engines to consider whether the backtest results (e.g., 13.3 years) are robust across different market regimes (e.g., bull vs. bear markets). Adding a question about regime-specific performance could yield more robust strategies.

## Ambiguities Flagged
- **"Strategy variants OR signal-emission paths":** Engines may interpret this as either new trading strategies or modifications to data pipelines, leading to inconsistent outputs (e.g., some engines might propose code changes instead of trading rules).
- **"Translate the academic edge into live `/audit` picks":** The term "translate" is vague—engines might propose wildly different approaches (e.g., new data sources vs. tweaking existing signals) without clear guidance on scope.
- **"Differentiation from existing":** The phrase is unclear about whether engines should compare to the provided backtest variants (long-short/long-only) or to the failing live emitters. This could lead to inconsistent benchmarks for differentiation.
- **"Fail mode":** Without examples or guidance, engines might provide generic failure modes (e.g., "overfitting") rather than specific risks tied to FUTURES trading or the provided data.

## Estimated Variance Reduction
`MEDIUM (10-30%)`

The suggested rewrites and additional topics would reduce variance by providing clearer boundaries on strategy types, failure modes, and practical considerations. However, some inherent variance remains due to the creative nature of proposing new strategies, which cannot be fully constrained without stifling useful diversity.

## Best Engine for THIS Prompt
`deepseek`
- **Reason:** DeepSeek has strong analytical capabilities for structured financial data and JSON output compliance, which aligns well with the detailed backtest context and strict output format required here.