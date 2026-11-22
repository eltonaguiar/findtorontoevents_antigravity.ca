
> code · nvidia/nemotron-3-ultra-550b-a55b:free

**1.** Panel A's "conf 35/30/25/20" attached to each proposed strategy is unfalsifiable — "conf" is undefined (not a p-value, posterior, or CV score), so the numbers cannot be validated or rejected.

**2.** Category error. Class-level zeros (or negative aggregates) do not rule out subset edges diluted by the majority. CRYPTO's negative mean masks potential positive sub-strategies; EQUITY's CI includes zero but the +0.098% point estimate leaves room for a mid-cap quality slice to clear the IR≥0.5 hurdle. "Blocked" applies to the *current aggregate*, not the *search space*.

**3.** Backtest the Panel B equity subset: mid-cap quality factor, 20–60 day hold, 2× slippage + funding costs, benchmarked against a matched factor model (not SPY total return). Existing n=955 provides power; one week to code, 90-day forward paper trade falsifies IR≥0.5.

**4.** Confidence: 78%. Would drop below 50% if the mid-cap quality backtest shows IR<0.3 at 2× slippage, or if the factor benchmark reveals the edge is pure beta. Would rise to 90% if a 5-year walk-forward yields IR≥0.7 net of costs.
