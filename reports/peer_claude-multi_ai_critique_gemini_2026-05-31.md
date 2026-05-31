# Multi-AI Critique — Gemini (gemini-2.5-pro/flash fallback)
Date: 2026-05-31
Author: claude-opus-4-7 (orchestrator) → Google Gemini
Endpoint: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
Model used: gemini-2.5-flash (gemini-2.5-pro free-tier quota was 0; falling back to flash succeeded after quota wait loop)
Key used: GOOGLE_GEMINI_API_KEY (primary, after a 429 wait window)
Status: ok
Agreement with brief: 90%

## Raw API JSON response
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          { "text": "<see parsed JSON below>" }
        ],
        "role": "model"
      },
      "finishReason": "STOP"
    }
  ],
  "modelVersion": "gemini-2.5-flash",
  "usageMetadata": "see /tmp/gemini_raw.json"
}
```

Full unprocessed payload preserved at `/tmp/gemini_raw.json` during run.

## Parsed model critique (JSON, as returned)

```json
{
  "missing": [
    "Max Drawdown, Calmar Ratio, or Sterling Ratio as hard gates for risk-adjusted return.",
    "Liquidity and Capacity Analysis: explicit gates for maximum position size relative to market liquidity (e.g., % of ADV), and estimated market impact.",
    "Explicit look-ahead bias checks beyond just intrabar replay (e.g., ensuring indicator calculations only use past data, no future corporate actions).",
    "Comprehensive data quality checks: survivorship bias, delisting events, corporate actions (splits, dividends), and stale data handling.",
    "Robustness testing: sensitivity analysis of strategy performance to small changes in key parameters.",
    "Stress testing: evaluation of strategy performance during extreme historical market events (e.g., 2008 financial crisis, flash crashes, specific sector downturns).",
    "Portfolio correlation/diversification metrics: how a new strategy correlates with existing ones or broad market indices.",
    "Average trade duration: a gate to ensure strategies align with intended frequency and risk profile (e.g., avoiding illiquid positions).",
    "Explicit gate for transaction costs (commissions, fees, slippage) as a percentage of gross PnL or per trade."
  ],
  "wrong": [
    "n >= 500 closed trades: too strict for low-frequency strategies (decades of data needed) and potentially too low for HFT with tiny edges/high variance — context-dependent.",
    "Bonferroni p < 0.0071: overly conservative when gates are correlated (which they are). Prefer Holm-Bonferroni, FDR (Benjamini-Hochberg), or permutation-based FWER.",
    "Walk-forward 12mo/1mo/1mo: fixed window may not suit all regimes; consider adaptive windowing or event-driven validation. 'By class' is vague.",
    "NEVER cap closed pnl_pct to [SL,TP]: too absolute — if the live execution system enforces hard SL/TP, realized PnL IS capped. The real rule is don't cap simulated PnL when the underlying strategy could exceed bounds; cap only when it reflects realized execution truth."
  ],
  "additions": {
    "execution": [
      "Dynamic bid-ask spread modeling (time-varying by liquidity/vol).",
      "Market impact models (linear / sqrt / Almgren-Chriss) based on order size vs ADV / instantaneous depth.",
      "Comprehensive fee structure (commissions, exchange, clearing, regulatory).",
      "Latency effects, especially for HFT — slippage from network/execution delay.",
      "Partial fills + queue position simulation against order-book depth."
    ],
    "regime": [
      "Structural break tests (CUSUM, Chow) on inputs and PnL series.",
      "Regime indicators (VIX, rate differentials, cycles, cross-asset correlations) to define states.",
      "Adaptive strategy logic — parameter switch / exposure reduction on regime flip.",
      "Performance attribution by regime (bull/bear/sideways, high/low vol)."
    ],
    "live_vs_paper": [
      "Define divergence KPIs (daily-PnL correlation, trade count, avg-PnL/trade, MDD) with hard thresholds.",
      "Automated divergence reports + alerts on threshold breach.",
      "Root-cause framework: data-feed / latency / market-impact / broker / model-drift / infra.",
      "Shadow trading — identical logic + order routing alongside live for real-time delta."
    ],
    "sizing": [
      "Fractional / modified Kelly (risk-controlled vs full Kelly).",
      "Portfolio-level VaR / CVaR + correlation-aware allocation.",
      "Dynamic position sizing on realized vol, confidence, equity.",
      "Hard maximum capital-at-risk per strategy and per portfolio with drawdown ceilings."
    ]
  },
  "predicted_bugs": [
    "Data synchronization issues — historical-provider vs paper-feed vs live-feed mismatches (TZ, corporate actions).",
    "Execution logic mismatch — paper-pilot order-type / fill / race conditions diverging from backtest.",
    "Underestimation of slippage / costs — paper inflates vs live.",
    "State management errors — open positions / cash / indicator state across restarts/halts.",
    "Reporting/aggregation bugs — same family as the ETF n=4 INSUFF aggregation bug; will recur.",
    "TIME_EXIT misclassification regression — exclusion bug re-emerges in pilot perf calc.",
    "Unhandled market events — circuit breakers, delistings, feed outages crash the pilot.",
    "Latency in signal-to-fill higher than backtest assumes — missed opportunities / worse fills.",
    "Symbol universe discrepancies between backtest set and paper-pilot tradable list."
  ],
  "agree_with_brief_pct": 90
}
```

## Top three actionable takeaways for our 30-day pilot

1. **Risk-adjusted hard gate is missing** — add an MDD / Calmar gate alongside PF and WR. Current brief can pass a high-PF strategy with a 40% drawdown.
2. **Bonferroni is too punitive for our gate structure** — gates 1-5 are correlated (n drives WR LB, bootstrap PF, perm p simultaneously). Switch to Benjamini-Hochberg FDR at q=0.05 or compute joint permutation FWER.
3. **Aggregation/misclassification bugs will recur** — Gemini independently predicted the ETF-aggregation and TIME_EXIT-exclusion bugs reappear in pilot harness. Add automated invariant checks (per-class n totals reconcile across raw/policy_clean/edge_stability cohorts) as a pilot precondition.

## Provenance

- API call script: `/tmp/gemini_brief.py`
- Raw response: `/tmp/gemini_raw.json` (8591 bytes)
- Parsed JSON: `/tmp/gemini_parsed.json`
- Retry handling: 429 quota wait-loop, completed on free tier `gemini-2.5-flash` after `gemini-2.5-pro` returned `Quota exceeded ... limit: 0`.
