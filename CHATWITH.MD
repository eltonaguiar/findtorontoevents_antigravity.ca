# CHATWITH -- Institutional Backtest Integration

Date: 2026-04-01  
Related context: `CHATWITHIT.MD`

## What Was Integrated

### 1) New production strategies (multi-asset)
Added 5 stricter strategies to `alpha_engine/proven_scanner_strategies.py`:
- `proven_donchian_adx_trend`
- `proven_volatility_compression_breakout`
- `proven_forex_london_sweep_reversal`
- `proven_etf_dual_momentum_rotation`
- `proven_futures_term_structure_proxy`

Each includes explicit TP/SL, confidence logic, and minimum R:R gating.

### 2) Institutional validation harness
Added `alpha_engine/validation/institutional_backtest_suite.py` and integrated it into `.github/workflows/walk-forward-backtest.yml`.

The suite consumes existing walk-forward outputs and adds:
- Multiple-hypothesis correction (Benjamini-Hochberg + Bonferroni)
- Fisher combined p-value across tested strategies
- Bootstrap confidence intervals via Monte Carlo engine
- Pick-level risk diagnostics (PoL, SL-hit frequency, R-multiple proxy, VaR/CVaR)
- Cross-asset holdout summary bucket

Output artifact:
- `alpha_engine/data/institutional_backtest_report.json`

## Test Execution (Extensive)

### Static checks
Executed:
- `python -m py_compile alpha_engine/validation/institutional_backtest_suite.py`
- `python -m py_compile alpha_engine/proven_scanner_strategies.py`
- `python -m py_compile alpha_engine/validation/metrics.py`
- `python -m py_compile alpha_engine/validation/monte_carlo.py`
- `python -m py_compile alpha_engine/validation/purged_cv.py`
- `python -m py_compile alpha_engine/validation/walk_forward.py`

Result: all passed.

### Full institutional suite run
Executed:
- `python -m alpha_engine.validation.institutional_backtest_suite --strategy-results alpha_engine/data/walk_forward_results.json --pair-results backtest_results/walk_forward_results.json --output alpha_engine/data/institutional_backtest_report.json --bootstrap-sims 3000`

Result file generated successfully.

## Key Results (from institutional report)

Source: `alpha_engine/data/institutional_backtest_report.json`

### Multiple-testing / significance
- Strategies evaluated: 5
- Fisher combined p-value: `0.000004`
- Significant after BH + Bonferroni:
  - `ema_crossover`
  - `bollinger_bounce`

### Portfolio risk (pair-level walk-forward aggregate)
- Trades: 934
- Win rate: 38.65%
- Probability of loss: 61.35%
- Max drawdown: 98.456%
- Sharpe: 1.589
- VaR95 / CVaR95: -1.5% / -1.5%

### Pair-level stress red flags
- High SL-hit frequency:
  - `SOL/USDT`: 98.46%
  - `DOGE/USDT`: 96.55%
  - `ARB/USDT`: 91.84%
  - `ETH/USDT`: 87.85%
- Best resilience in this sample:
  - `TRX/USDT`: 430 trades, PoL 33.49%, cumulative pnl proxy +6.42

### Bootstrap robustness
- Simulations: 3000 (block bootstrap)
- Sharpe CI (5%-95%): `-1.748` to `5.292`
- Total-return CI (5%-95%): `-0.894` to `767.758` (very wide; indicates instability in current distribution)

## Interpretation
- The new validation layer is now in CI and reproducible.
- Current legacy walk-forward sample remains unstable across many symbols despite isolated significant strategy names.
- No strategy passed the stricter "robust edge candidate" gate (BH-significant + OOS quality thresholds).

## Next hardening steps
- Add transaction-cost + dynamic slippage model into walk-forward generator before computing p-values.
- Add purged K-fold pass/fail as a required gate in workflow.
- Add strategy-level MAE/MFE logging in resolver/backtester to replace proxy-only risk metrics.
- Run cross-asset holdout on true mixed-asset strategy set (current sample is mostly crypto).
