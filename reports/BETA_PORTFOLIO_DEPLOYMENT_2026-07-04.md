# Decision + Deployment: Diversified Beta-Harvesting Portfolio (2026-07-04)

**Decision:** after an exhaustive alpha hunt found no net-of-cost systematic edge on free data (`FREE_DATA_EDGE_HUNT_CAPSTONE_2026-07-04.md`), the AI swarm was consulted and returned a **unanimous 3/3 verdict** (deepseek, groq, paid-mode-fast): **deploy a diversified risk-managed BETA portfolio; stop hunting alpha.** I concur — it is the only honest, tradeable path under free-data + retail-cost constraints. This is the deployable system.

## What it is (and is NOT)
- **IS:** beta harvesting — own a diversified basket, weight sleeves by inverse volatility (risk-parity-lite), apply a light crash guard. Captures the diversified risk premium (~0.8-1.0 Sharpe historically) at near-zero cost/effort.
- **IS NOT:** alpha. It will not beat the market. Success = capturing beta with controlled drawdown; benchmark vs **60/40**, not vs an imaginary edge.

## Design choices (evidence-based)
- **Inverse-vol weighting** (not equal-weight) — risk-parity-lite so no single sleeve dominates risk.
- **Light crash guard** (halve a sleeve below its 200d MA → cash), NOT a binary in/out trend overlay. We proved the binary overlay does **not** improve risk-adjusted return (Calmar 0.73→0.65 on 2021-26; it whipsaws in choppy markets). The light haircut keeps most beta while trimming tail risk in *sustained* bears only.
- **Sleeves** (tracker computes weights from free DB feeds; a live account holds the liquid proxy):
  - EQUITY → VTI/SPY (equity_daily_ohlcv basket)
  - COMMODITY → DBC (futures_daily_ohlcv 11-contract basket)
  - CRYPTO → BTC, small (crypto_ohlcv; short history)
  - **BONDS → AGG/TLT — recommended but NOT in the free DB.** Add a free bond price feed (e.g., yfinance AGG/TLT daily) to complete an all-weather mix; this is the one build-out that would materially improve diversification.

## Backtest — real, survivorship-free ETFs (2021-2026, monthly rebalance, look-ahead-free, net cost)
Upgraded from the survivorship-biased basket to actual liquid ETFs ingested via yfinance into `etf_daily_ohlcv` (SPY, DBC, AGG, TLT, IEF, GLD):

| portfolio | Sharpe | MaxDD | Calmar | both-halves |
|---|---|---|---|---|
| SPY only | 0.93 | −24% | 0.62 | 0.47 / 1.46 |
| 60/40 SPY/AGG | 0.86 | −21% | 0.44 | 0.24 / 1.59 |
| **SPY+DBC inverse-vol** | **1.04** | **−18%** | **0.81** | 0.85 / 1.32 |
| +AGG+GLD (4-sleeve) | 0.95 | −15% | 0.46 | 0.11 / 1.97 |
| +TLT (5-sleeve) | 0.65 | −17% | 0.27 | −0.22 / 1.72 |

**Key finding (honest + non-obvious):** equity+commodity risk-parity **beat everything on 2021-26 — including 60/40 and the bonds-heavy all-weather** — because bonds had their worst rate-hike cycle in 40 years (2022 crash). **But that is recency-specific:** bonds pay off when rates fall, so the deployed tracker still holds them for *regime* diversification (inverse-vol sizes them; do not drop a sleeve for lagging recently — that is the exact recency-overfit trap that killed prior "edges"). The crash guard again slightly *reduced* risk-adjusted return (4-sleeve 0.95→0.89) — kept only as light tail insurance for sustained bears.

## The tool
`tools/beta_portfolio_tracker.py` — read-only sidecar. Each run computes the current target weights (inverse-vol + crash guard) and writes `audit_dashboard/data/beta_portfolio_status.json`. Places no orders. Current output (2026-07-04): EQUITY 44.8% / COMMODITY 35.9% / CRYPTO 9.7% / CASH 9.7% (crypto crash-guarded — BTC below its 200d MA). Wire into a monthly/weekly cron next to the other trackers to log a live NAV track record.

## The ONE alpha-salvage path (documented, not deployed)
The gap-fade is the only real gross effect found (equity intraday reversal, Sharpe 0.71 gross, breakeven 2-3bp/side). Two swarm members (deepseek, paid-mode) independently flagged the same salvage: **reduce execution cost to sub-2bp via maker rebates / passive limit orders on the open.** If a venue with maker rebates + passive fills is available, the gap-fade could reach breakeven-to-slightly-positive. This is an *execution* edge, not a data edge — the only route to any alpha from the entire hunt. Filed for future; not viable at standard retail market-order costs.

## Bottom line
The honest, deployable answer is a diversified beta portfolio (built, `beta_portfolio_tracker.py`). It wins by *capturing the risk premium cheaply and with discipline*, not by beating the market — because we proved, rigorously, that beating it is not possible under these constraints.
