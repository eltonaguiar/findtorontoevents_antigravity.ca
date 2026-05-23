# Asset-Class Edge Report

Source: `closed_picks.json` — 8421 resolved picks.
Thresholds: best-edge n>=20, consistent n>=30, low-sample n<20.

## 1. Overall performance per asset class

| Asset class | n | WR | PF | total pnl% |
|---|---|---|---|---|
| UNKNOWN | 2 | 100.0% | 999.00 | 5.0% |
| COMMODITY | 354 | 60.2% | 2.28 | 596.9% |
| EQUITY | 44 | 36.4% | 0.71 | -28.2% |
| CRYPTO | 6884 | 32.8% | 0.41 | -105682.8% |
| FOREX | 932 | 25.6% | 0.35 | -212.9% |
| FUTURES | 203 | 3.0% | 0.06 | -536.6% |
| STOCKS | 1 | 0.0% | 0.00 | -4.5% |
| BOND | 1 | 0.0% | 0.00 | -46.3% |

## BOND — strategy breakdown


## COMMODITY — strategy breakdown

- **Best edge:** `cot_positioning` — PF 4.64, WR 78.2%, n=133
- **Most consistent:** `cot_positioning` — WR 78.2%, PF 4.64, n=133
- ⚠️ **Possible mis-ban:** `cftc_cot_commercial_signal` is BLOCKED (retired) but its closed history is WR 74.8% / PF 4.52 / n=131 — human review.

## CRYPTO — strategy breakdown

- **Best edge:** `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — PF 60.54, WR 96.8%, n=31
- **Most consistent:** `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — WR 96.8%, PF 60.54, n=31
- **High-edge / low-sample (investigate — broke or regime-specific):**
  - `ml_enhanced_ZKUSDT_4h_D_ensemble_stack` — PF 999.00, WR 100.0%, n=9
  - `ml_enhanced_BNBUSDT_15m_B_lightgbm` — PF 58.82, WR 89.5%, n=19
  - `macd_crossover` — PF 4.09, WR 68.8%, n=16
  - `rsi_overbought` — PF 2.25, WR 60.0%, n=5

## EQUITY — strategy breakdown

- **Best edge:** `stocks_rsi2_pullback` — PF 0.97, WR 37.8%, n=37
- **Most consistent:** `stocks_rsi2_pullback` — WR 37.8%, PF 0.97, n=37

## FOREX — strategy breakdown

- **Best edge:** `cta_cross_asset_tsmom` — PF 2.04, WR 57.6%, n=177
- **Most consistent:** `cta_cross_asset_tsmom` — WR 57.6%, PF 2.04, n=177

## FUTURES — strategy breakdown

- **Best edge:** `futures_momentum` — PF 0.03, WR 2.0%, n=201
- **Most consistent:** `futures_momentum` — WR 2.0%, PF 0.03, n=201

## STOCKS — strategy breakdown


## UNKNOWN — strategy breakdown
