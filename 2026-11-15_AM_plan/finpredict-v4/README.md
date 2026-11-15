# 2026-11-15_AM_plan/finpredict-v4

**Date:** 2026-11-15 (AM)
**Author:** finpredict-v4 (Kilo)
**Status:** Research/planning deliverable — no capital deployment recommendation.

---

## Core conclusion

**No asset class is currently proven profitable.** All 9 tracked classes return `sizing_allowed: false`. The path to profitability is:

1. **Fix measurement first** (QA gate validates every PnL vs real market data).
2. **Separate beta from alpha** — deployable core = index exposure; alpha research runs under strict gates.
3. **Long-term trend / momentum is the only grounded edge family** (Faber 200-day MA, AQR momentum, CTA trend). Intraday scalping/day-trading fails across all classes.
4. **Mutual funds / ETFs = highest-probability lower-risk path** — as beta allocation, not prediction.

---

## Contents

| Folder | File | Purpose |
|--------|------|---------|
| `01_per_asset_class_plans/` | `PER_ASSET_CLASS_PLANS.md` | Concrete profitability plan per class |
| `01_per_asset_class_plans/` | `PREDICTION_MARKETS_WHY_NO_WINNERS.md` | Why Kalshi/Polymarket copy trading fails |
| `02_holding_period_style_analysis/` | `HOLDING_PERIODS_AND_STYLES.md` | Holding-period × style analysis + famous algorithms reality-checked |
| `04_essential_questions/` | `ESSENTIAL_QUESTIONS.md` | 12-gate strategy vetting checklist |
| `04_essential_questions/` | `SUBQ_USAGE_GUIDE.md` | How to use SubQ (endpoint, schema, fact-check protocol) |
| `05_company_transformations/` | `HOW_FIRMS_BECAME_TRUSTWORTHY.md` | Renaissance/AQR/Winton etc. — pillars for trust |
| `06_key_metrics/` | `KEY_METRICS_MULTI_PERSPECTIVE.md` | Sharpe + thresholds from investor/fund/trader/risk views |
| `07_agent_prompts/` | `AGENT_PROMPTS.md` | Ready-to-paste prompts for parallel coding agents |

---

## How to use

- **Agents:** copy prompts from `AGENT_PROMPTS.md`; require cost-adjusted, benchmark-relative, OOS, SubQ-fact-checked results.
- **SubQ:** see `SUBQ_USAGE_GUIDE.md` — endpoint verified; don't commit keys; use as fact-checker, not source of truth.
- **Decision rule:** nothing deploys until it passes the 12 gates + 90-day paper + benchmark test.

---

## Verification notes

- SubQ endpoint reachable (`https://api.subq.ai/v1/systemone`); custom `questions` schema requires one more successful round-trip to pin exact `type` constant.
- Local LiteLLM proxy (`http://localhost:4000`) is a fallback for LLM fact-checking.
- All recommendations are grounded in repo evidence + famous-algorithm reality-checks (contest claims treated as overfit theater unless audited).
