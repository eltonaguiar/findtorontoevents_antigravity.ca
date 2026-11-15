# Proof Suite Summary Table (10-Step Non-Negotiable Standard)

- **Generated UTC:** `2026-11-15T07:45:58Z` | **Seed:** `42` | **Trials Evaluated:** `9` (cascaded against `N_repo = 646`)

| ID | Asset Class | Timeframe | CAGR Net | CAD After-Tax | Sharpe | Sortino | Calmar | MaxDD | WinRate | PF | DSR (N=9 / N=646) | Holm p | Block MC +% | Shuffle p | Gates (/10) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `E1` | ETFs | Monthly (21d rebalance) | +7.31% | +5.44% | 0.44 | 0.68 | 0.30 | -24.4% | 57.6% | 1.61 | 0.452 / 0.026 | 0.7783 | 91.6% | 0.6550 | 7/10 | **PROMISING (NEAR-MISS)** |
| `M1` | Mutual Funds | Monthly NAV (>=30d hold) | +7.49% | +5.57% | 0.45 | 0.71 | 0.31 | -24.4% | 57.6% | 1.63 | 0.472 / 0.029 | 0.7783 | 93.5% | 0.6550 | 7/10 | **PROMISING (NEAR-MISS)** |
| `MA1` | Multi-Asset (/audit Cohort) | Mixed Live Picks (Monthly Re-rank) | +10.50% | +4.84% | 0.75 | 1.22 | 1.58 | -6.6% | 46.8% | 1.19 | 0.112 / 0.001 | 1.0000 | 74.0% | 0.0550 | 5/10 | **REJECT** |
| `MA2` | Multi-Asset (Sleeves) | Monthly Risk-Parity Combo | +3.99% | +2.95% | 0.27 | 0.45 | 0.32 | -12.6% | 59.5% | 1.83 | 0.233 / 0.005 | 1.0000 | 79.9% | 0.0650 | 7/10 | **REJECT** |
| `S1` | Stocks / Equities | Swing (1-14d) | +25.94% | +18.86% | 0.93 | 1.45 | 1.35 | -19.2% | 46.7% | 1.10 | 0.135 / 0.001 | 1.0000 | 72.5% | 0.2100 | 5/10 | **REJECT** |
| `C1` | Crypto | 1h Trend (ATR TP/SL + 72h MaxHold) | -24.93% | -24.93% | -2.58 | -3.73 | -2.54 | -9.8% | 25.0% | 0.54 | 0.018 / 0.001 | 1.0000 | 5.2% | 0.5350 | 3/10 | **REJECT** |
| `B1` | Bonds | Monthly (21d rebalance) | +0.74% | +0.13% | -0.20 | -0.29 | 0.04 | -19.5% | 79.4% | 1.17 | 0.008 / 0.000 | 1.0000 | 20.4% | 0.1650 | 5/10 | **REJECT** |
| `CM1` | Commodities | Monthly (21d rebalance) | +9.08% | +6.80% | 0.59 | 1.00 | 0.48 | -18.8% | 70.3% | 1.99 | 0.678 / 0.083 | 0.2646 | 96.2% | 0.0050 | 7/10 | **REJECT** |
| `FX1` | Forex | Intraday / Swing | -1.04% | -1.04% | -1.97 | -2.62 | -0.88 | -1.2% | 43.7% | 0.87 | 0.010 / 0.000 | 1.0000 | 12.8% | 0.8800 | 3/10 | **REJECT** |

## Benchmark Reference Curves

| Benchmark | Span | CAGR | Ann Vol | Sharpe | MaxDD |
|---|---|---|---|---|---|
| `SPY_BH` | 166 bars | +12.82% | 14.3% | 0.75 | -24.8% |
| `60_40_SPY_AGG` | 166 bars | +7.31% | 9.4% | 0.54 | -21.0% |
| `AGG_BH` | 166 bars | -1.02% | 4.7% | -0.72 | -22.8% |
| `TLT_BH` | 166 bars | -2.80% | 13.2% | -0.34 | -54.5% |
| `GLD_BH` | 166 bars | +5.85% | 16.2% | 0.28 | -37.4% |
| `DBC_BH` | 166 bars | +1.39% | 17.1% | 0.02 | -61.7% |
| `BTCUSDT_3mo_BH` | 84 bars | -70.73% | 57.5% | -1.89 | -35.0% |
