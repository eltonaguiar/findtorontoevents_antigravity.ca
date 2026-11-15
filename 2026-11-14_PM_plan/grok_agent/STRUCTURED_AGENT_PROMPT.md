# STRUCTURED_AGENT_PROMPT.md

**Optional extra prompt** — structured, agent-friendly version for parallel research agents.

Use this when you want tighter operational constraints, explicit checkpoints, and safety rails. Fill in the bracketed placeholders before giving it to an agent.

---

## Prompt

```text
Objective
Act as the strategy research agent for [ASSET CLASS] and produce a cost-adjusted, out-of-sample-validated candidate strategy (or up to 3) that beats its buy-and-hold benchmark after costs — or an explicit "no edge found" verdict with evidence.

Starting State
Repo: [REPO PATH]. Read the package at `2026-11-14_PM_plan/grok_agent/` in this order: README.md, ASSET_CLASS_PLANS.md, ESSENTIAL_QUESTIONS.md, KEY_METRICS_MULTI_PERSPECTIVE.md, HOLDING_PERIODS_AND_STYLES.md, SUBQ_USAGE_GUIDE.md, EXTENSION_TO_PRIOR_ANALYSIS.md — plus PREDICTION_MARKETS_WHY_NO_WINNERS.md if that is the class.

Target State
For each candidate strategy:
- Answers to all 12 questions in ESSENTIAL_QUESTIONS.md
- Short economic/behavioral rationale for why any edge should exist and persist
- Data hygiene notes (look-ahead, survivorship, fill bias checks)
- Backtest artifacts: equity curve, turnover, explicit cost model
- Table: in-sample vs out-of-sample vs forward (n, WR, PF, expectancy, net Sharpe, max DD, excess return vs benchmark)
- Brief regime note if data permits
- Verdict line: <beats benchmark> or <no edge found>

Constraints
- Every active strategy MUST beat the relevant buy-and-hold benchmark after costs on clean data — [BENCHMARK]
- Report IS, OOS, and forward separately; NEVER claim OOS without a held-out window
- NO performance number without stated commissions, spread, slippage, and borrow/funding assumptions
- Apply the thresholds in KEY_METRICS_MULTI_PERSPECTIVE.md — minimum net Sharpe [VALUE]
- Use SubQ to fact-check every "proven", contest, or published-performance claim against primary sources; tag unverified claims <unverified>
- For MF/ETF: explicitly state when the result is low-cost beta capture rather than active alpha

Allowed Actions
Read repo files; write only new files under [OUTPUT DIRECTORY]
Run backtests on repo data or [DATA SOURCE]
Query SubQ using the SUBQ_API_KEY environment variable

Forbidden Actions
Do NOT commit to main, edit existing package files, or delete anything
Do NOT add paid data vendors, dependencies, or keys
Do NOT issue live-trading or position-sizing recommendations

Stop Conditions
Pause for human review when a claim stays unverified after 2 SubQ attempts, the class needs data the repo lacks, or results survive only under unrealistic costs.

Checkpoints
After each stage output: ✅ <stage> plus files touched. End with the summary table(s) and verdict line(s).
```

---

## Placeholders to fill

| Placeholder | Example |
|-------------|---------|
| `[ASSET CLASS]` | EQUITY, MF/ETF, CRYPTO, COMMODITY, FOREX, PREDICTION_MARKETS |
| `[REPO PATH]` | `./findtorontoevents_antigravity.ca` or full GitHub URL |
| `[BENCHMARK]` | SPY total return, BTC buy-and-hold, equal-weight commodity basket, etc. |
| `[VALUE]` | 1.0 (or whatever threshold you want enforced) |
| `[OUTPUT DIRECTORY]` | `research_output/equity_agent_2026-11-15/` |
| `[DATA SOURCE]` | repo data, local CSV cache, free API, etc. |

---

*This file is optional. The original free-form prompts in AGENT_PROMPTS.md remain available.*
