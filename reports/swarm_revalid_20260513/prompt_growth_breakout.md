# Proven backtestable patterns — growth, breakout, undervalued-rebound, trend-strength

## Context

User asks: "find us some proven backtesting strategies that really work" — trend strength, growth stocks (long-term up with minor variation), undervalued+rebound, breakouts. Need patterns that are (a) literature-confirmed, (b) backtestable with yfinance+FRED free tier, (c) classifiable per asset class.

## Existing baselines this session

- EQUITY top-5 12-1m momentum: PF 2.82 / Sharpe 1.34 / MDD 24.18% (TIER-2, near-TIER-1)
- ETF top-3 sector rotation: PF 2.05 / Sharpe 0.97 (TIER-1 PF candidate)
- BOND HYG/LQD 6m momentum: PF 1.62 (TIER-2)
- FUTURES TS-mom long-only: Sharpe 0.86 / MDD 6.57% (NEAR-TIER-1 MDD passes)
- CRYPTO sub-T2 (PF 1.25 live)

## Question to engines

Propose 5-7 ACADEMICALLY-CONFIRMED + BACKTESTABLE strategies covering:
- Trend strength (e.g., 200d-MA distance percentile, ADX cutoff)
- Growth stocks (slow-and-steady, low-vol, low-drawdown compounders)
- Undervalued-rebound (P/B + price acceleration combo)
- Breakouts (Donchian channel, 52w high, volume-confirmed)
- Quality (Piotroski F-score, Greenblatt's Magic Formula, Asness Quality-Minus-Junk)

Return strict JSON ONLY:

```json
{
  "strategies": [
    {
      "name": "<short_identifier>",
      "category": "trend_strength | growth | undervalued_rebound | breakout | quality",
      "academic_source": "<paper or industry standard, with year>",
      "signal_rule": "<exact entry condition>",
      "exit_rule": "<exit condition>",
      "universe": "<S&P 500 / Russell 1000 / US large+mid cap / etc.>",
      "expected_pf": <number>,
      "expected_sharpe": <number>,
      "expected_mdd_pct": <number>,
      "horizon": "<weeks/months>",
      "free_data_path": "<yfinance fields / FRED series / etc.>",
      "implementation_hours": <integer>,
      "killer_caveat": "<biggest fail mode>"
    }
  ],
  "single_most_proven_pattern": "<one name + why it's the most robust>",
  "top_3_for_immediate_backtest": ["<name1>", "<name2>", "<name3>"],
  "cheap_stocks_buckets_recommendation": "<sub-\\$2 / sub-\\$6 / sub-\\$10 — which bucket has the cleanest edge per literature>"
}
```

## Constraints

- All strategies must be reproducible with yfinance (price+volume+dividends, basic fundamentals via .info)
- Reject anything needing Compustat/Bloomberg paid feeds
- Must specify 10y+ backtestable history
- Reject expected Sharpe < 0.8
- MUST address user's question on penny stocks bucketing (<$2, <$6, <$10)
