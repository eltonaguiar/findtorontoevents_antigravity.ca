# FX Trend-Following — clean-bar backtest: MIXED, NOT promoted (2026-06-03)

Same clean-bar method as ETF (PR #502 PASS) / commodity (PR #506 REJECT). FX cross-sectional
trend-following: top-1 currency ETF by trailing 12m return that beats cash, else cash. Universe
FXY/FXB/FXA/FXF vs BIL (**FXE failed to fetch — 4-currency universe**, noted). Benchmark UUP
(dollar-bull). Real yfinance daily, 48mo walk-forward, fixed params.

## Result — partial (real alpha, but edge too weak to promote)
| Metric | Value | Bar | Pass? |
|---|---|---|---|
| Profit factor | 1.42 | ≥1.5 | ❌ (weak) |
| Sharpe | **0.42** | ≥1.0 | ❌ |
| Max drawdown | −6.9% | ≤20% | ✅ |
| Win rate | 68.8% | — | — |
| **#111 attribution vs UUP** | alpha 0.42%/mo, **t=2.13**, IR 0.31, **beta −0.61** | t≥2.0 & IR≥0.10 | ✅ |
| **Bootstrap PF 95% CI** | **[0.63, 3.36]** | lower>1.0 | ❌ |

## Read
FX trend HAS statistically significant alpha vs the dollar (t=2.13, beta −0.61 = a short-USD tilt
that adds value beyond UUP), which is genuinely interesting — but the **PF is unstable** (bootstrap
lower 0.63 < 1) and **Sharpe 0.42 is far below the 1.0 real-money bar**. The alpha is real but small;
the strategy is not robust enough to promote.

## Verdict: NOT a forward-test candidate (unlike ETF). Logged as watch/negative, not VALIDATED.

## Scorecard (3 archetypes, identical pipeline)
| Archetype | Attr t | beta | Sharpe | bootstrap lower | Verdict |
|---|---|---|---|---|---|
| ETF dual-momentum | 2.36 | 0.34 | 1.62 | 1.64 | **VALIDATED candidate** |
| Commodity TSMOM | 0.84 | 0.72 | 0.67 | 0.78 | REJECTED |
| FX trend | 2.13 | −0.61 | 0.42 | 0.63 | MIXED — alpha real, edge too weak |

Only ETF dual-momentum clears all gates. The harness produces a clean, discriminating ranking.

## Reproduce
`python3 verified_strategies/fx_trend_backtest.py`
