# Commodity TSMOM — clean-bar backtest: REJECTED by the gate-stack (2026-06-03)

Same clean-bar method as the ETF sleeve (PR #502). Canonical commodity archetype: time-series
momentum (each commodity long iff own trailing 12m beats cash; equal-weight; else cash). Universe
DBC/GLD/USO/DBA/SLV/UNG vs BIL, real yfinance daily, 48mo walk-forward, fixed params.

## Result — does NOT clear the gate-stack
| Metric | Value | Bar | Pass? |
|---|---|---|---|
| Profit factor | 1.69 | ≥1.5 | ~ (weak) |
| Sharpe | 0.67 | ≥1.0 | ❌ |
| Max drawdown | **−33.8%** | ≤20% | ❌ |
| Win rate | 58.3% | — | — |
| **#111 attribution vs DBC** | alpha 0.49%/mo, **t=0.84**, IR 0.12, **beta 0.72** | t≥2.0 & IR≥0.10 | ❌ |
| **Bootstrap PF 95% CI** | **[0.78, 3.93]** | lower>1.0 | ❌ |

## Read
Commodity TSMOM is **mostly broad-commodity beta** (market_beta 0.72 vs DBC) with **no significant
alpha** (t=0.84) and a too-deep 34% drawdown. Not a forward-test candidate.

## Why this is a GOOD result
The gate-stack **discriminates**: ETF dual-momentum PASSED (beta 0.34, t=2.36, MDD 12%); commodity
TSMOM FAILED (beta 0.72, t=0.84, MDD 34%) on the identical pipeline. That is the harness doing its
job — it admits real alpha and rejects beta-in-disguise. Logged as an honest negative; not promoted.

## Reproduce
`python3 verified_strategies/commodity_tsmom_backtest.py`
