# EQUITY Cross-Sectional Momentum — clean-bar backtest: MIXED, NOT promoted (2026-06-03)

Same clean-bar method as ETF (#502 PASS) / commodity (#506 REJECT) / FX (#508 MIXED). Cross-sectional
momentum on mega-caps (AAPL/MSFT/NVDA/GOOGL/AMZN/META/JPM/V/UNH/COST/LLY/AVGO), top-3 by trailing 12m
that beat cash, monthly, vs BIL. Benchmark SPY. 48mo walk-forward, fixed params.

## Result — strong raw metrics, but fails the alpha gate
| Metric | Value | Bar | Pass? |
|---|---|---|---|
| Profit factor | 3.53 | ≥1.5 | ✅ |
| Sharpe | 1.65 | ≥1.0 | ✅ |
| Max drawdown | −14.8% | ≤20% | ✅ |
| CAGR | 52% | — | — |
| Bootstrap PF 95% CI | [1.73, 7.91] | lower>1 | ✅ |
| **#111 attribution vs SPY** | alpha 2.0%/mo, **t=1.98**, IR 0.31, **beta 1.13** | t≥2.0 | ❌ (just misses) |

## Read — why NOT promoted despite Sharpe 1.65
1. **Attribution fails:** t=1.98 < 2.0 (alpha not statistically significant) and **beta 1.13 > 1** — the
   sleeve is *amplified equity beta* (more than 100% SPY exposure), so most of the 52% CAGR is levered
   market, not stock selection. The marginal alpha is not significant.
2. **Survivorship bias:** the universe is today's mega-cap winners, hand-picked with hindsight. This
   upward-biases the backtest materially. A real test needs a point-in-time universe (no look-ahead on
   membership) — not done here.

## Verdict
Strong-looking but **MIXED — not a forward candidate**. The Sharpe is real but it is high-beta +
survivorship, with sub-threshold alpha. Honest non-promote. Contrast ETF dual-momentum (beta 0.34,
t=2.36) which earns its return with low beta + significant alpha.

## Scorecard (4 archetypes, identical pipeline)
| Archetype | Attr t | beta | Sharpe | bootstrap lower | Verdict |
|---|---|---|---|---|---|
| ETF dual-momentum | 2.36 | 0.34 | 1.62 | 1.64 | **VALIDATED** |
| Commodity TSMOM | 0.84 | 0.72 | 0.67 | 0.78 | REJECTED |
| FX trend | 2.13 | −0.61 | 0.42 | 0.63 | MIXED (alpha real, weak) |
| EQUITY momentum | 1.98 | 1.13 | 1.65 | 1.73 | MIXED (high-beta + survivorship) |

Still only ETF dual-momentum clears all gates with genuine low-beta alpha.

## Reproduce
`python3 verified_strategies/equity_momentum_backtest.py`
