# Research swarm — Github strategy libraries for struggling asset classes

Three asset classes need outperformance vs current picks. Peer is on FOREX + FUTURES.
Focus this round on: **CRYPTO, ETF, BOND**.

## Current state (sub-Tier-2)

| Class | n | WR | PF | PnL % | Issue |
|---|---|---|---|---|---|
| CRYPTO | 7935 | 46.5 | 1.36 | +3019 | sub-T2 (WR<50). Top symbol BTCUSDT only 10% = diversified. Edge masked by 3-4 dragger strategies. |
| ETF | 107 | 56.1 | 1.34 | +37.5 | sub-T2 (PF<1.5). Just below T2 graduation. Top XLE 20.9%. |
| BOND | 11 | 54.5 | 0.66 | -1.5 | thin sample (n<<100 charter floor). PF<1 means losing. |

## Per-class research target

### CRYPTO (largest n, biggest impact)
Find ≥2 github libraries with backtestable strategies that have:
- Documented Sharpe > 1.5 over 3+ year live OR robust OOS
- Implementation in Python (matches our `alpha_engine/strategies/` shape)
- Free/open data sources only (no Glassnode Pro, no Refinitiv)
- Capacity > $100k notional (we don't need HFT scale yet)

Specific edge hypotheses worth verifying:
- Hyperliquid HLP carry replication (funding-rate basis trade)
- BTC seasonal-by-UTC-hour (memory shows 22 UTC = 61% WR, n=1000+)
- Cross-exchange basis arb post-BinanceUS
- On-chain whale-flow + OI delta signals
- Funding skew + taker imbalance

### ETF (closest to T2 graduation)
Find ≥2 libraries for:
- Sector rotation (XLF/XLE/XLK monthly rebalance, Sharpe 0.7-1.0)
- Risk-parity over treasury-duration + equity exposure
- EFA/VEA vs VTI international-relative-strength
- ETF momentum (12-1m or 6m skip-1m)
- Black-Litterman with sector views

### BOND (data accumulation phase)
Find ≥2 libraries for:
- TLT/IEF momentum (3yr Sharpe 1.2-1.5 historical)
- Treasury yield-curve steepener mean-reversion
- IG-credit carry post-QE
- HYG/LQD ratio mean reversion
- PIMCO BOND-fund ETF basket replication

## Constraints
- Library must be alive (commits in last 18 months)
- License must be permissive (MIT/Apache/BSD); no GPL/AGPL
- Must be importable without C++ compilation pain (we run py 3.11)
- Avoid libraries that require proprietary data feeds we don't have

## YOUR TASK

For each of CRYPTO / ETF / BOND, return:

```
## <CLASS>
candidate_1:
  repo: <github.com/user/repo>
  stars: <approximate>
  strategy_name: <one-line>
  documented_perf: <Sharpe / PF / WR / live OR OOS window>
  free_data_only: <YES|NO|PARTIAL>
  capacity_ok: <YES|NO|UNKNOWN>
  integration_effort_hours: <number>
  risk_red_flags: <e.g. backtest period excludes 2022 crash>

candidate_2: (same shape)

shortlist_recommendation: candidate_X — <one-line reason>
```

Plus one final block:

```
## Cross-class
single_repo_to_pilot_first: <repo>
why: <one-line>
estimated_time_to_first_backtest_result: <hours>
```

Keep total response under 1200 words. Be specific — repo URLs, star counts,
strategy types. Generic "use ML to predict prices" answers are useless.
