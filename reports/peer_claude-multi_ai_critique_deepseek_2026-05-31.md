# Peer Critique — DeepSeek (deepseek-chat / deepseek-v4-flash)

Date: 2026-05-31
Source: Multi-AI red-team fan-out of Claude opus-4-7 Day-1-close methodology brief.
Endpoint: https://api.deepseek.com/v1/chat/completions
Model returned: deepseek-v4-flash
Status: ok
Agree-with-brief: 75%

## Parsed JSON critique

```json
{
  "missing": [
    "Survivorship bias: backtest only includes symbols that still exist; dead symbols dropped inflate PF",
    "Look-ahead bias: using future data for corporate actions, index rebal, or fundamental releases",
    "Out-of-sample decay: no explicit decay test (e.g., half-life of edge over rolling windows)",
    "Multi-collinearity among gates: Bonferroni assumes independence; correlated gates inflate false rejections",
    "Data snooping: no penalty for number of strategies tested before selection (e.g., 1000 strategies, 7 pass by chance)",
    "Transaction cost model: no bid-ask spread, market impact, or commission assumptions in backtest",
    "Liquidity filter: no minimum volume or market cap gate; illiquid symbols can produce phantom edges",
    "Regime shift detection: no structural break test (e.g., Chow, CUSUM) on strategy performance",
    "Live-paper divergence: no explicit threshold for divergence (e.g., Sharpe ratio drop > 0.5) before reversion",
    "Capital allocation: no Kelly fraction or risk parity; equal-weight allocation can lead to ruin",
    "Path dependency: no Monte Carlo simulation of trade sequences to assess drawdown risk",
    "Time decay of edge: no rolling window of WR or PF to detect edge erosion"
  ],
  "wrong": [
    "n >= 500 too strict for high-frequency strategies: 500 trades may be 1 day of data; Wilson LB on WR with n=500 is overly conservative for HFT where WR is near 0.5 and variance is low; better to use minimum trading days (e.g., 20) or time-based threshold",
    "Bonferroni correction with alpha=0.05 / 7 = 0.0071 is too punitive if gates are positively correlated (e.g., WR and PF are correlated); false rejection rate increases; use Holm-Bonferroni or FDR (Benjamini-Hochberg) instead",
    "Top-3 trade concentration < 50% of positive PnL: this can be gamed by splitting trades into smaller lots; better to use Herfindahl-Hirschman Index (HHI) on trade PnL directly",
    "DSR > 0.95 and PBO < 0.05 are redundant with permutation p < 0.05; DSR already accounts for multiple testing; PBO is a different metric but often correlates; one of these can be dropped to reduce gate count",
    "Permutation p < 0.05 is weak: permutation tests only test if strategy beats random timing, not random direction; should also test against random entry/exit",
    "Walk-forward by class (12mo train, 1mo validate) may be too short for strategies with quarterly or annual signals; need adaptive window based on signal frequency"
  ],
  "additions": {
    "execution": [
      "Include slippage model: e.g., 0.5 * spread + 0.1 * (volume / avg_daily_volume) * price",
      "Include commission: e.g., $0.005 per share or 0.1% of notional",
      "Include market impact: e.g., Almgren-Chriss model for large orders",
      "Test sensitivity to slippage: e.g., double the slippage and check if PF > 1.0 still holds",
      "Include short-selling costs: e.g., borrow fee, uptick rule constraints"
    ],
    "regime": [
      "Add structural break test: e.g., Chow test on rolling WR with p < 0.05 triggers regime alert",
      "Add volatility regime filter: e.g., only trade when VIX < 30 or rolling 20-day vol < 2x median",
      "Add correlation regime filter: e.g., drop strategy if correlation to SPY exceeds 0.7 in last 60 days",
      "Add regime classification: e.g., use HMM or k-means on macro factors (rates, vol, trend) and test strategy per regime",
      "Add regime decay: e.g., if strategy fails in current regime for > 10 trades, pause and re-evaluate"
    ],
    "live_vs_paper": [
      "Set divergence threshold: e.g., if live Sharpe < paper Sharpe - 0.5 for 20 trades, flag for review",
      "Add daily PnL correlation check: e.g., if correlation < 0.8 over 30 days, investigate data feed or execution",
      "Add fill ratio check: e.g., if live fill rate < 90% of paper, flag slippage or liquidity issue",
      "Add latency check: e.g., if live execution delay > 100ms vs paper, flag for infrastructure review",
      "Add systematic bias test: e.g., paired t-test on daily returns (live vs paper) with p < 0.05 indicates bias"
    ],
    "sizing": [
      "Use Kelly criterion: f* = (p * b - q) / b, where p = win rate, q = 1-p, b = avg win / avg loss; cap at 25% of capital",
      "Add risk parity: allocate capital inversely proportional to strategy volatility (e.g., 1/vol)",
      "Add drawdown constraint: e.g., if peak-to-trough drawdown > 20%, reduce position size by 50%",
      "Add correlation-based sizing: e.g., if two strategies have correlation > 0.7, reduce combined allocation by 30%",
      "Add Monte Carlo sizing: e.g., simulate 10,000 paths with Kelly fraction and choose fraction that minimizes probability of 50% drawdown"
    ]
  },
  "predicted_bugs": [
    "Time exit trades misclassified: if TIME_EXIT trades are included in WR denominator but not in PF calculation, PF will be inflated; ensure consistency",
    "Walk-forward leakage: if train and validation periods overlap due to data alignment (e.g., using close prices from same day), edge will be overestimated",
    "Bonferroni gate count mismatch: if gates are added or removed dynamically, the correction factor (7) becomes stale; hard-code gate list and count",
    "Top-3 concentration gate fails for strategies with many small winners: e.g., 1000 trades each with 0.1% PnL, top-3 may be < 50% but strategy is still concentrated in time or symbol; add time-based concentration check",
    "DSR calculation error: DSR requires non-IID adjustment; if autocorrelation is ignored, DSR is inflated; check for serial correlation in daily returns",
    "Permutation p-value instability: with n=500, permutation p can vary by 0.02 across runs; set seed and use at least 10,000 permutations",
    "Caveat about 'Don't filter TP_HIT-only' conflicts with gate 1 (Wilson LB on WR): if WR is defined as pnl>0, then TP_HIT-only trades are wins by definition; but if TP_HIT trades are a subset, WR may be biased upward; clarify win definition",
    "Aggregation bug: if strategies are aggregated by class (e.g., ETF), but some symbols within class have n < 500, the aggregate may pass while individual symbols fail; add per-symbol gate check"
  ],
  "agree_with_brief_pct": 75
}```

## Raw API response

```json
{"id":"d0a881de-cc03-4e8f-835f-0662e1e0e1cc","object":"chat.completion","created":1780268367,"model":"deepseek-v4-flash","choices":[{"index":0,"message":{"role":"assistant","content":"{\n  \"missing\": [\n    \"Survivorship bias: backtest only includes symbols that still exist; dead symbols dropped inflate PF\",\n    \"Look-ahead bias: using future data for corporate actions, index rebal, or fundamental releases\",\n    \"Out-of-sample decay: no explicit decay test (e.g., half-life of edge over rolling windows)\",\n    \"Multi-collinearity among gates: Bonferroni assumes independence; correlated gates inflate false rejections\",\n    \"Data snooping: no penalty for number of strategies tested before selection (e.g., 1000 strategies, 7 pass by chance)\",\n    \"Transaction cost model: no bid-ask spread, market impact, or commission assumptions in backtest\",\n    \"Liquidity filter: no minimum volume or market cap gate; illiquid symbols can produce phantom edges\",\n    \"Regime shift detection: no structural break test (e.g., Chow, CUSUM) on strategy performance\",\n    \"Live-paper divergence: no explicit threshold for divergence (e.g., Sharpe ratio drop > 0.5) before reversion\",\n    \"Capital allocation: no Kelly fraction or risk parity; equal-weight allocation can lead to ruin\",\n    \"Path dependency: no Monte Carlo simulation of trade sequences to assess drawdown risk\",\n    \"Time decay of edge: no rolling window of WR or PF to detect edge erosion\"\n  ],\n  \"wrong\": [\n    \"n >= 500 too strict for high-frequency strategies: 500 trades may be 1 day of data; Wilson LB on WR with n=500 is overly conservative for HFT where WR is near 0.5 and variance is low; better to use minimum trading days (e.g., 20) or time-based threshold\",\n    \"Bonferroni correction with alpha=0.05 / 7 = 0.0071 is too punitive if gates are positively correlated (e.g., WR and PF are correlated); false rejection rate increases; use Holm-Bonferroni or FDR (Benjamini-Hochberg) instead\",\n    \"Top-3 trade concentration < 50% of positive PnL: this can be gamed by splitting trades into smaller lots; better to use Herfindahl-Hirschman Index (HHI) on trade PnL directly\",\n    \"DSR > 0.95 and PBO < 0.05 are redundant with permutation p < 0.05; DSR already accounts for multiple testing; PBO is a different metric but often correlates; one of these can be dropped to reduce gate count\",\n    \"Permutation p < 0.05 is weak: permutation tests only test if strategy beats random timing, not random direction; should also test against random entry/exit\",\n    \"Walk-forward by class (12mo train, 1mo validate) may be too short for strategies with quarterly or annual signals; need adaptive window based on signal frequency\"\n  ],\n  \"additions\": {\n    \"execution\": [\n      \"Include slippage model: e.g., 0.5 * spread + 0.1 * (volume / avg_daily_volume) * price\",\n      \"Include commission: e.g., $0.005 per share or 0.1% of notional\",\n      \"Include market impact: e.g., Almgren-Chriss model for large orders\",\n      \"Test sensitivity to slippage: e.g., double the slippage and check if PF > 1.0 still holds\",\n      \"Include short-selling costs: e.g., borrow fee, uptick rule constraints\"\n    ],\n    \"regime\": [\n      \"Add structural break test: e.g., Chow test on rolling WR with p < 0.05 triggers regime alert\",\n      \"Add volatility regime filter: e.g., only trade when VIX < 30 or rolling 20-day vol < 2x median\",\n      \"Add correlation regime filter: e.g., drop strategy if correlation to SPY exceeds 0.7 in last 60 days\",\n      \"Add regime classification: e.g., use HMM or k-means on macro factors (rates, vol, trend) and test strategy per regime\",\n      \"Add regime decay: e.g., if strategy fails in current regime for > 10 trades, pause and re-evaluate\"\n    ],\n    \"live_vs_paper\": [\n      \"Set divergence threshold: e.g., if live Sharpe < paper Sharpe - 0.5 for 20 trades, flag for review\",\n      \"Add daily PnL correlation check: e.g., if correlation < 0.8 over 30 days, investigate data feed or execution\",\n      \"Add fill ratio check: e.g., if live fill rate < 90% of paper, flag slippage or liquidity issue\",\n      \"Add latency check: e.g., if live execution delay > 100ms vs paper, flag for infrastructure review\",\n      \"Add systematic bias test: e.g., paired t-test on daily returns (live vs paper) with p < 0.05 indicates bias\"\n    ],\n    \"sizing\": [\n      \"Use Kelly criterion: f* = (p * b - q) / b, where p = win rate, q = 1-p, b = avg win / avg loss; cap at 25% of capital\",\n      \"Add risk parity: allocate capital inversely proportional to strategy volatility (e.g., 1/vol)\",\n      \"Add drawdown constraint: e.g., if peak-to-trough drawdown > 20%, reduce position size by 50%\",\n      \"Add correlation-based sizing: e.g., if two strategies have correlation > 0.7, reduce combined allocation by 30%\",\n      \"Add Monte Carlo sizing: e.g., simulate 10,000 paths with Kelly fraction and choose fraction that minimizes probability of 50% drawdown\"\n    ]\n  },\n  \"predicted_bugs\": [\n    \"Time exit trades misclassified: if TIME_EXIT trades are included in WR denominator but not in PF calculation, PF will be inflated; ensure consistency\",\n    \"Walk-forward leakage: if train and validation periods overlap due to data alignment (e.g., using close prices from same day), edge will be overestimated\",\n    \"Bonferroni gate count mismatch: if gates are added or removed dynamically, the correction factor (7) becomes stale; hard-code gate list and count\",\n    \"Top-3 concentration gate fails for strategies with many small winners: e.g., 1000 trades each with 0.1% PnL, top-3 may be < 50% but strategy is still concentrated in time or symbol; add time-based concentration check\",\n    \"DSR calculation error: DSR requires non-IID adjustment; if autocorrelation is ignored, DSR is inflated; check for serial correlation in daily returns\",\n    \"Permutation p-value instability: with n=500, permutation p can vary by 0.02 across runs; set seed and use at least 10,000 permutations\",\n    \"Caveat about 'Don't filter TP_HIT-only' conflicts with gate 1 (Wilson LB on WR): if WR is defined as pnl>0, then TP_HIT-only trades are wins by definition; but if TP_HIT trades are a subset, WR may be biased upward; clarify win definition\",\n    \"Aggregation bug: if strategies are aggregated by class (e.g., ETF), but some symbols within class have n < 500, the aggregate may pass while individual symbols fail; add per-symbol gate check\"\n  ],\n  \"agree_with_brief_pct\": 75\n}"},"logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens":891,"completion_tokens":1578,"total_tokens":2469,"prompt_tokens_details":{"cached_tokens":0},"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":891},"system_fingerprint":"fp_8b330d02d0_prod0820_fp8_kvcache_20260402"}```
