# Block 3 / Round D6 — Horizon Comparison (short vs long term)

**Date:** 2026-11-22 · **Tool:** [`tools/breakout_backtest.py`](../../tools/breakout_backtest.py) · **Report:** [`reports/horizon_comparison_20261122.json`](../../reports/horizon_comparison_20261122.json)

The question: *"best investment for short vs long term — GIC, savings, ETF, stocks, crypto, futures, forex?"*
Answered with measured numbers, not prose. All risky-asset figures come from
`data/cache/asset_class_review/*_5y.csv`, aligned to the same start
(2021-11-22) so they are comparable. No return series was fabricated.

## Vehicle table (measured on real data)

| Vehicle | Horizon it suits | Measured return (CAGR, 2021-11→2026-11) | Vol | Max DD | Cost drag | Investment or trade? |
|---|---|---|---|---|---|---|
| **GIC / HISA** | short + any | **not measurable from market data** — known nominal rate (~3–5%), ~0 vol, CDIC-type protection | ~0 | ~0 | none | **Investment** (capital-preserving) |
| **Broad ETF (SPY)** | long | **+10.4%/yr** (Sharpe 0.66) | 17.4% | −24.5% | ~5 bp/side | **Investment** (the benchmark) |
| **Tech ETF (QQQ)** | long | +10.8%/yr (Sharpe 0.55) | 23.4% | −35.1% | ~5 bp/side | Investment (higher beta) |
| **Small-cap (IWM)** | long | +4.0%/yr (Sharpe 0.28) | 22.5% | −28.7% | ~5 bp/side | Investment (weaker) |
| **Gold (GLD)** | long | +14.8%/yr (Sharpe 0.81) | 19.3% | −32.4% | ~5 bp/side | Investment (diversifier) |
| **Long bonds (TLT)** | long | **−8.1%/yr** (Sharpe −0.46) | 15.6% | −43.7% | ~5 bp/side | Investment (lost money this window) |
| **Crypto (BTC)** | long, speculative | +1.3%/yr (Sharpe 0.24) | 42.1% | **−72.7%** | ~10 bp/side | **Trade/speculation** (no dividend, huge DD) |
| **FX spot (EURUSD / USDJPY)** | short only | **NOT an investment return** — price change only, no carry | 7–9% | — | spread | **Trade** (zero-sum without a rate differential) |
| **Futures** | short only | **not measurable** — no forward rows; leveraged wrapper on the above | high | high | commission | Trade |
| **The pods (incl. POD-EQUITY-BREAKOUT)** | n/a | **not measurable** — 0 forward rows (`sidecar_promotion_status`: all `n=0`) | n/a | n/a | n/a | Proven nothing |

Notes:
- **FX spot is not an investment.** EURUSD spot changed −4.0% and USDJPY +44.3% over 2018-12→2026-11; neither is a return without carry/interest. Presented as price behaviour only.
- **Pods have no measurable return.** `POD-EQUITY-BREAKOUT` is pre-registered and emits zero rows; every pod in `sidecar_promotion_status` has `n = 0`. No return is invented for them. The independent breakout test (D7) is the only evidence, and it was **KILLed**.
- **Crypto is a trade, not an investment**, on this evidence: 42% vol and a −73% drawdown for +1.3%/yr.

## Horizon slices (same data, different lookback)

| Horizon | SPY | QQQ | BTC |
|---|---|---|---|
| **Short (1y)** | +9.2% | +8.0% | **−13.3%** |
| **Medium (3y)** | +18.2% | +19.4% | −2.7% |
| **Long (full 5y)** | +10.4% | +10.8% | +1.3% |

Short-term BTC was the worst; long-term it barely beat zero with a −73% drawdown.
Equities were consistent across horizons. This is a small sample (one 5-year
window) and says nothing about the next 5 years.

## GIC break-even sensitivity (NOT a fabricated series)

No GIC/savings market series exists in the repo. A GIC is a known nominal rate
with ~zero vol and deposit protection. The honest comparison is a **break-even**:
what annualized return must a risky asset earn to match a GIC, after annual cost
drag and volatility drag (`0.5·σ²`)?

| GIC rate | Cost drag | Vol 15% | Vol 30% | Vol 60% |
|---|---|---|---|---|
| 3% | 0.5% | 4.6% | 8.0% | 21.5% |
| 4% | 0.5% | 5.6% | 9.0% | 22.5% |
| 5% | 0.5% | 6.6% | 10.0% | 23.5% |
| 4% | 2.0% | 7.1% | 10.5% | 24.0% |

Reading it: to beat a 4% GIC a 30%-vol asset (like QQQ) must earn **~9%/yr**
arithmetic just to match risk-adjusted, and a 60%-vol asset (crypto) must earn
**~22%/yr**. Measured: SPY 10.4% at 17% vol (comfortably beats a 3–4% GIC),
QQQ 10.8% at 23% vol (matches a ~4% GIC), BTC 1.3% at 42% vol (loses badly to
any GIC once volatility drag is counted).

## Blunt summary

- **Actually an investment:** a broad equity ETF (SPY/QQQ) and a GIC/HISA. SPY cleared a 3–4% GIC after drag; a GIC is the risk-free floor for short horizons.
- **Actually a trade:** crypto (BTC), FX spot, futures. High vol, no yield, drawdowns that dwarf the return.
- **Proven nothing:** every pod, including POD-EQUITY-BREAKOUT. Zero forward rows, and the one independent breakout test came back **KILL** (fails the random-entry control and the selection-alpha gate). The ledger's claimed +0.61 Sharpe did not reproduce as evidence of edge.
- **Best for short term:** GIC/HISA (or T-bills) — capital preservation, ~0 vol.
- **Best for long term (on this evidence):** a broad equity ETF, held. Not a breakout strategy, and not crypto.
