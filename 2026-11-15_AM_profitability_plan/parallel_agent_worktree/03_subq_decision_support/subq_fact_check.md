# SubQ API Key Usage & Fact-Checking Framework

## SubQ API Keys Found

**Location:** `session-ses_e2d8.md` (hardcoded in plain text — rotate immediately if still active)

| Variable | Key | Source |
|----------|-----|--------|
| `SUBQ_FREE_API_KEY` | `sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV` | session-ses_e2d8.md |
| `SUBQ_TOKEN_API_KEY` | `sk-proj-7IuzAriNQVjz7lnikGi2Hi45c4j084O7` | session-ses_e2d8.md |

**Security warning:** These keys are committed in plain text. Rotate them and remove from the file and git history.

**Note:** `dbpasses.txt` does NOT exist. SubQ keys are NOT in dbpasses.txt.

## SubQ Endpoints & Models Found

- **Endpoint:** `https://api.subq.ai/v1/systemone`
- **Model:** `subq-snap-1.2`
- **Reference files:**
  - `2026-11-15_1227AM_profitability/buffy/07_subq/subq_run_20261115T002920Z.json`
  - `2026-11-15_1227AM_profitability/buffy/07_subq/subq_run_20261115T002900Z.json`

## How to Use SubQ for Decision-Making

SubQ should be used as a **second-opinion / cross-validation layer**, not as a primary signal generator. Recommended usage:

1. **Strategy idea validation:** Ask SubQ to evaluate a proposed strategy's economic logic before backtesting.
2. **Fact-checking:** Ask SubQ to verify claims made by peer reviews or backtest results.
3. **Coverage gap identification:** Ask SubQ to identify missing risk factors, cost components, or regime considerations.
4. **Benchmark comparison:** Ask SubQ to compare proposed strategy vs known benchmarks (SPY, buy-and-hold, etc.).

## Fact-Checking Protocol (Critical)

**Never trust SubQ output blindly.** Every SubQ response must be fact-checked against logical principles grounded in reality.

### Fact-Check Checklist

For any SubQ response about a trading strategy or financial claim, verify:

| Check | Question | Pass/Fail |
|-------|----------|-----------|
| **Economic logic** | Does the strategy have a sound economic rationale (risk premium, behavioral anomaly, market microstructure)? | |
| **Cost inclusion** | Are transaction costs, slippage, fees, and spread explicitly netted? | |
| **Multiple testing** | Was the strategy selected from many candidates? If so, was Bonferroni/Benjamini-Hochberg or similar applied? | |
| **Out-of-sample** | Was the strategy tested on data NOT used for parameter selection? | |
| **Effective N** | Is the sample size sufficient after accounting for autocorrelation and overlapping windows? | |
| **Regime robustness** | Does the strategy work across bull, bear, and sideways markets? | |
| **Benchmark comparison** | Is the strategy compared to a transparent benchmark (SPY total return, buy-and-hold, cash)? | |
| **Execution realism** | Are fill prices realistic (gap-aware, intrabar, not idealized)? | |
| **Survivor bias** | Does the backtest avoid delisted/survivor-biased securities? | |
| **Look-ahead bias** | Is any future information leaked into the signal? | |

### Red Flags in SubQ Responses (Auto-Reject)

- "This strategy has a Sharpe of 3.0 with no costs mentioned" → Reject
- "Backtested on 10 years of data with no OOS split" → Reject
- "Won a TradingView contest" → Treat as anecdote, not evidence
- "No drawdown" or "guaranteed profit" → Reject immediately
- "Works on all asset classes" → Reject (no universal edge exists)
- "Parameters optimized on full sample" → Reject (overfitting)

## SubQ Prompt Templates for Decision Support

### Template 1: Strategy Logic Evaluation
```
Evaluate the following trading strategy for economic soundness:
- Asset class: [CRYPCO/EQUITY/ETF/etc.]
- Signal: [description]
- Holding period: [days/weeks/months]
- Proposed entry/exit rules: [rules]
- Benchmark: SPY total return

Tasks:
1. State the economic rationale (or explain why none exists).
2. Identify all cost components that must be netted (spread, commission, slippage, fees, funding).
3. Identify potential look-ahead bias or survivor bias.
4. State what out-of-sample test design you would require.
5. Give a probability (0-100%) that this strategy has genuine edge after costs.
6. List 3 specific reasons it might fail in live trading.
```

### Template 2: Fact-Check a Backtest Claim
```
Fact-check the following backtest claim:
- Claim: [PF/WR/Sharpe/MaxDD numbers]
- Asset class: [class]
- Sample period: [dates]
- Number of trades: [n]
- Costs included: [yes/no]

Tasks:
1. Identify missing information needed to validate the claim.
2. State which statistical tests (DSR, PBO, SPA, block bootstrap) are required.
3. Calculate minimum n required for statistical significance at 95% confidence.
4. State whether the claim passes or fails the "sniff test" for economic plausibility.
5. Recommend accept / reject / needs-more-evidence.
```

### Template 3: Coverage Gap Analysis
```
Analyze coverage gaps for [asset class] strategy research:
- Existing strategies: [list]
- Data sources: [list]
- Known bugs/failures: [list]

Tasks:
1. Identify missing data (NAV history, contract identity, yield/duration, etc.).
2. Identify missing risk factors (regime, correlation, tail risk).
3. Identify missing cost components.
4. Prioritize gaps by impact on profitability decision.
5. Recommend next data build or kill decision.
```

## Integration with Pipeline

1. Before any strategy advances to backtesting, run SubQ Template 1.
2. Before any backtest result is trusted, run SubQ Template 2.
3. Before any asset class is unblocked, run SubQ Template 3.
4. Log all SubQ queries and responses in `audit_dashboard/data/subq_decision_log.json` with timestamp, prompt, response, and fact-check verdict.

## Go/No-Go Rule for SubQ Input

SubQ can recommend "proceed to backtest" but CANNOT override the hard gates:
- DSR ≥ 0.95
- PBO ≤ 0.10
- Cost-adjusted PF ≥ 1.15
- Forward n ≥ 100 over ≥ 3 months

If SubQ says "go" but the gates say "no," the gates win.
