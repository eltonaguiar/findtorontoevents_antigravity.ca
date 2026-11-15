# 08 — Review: `2026-11-14_PM_plan/grok_agent` (origin/main)

**Reviewed:** `2026-11-14_PM_plan/grok_agent/{README,AGENT_PROMPTS,ASSET_CLASS_PLANS,HOLDING_PERIODS_AND_STYLES,PREDICTION_MARKETS_WHY_NO_WINNERS,EXTENSION_TO_PRIOR_ANALYSIS,ESSENTIAL_QUESTIONS,HOW_FIRMS_BECAME_TRUSTWORTHY,KEY_METRICS_MULTI_PERSPECTIVE,SUBQ_USAGE_GUIDE}.md`

## Overall
Strong, repo-aligned package. It correctly enforces measurement integrity, pre-registration, net-of-cost/OOS testing, and **explicit comparison vs buy-and-hold benchmarks** (SPY total return, BTC hold) — critical and previously under-emphasized.

## Strengths
- **Benchmark discipline:** must beat relevant buy-and-hold after costs (not absolute profit).
- **Beta vs alpha clarity:** low-cost ETFs/MFs as highest-probability lower-risk path via equity risk premium + cost/diversification (not prediction edge); core allocation need not wait for alpha.
- **Style realism:** longer-horizon/swing/CTA/dual-momentum prioritized over cost-sensitive day/scalping.
- **Prediction markets:** solid structural reasons copy-trading fails (zero-sum minus fees, bot/pro dominance, adverse selection/latency, favorite-longshot bias, size/survivorship/fill issues) and correct implication (research side-quest).
- **Actionable prompts/questions/metrics:** per-class prompts, 12 essential questions, multi-perspective thresholds with sensible Sharpe anchors and caution on extreme claims.
- **Turnaround/process lessons:** grounded emphasis on process, risk, capacity, auditability.
- **SubQ hygiene:** aid-not-oracle, no committed keys, cross-check.

## Gaps / tightenings for this repo’s evidence bar
| Area | Gap | Add |
|---|---|---|
| Integrity/fills | Generic gates miss our failure modes | Intrabar/next-bar & gap-aware fills, 0%/blank/stale disposition, unit/sign/coercion reconciliation, provenance/freshness, canonical-cohort hash |
| Statistical validity | Limited multiple-testing treatment | Effective-N, **DSR (true trial count), PBO/CSCV**, regime/subperiod stability, concentration/sensitivity |
| MF mechanics | Beta framing light on implementation | Next-NAV, trading restrictions/loads/fees, no intrabar stops; NAV-based, net-of-fee vs risk-matched benchmark |
| Famous/contest claims | Caveats present but soft | Treat Hoffman/TradingView/YouTube results as **unverified** until replicated net, OOS/forward, multi-regime (selection/survivorship/paper-fill bias) |
| Prediction markets | Good list, incomplete execution detail | Timestamped signal-vs-executable, capacity/limits, calibration/Brier, hedges/elsewhere-book context, copy-fidelity |
| SubQ | Good guardrails | SubQ/LLM triage ≠ empirical evidence and never sizing-grade |
| Crypto benchmark | BTC hold included | Also risk-matched/vol-target and stress funding/slippage/venue risk |

## Bottom line
**Adopt as a strong baseline** (especially “beat buy-and-hold/SPY net of costs” and prediction-market realism). Pair with `final_v5`-grade measurement/QA, fill-realism, and multiple-testing/forward gates before any result is promotable. Not evidence of current profitability.

## Addendum: `STRUCTURED_AGENT_PROMPT.md` (review)
**Reviewed:** `origin/main:2026-11-14_PM_plan/grok_agent/STRUCTURED_AGENT_PROMPT.md` (commit `9678c898...`).

- **Strengths:** clear objective/constraints/checkpoints, separates IS vs OOS vs forward, requires cost assumptions for every number, mandates benchmark outperformance, SubQ fact-check of “proven/contest” claims tagged `<unverified>`, explicit MF/ETF beta-vs-alpha labeling, and good safety rails (no main commits, no live trading, pause conditions). The placeholders table makes it easy to deploy across agents.
- **Tightenings for this repo:** (1) require **intrabar/next-bar or NAV/next-NAV fill realism** and disposition of 0%/blank/stale PnL in “data hygiene”; (2) add **DSR/PBO/effective-N and trial-count accounting** to thresholds (Sharpe alone insufficient); (3) require **canonical cohort hash/provenance** and reconciliation vs verified marks; (4) specify benchmark as **risk-matched total return** (and T-bill hurdle) and report alpha/beta; (5) cap “3 candidates” with pre-registration to limit multiple-testing; (6) treat SubQ/LLM fact-checks as non-sizing evidence.
- **Verdict:** strong operational upgrade over free-form prompts; adopt with the above gates to match `final_v5`/money-ready evidence standards.
