# Prompt critique

## Summary verdict
`NEEDS_SCAFFOLDING`

The prompt has a solid skeleton and clear data, but lacks output constraints that will cause high variance across engines. The JSON schema is underspecified (no types, no allowed values, no required fields), and several terms are ambiguous.

## Suggested rewrites

- **"Return ONLY valid JSON"** → Add: `"Return ONLY valid JSON. Do NOT include any explanatory text before or after the JSON block. The JSON must be parseable by json.loads() without preprocessing."`
  *Reason: Engines will wrap JSON in markdown code blocks or add commentary, breaking automated parsing.*

- **"estimated improvement"** → Replace with: `"expected_impact.p6_commodity_lift_pct": "integer between 0 and 100 representing estimated percentage improvement in COMMODITY PF"`  
  *Reason: "Estimated improvement" is vague — some engines will guess a number, others a range, others a string like "moderate".*

- **"dependency_order": "which must precede which"** → Replace with: `"dependency_order": [{"predecessor": "P6", "successor": "P2", "reason": "liquidity fix needed before signal gates"}]`  
  *Reason: Free-text field will produce inconsistent formats (bullet lists, sentences, arrows).*

- **"severity": "high|medium|low"** → Add: `"severity": "high" | "medium" | "low"` (exact string literals)  
  *Reason: Some engines will use "critical", "moderate", "minor" instead.*

- **"do_first": ["P6", "Q2"]** → Add constraint: `"do_first": ["P6", "Q2"]` must be a subset of proposals listed.  
  *Reason: Engines may invent new proposal IDs not in the prompt.*

## Overlooked topics (consider adding)

- **Implementation cost estimate**: The prompt mentions "30 min work" for P6 but no cost/effort for other proposals. Engines will guess wildly.
- **Risk of breaking crypto performance**: All optimizations focus on non-crypto. What if rebalancing weights degrades the 93% crypto share?
- **Backtesting requirement**: Should proposals require historical validation before deployment? Currently implied but not explicit.
- **Regulatory/compliance angle**: FOREX and BOND may have regulatory constraints on strategy changes.
- **Rollback plan**: What if a change makes things worse? No mention of revert strategy.

## Ambiguities flagged

- **"stable" / "stressed" / "thin_sample"**: No definition of these statuses. Engines will interpret differently (e.g., "stressed" could mean high volatility, low liquidity, or regulatory risk).
- **"PF"**: Not defined. Could be Profit Factor, Performance Factor, or something else. Engines may assume different meanings.
- **"Elite score floors"**: Unclear if these are minimums to trade, minimums to be considered "elite", or admission thresholds for some system.
- **"consensus requires >=2 strategies"**: Unclear if this means 2 out of total strategies or 2 out of available strategies for that asset class.
- **"Spearman correlations"**: Not specified whether positive or negative correlation is desirable, or what threshold triggers action.
- **"do_first" vs "do_later"**: No time horizon specified (hours, days, sprints). Engines will impose their own.

## Estimated variance reduction
`HIGH (>30%)`

The current prompt will produce wildly different JSON structures, risk assessments, and prioritization orders across engines. Adding strict schema definitions, removing ambiguous terms, and constraining output format would dramatically reduce variance.

## Best engine for THIS prompt
**xai** — Most likely to follow the JSON schema strictly without adding extraneous commentary or markdown formatting. Deepseek and Groq tend to be more verbose.