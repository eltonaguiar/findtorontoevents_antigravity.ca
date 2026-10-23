# Institutional-Gate Gap Assessment — vs the Phase 1/2/3 Standard (2026-10-22)

**Author:** Zoo (VLLM)
**Date:** 2026-10-22 ~22:35 UTC
**Purpose:** Map the institutional verification framework (Sharpe/Sortino/Calmar → bootstrap p/DSR → capacity/CVaR) against what the codebase already computes, and record the concrete gaps that block any candidate from institutional deployment.

## Summary

The system is strong on **Phase 1 (risk-adjusted)** and **Phase 2 (statistical edge)**. The entire **Phase 3 (institutional scale: measured slippage / market impact, Omega ratio, portfolio CVaR)** is essentially missing. That is precisely why 0/9 asset classes are money-ready.

## What is already implemented

| Phase | Metric | Present | Evidence |
|---|---|---|---|
| 1 | Sharpe / Sortino / Calmar | ✅ | [`alpha_engine/risk_metrics.py`](alpha_engine/risk_metrics.py:1); `alpha_engine/data/institutional_metrics.json`; `intensive_monte_carlo_report.json`; TAA reports compute Sharpe/Calmar |
| 1 | Information Ratio | ⚠️ partial | [`alpha_engine/validation/metrics.py`](alpha_engine/validation/metrics.py:1); `ab_portfolio_test.py`; `decile_test.json` |
| 2 | Bootstrap p / CI (10k) | ✅ | Used in every winner certificate |
| 2 | DSR / PBO / SPA / FDR | ✅ | `audit_dashboard/data/money_ready_verdict.json` → `details` block (`dsr`, `pbo`, `spa`, `fdr`, `expectancy`, `mdd_cvar`, `recency`) |
| 2 | Profit Factor / Expectancy | ✅ | Verdicts + `forward_candidate_scoreboard.json` |

## Missing vs the institutional bar (the gaps)

1. **Omega ratio** — no implementation anywhere in `alpha_engine/`, `audit_trail/`, or `tools/`. Nothing captures the full fat-tailed return distribution beyond Sharpe/Sortino.
2. **Measured market impact / slippage / capacity** — **absent.** All agents (GHCOPILOT, Buffy, OpenCode) explicitly flagged current cost scenarios are *illustrative* (0.10–0.30 pp), not measured execution. There is no `market_impact`/`slippage` model for any asset class. This is the single biggest institutional blocker.
3. **Explicit portfolio-level CVaR** — only `mdd_cvar` exists per-class in verdict details; there is no measured tail-loss/execution model at scale.
4. **Information Ratio** is not consistently tied to a hurdle index in candidate certificates (only in specific harnesses).

## Implication

Every current candidate — including the ETF tactical rotation — satisfies at best Phase 1+2. None can pass Phase 3 because the cost/impact layer does not exist. This is consistent with the audit verdict: **0/9 classes money-ready**.

## Suggested next step (not yet implemented)

If authorized, add `tools/institutional_gates.py` computing Omega ratio and a measured-slippage stub for the candidate cohort. This is new implementation work and requires explicit go-ahead.

### Related
- Prior verification: `updates/2026-10-22-grok-plan-cross-verification.md`
- Asset-class review: `updates/2026-10-22-asset-class-review-hidden-winners.md`
- Verdict data: `audit_dashboard/data/money_ready_verdict.json`

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
