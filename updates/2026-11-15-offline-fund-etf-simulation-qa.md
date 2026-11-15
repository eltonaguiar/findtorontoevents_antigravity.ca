# Offline fund/ETF simulation and accounting QA

The user requested executed historical simulations and a forward-tracking protocol, not production trading changes.

## Problem addressed

Positive pick returns, fund price growth and lower drawdown can be mistaken for account-level, benchmark-beating alpha. Overlapping trade compounding, fees, current-versus-exit timestamps and same-close execution can fabricate apparently profitable results.

## What was added

An opt-in standalone research runner, focused tests, immutable source/NAV evidence, frozen H-142/H-143 simulation plan and forward CSV/protocol in [the dated package](../2026-11-15_AM_profitability-plan/copilot-financial-review/README.md). Canonical preregistration commit199ddeb3ea6dcb726ee268378c8d0446e6276e58 preceded implementation/backtesting.

The runner models funded fractional total-return units, next-close decisions, drift and transaction costs. It rejects invalid prices/calendars/weights. It is **not wired to production**, has no credentials/network/order/DB capability, and changes no production picks or gates.

## Verification and result

From the dated package:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s . -p test_simulation_runner.py -v
PYTHONDONTWRITEBYTECODE=1 python3 simulation_runner.py run --input market_prices.csv --output simulation_results.json
```

Actual:13tests passed after11expected initial failures and two added cost-boundary failures;14passive closed-form terminal accounts and28,120NAV rows reconciled. Independent review identified one-time boundary fees being resampled as ordinary returns; the runner now applies them exactly once at each simulated path's endpoints. Realized account NAV remained byte-identical. FXAIX five-year modeled net CAGR11.61% and24.50%drawdown; fixed tactical CAGR9.34% vs matchedSPY18.09%, **screen false** under both5/20bps costs.

No predictive profitability was certified. Source/fill/PIT/tax limits and conditional-simulation caveats are documented in [executed results](../2026-11-15_AM_profitability-plan/copilot-financial-review/09_EXECUTED_SIMULATIONS.md). Forward tracking remains unstarted; code/report publication is not capital deployment.
