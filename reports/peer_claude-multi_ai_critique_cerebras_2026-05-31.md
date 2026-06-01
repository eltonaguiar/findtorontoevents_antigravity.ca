# Peer critique — Cerebras (gpt-oss-120b) — 2026-05-31

**Endpoint:** https://api.cerebras.ai/v1/chat/completions
**Model:** gpt-oss-120b (requested llama-3.3-70b → 404 not_found; only `gpt-oss-120b` and `zai-glm-4.7` accessible on this free key)
**Key env:** CEREBRAS_FREE_API_KEY
**Status:** ok
**Agree with brief:** 78%

## Parsed JSON critique

```json
{
  "missing": [
    "Explicit transaction-cost and market-impact modeling",
    "Latency and order-book depth considerations for HFT regimes",
    "Robust out-of-sample cross-validation beyond simple walk-forward (e.g., nested CV)",
    "Tail-risk metrics (e.g., CVaR, max drawdown, drawdown-to-recovery)",
    "Data-snooping and look-ahead bias checks (e.g., future-label leakage)",
    "Stress-testing under extreme market regimes"
  ],
  "wrong": [
    "n >= 500 trades may be excessive for high-frequency strategies where trade count is huge but per-trade expectancy is tiny",
    "Bonferroni correction assumes independence; the seven gates are highly correlated, making the threshold overly punitive",
    "Wilson lower-bound applied to win-rate without accounting for asymmetric win/loss definitions can mis-estimate true edge",
    "PF bootstrap lower-bound > 1.2 is unrealistic for many low-volatility strategies and can mask over-fitting",
    "HHI < 0.30 as a concentration metric ignores temporal clustering of PnL"
  ],
  "additions": {
    "execution": [
      "Model per-trade slippage as function of volatility, volume, order-size",
      "Include commission, exchange fees, clearing costs",
      "Simulate fill probability and partial fills in intrabar replay",
      "Market-impact function calibrated to historical order flow"
    ],
    "regime": [
      "Statistical regime-change detectors (Chow test, rolling kurtosis); re-train per regime",
      "Separate validation windows for bull/bear/sideways",
      "Minimum performance thresholds in each regime before promotion"
    ],
    "live_vs_paper": [
      "Shadow paper orders in live market to capture latency + fill-rate drift",
      "Track realized vs simulated PnL divergence; de-qualify if drift > 5%",
      "Validate timestamps and bar alignment identical paper-vs-live"
    ],
    "sizing": [
      "Kelly / fractional Kelly based on edge + variance",
      "Cap position by volatility-scaled risk budget (e.g., 1% equity/trade)",
      "Max-drawdown limits (20% equity) + dynamic leverage reduction",
      "Position-limit matrix to prevent symbol+strategy concentration"
    ]
  },
  "predicted_bugs": [
    "Off-by-one when counting TIME_EXIT in WR denominator",
    "HHI computed on raw PnL instead of absolute contribution",
    "Bootstrap with replacement that preserves temporal order (breaks independence)",
    "Permutation test shuffling W/L without preserving autocorrelation (inflates significance)",
    "Walk-forward loop fails to drop oldest month -> overlapping train windows + leakage",
    "DSR using raw Sharpe instead of de-biased Sharpe (optimistic)",
    "PBO using one-sided instead of two-sided test (under-reports overfit)"
  ],
  "agree_with_brief_pct": 78
}
```

## Raw response

```json
{"id":"chatcmpl-30b1b1e9-0795-471b-afa8-4bbc5ef13d92","model":"gpt-oss-120b","choices":[{"finish_reason":"stop","message":{"content":"<JSON above>"}}]}
```

## Notes
- Free-key model swap: llama-3.3-70b not available; fell back to gpt-oss-120b.
- Strong takes: Bonferroni-with-correlated-gates is over-punitive; n>=500 wrong axis for HFT; live-vs-paper PnL drift >5% as de-qualification trigger; predicted bootstrap-temporal-order bug is consistent with our intrabar/winsorize fixes today.
