# opencode money_ready 20261020 — crypto lane

## 1. Verdict (3 lines)
- No strategy in the crypto lane is MONEY-READY. All five fail the MDD gate (and most fail DSR/PF/CI/MC).
- Closest candidate: crypto_r1 (volume >2x 20-day avg + up close, 5-day hold) — OOS n=689, PF 2.449, WR 55.73, MC 100, pf@2x 2.332, but MDD -89.85% and DSR 0.00. Classified FAIL (misses MDD).
- macd_rsi_m048 is the next closest (PF 1.56, MDD -78.11, MC 83.2). Recommend forward paper track only after adding a stop-loss/volatility sizing to fix MDD.

## 2. Step 1 idea list (crypto lane, written before seeing new results)
Count of trials = 5 (used for Deflated Sharpe).

| # | Idea | Source | Claimed n/PF | Why it stalled |
|---|---|---|---|---|
| 1 | macd_rsi_m048 (MACD crossover + RSI>50 + volume surge, ATR TP/SL) | baby_strategies/proven_winners.py (MACDRSIMomentumStrategy); verified_strategies/paper_pilot | PF 3.33 test, 75.4% WR, 5/5 folds | No production caller; shadow mode only; MDD 51.7% on leaderboard (n=393) |
| 2 | crypto_r1 (volume >2x 20d avg + up close, 5-day hold) | turnaround plan (crypto R1) | OOS n=248, PF 2.21 | DSR fails (selection from 6 rules x 5 classes) |
| 3 | connors_rsi2 (RSI(2)<5 & close>200SMA, exit RSI(2)>65 or 10d) | alpha_engine/connors_rsi2.py (adapted to crypto) | 73-76% WR on SPY 1993-2008 | Not previously tested on crypto |
| 4 | crypto_mom20 (20d momentum>0, 5-day hold) | novel simple baseline | none | baseline |
| 5 | crypto_mr_rsi14 (RSI(14)<30, 5-day hold) | novel simple baseline | none | baseline |

## 3. Results table (OOS = 2020-01-01 to 2026-10-20, crypto 30bp costs; IS = <=2019)

| Strategy | Period | n | wins | WR% | PF | PF 95% CI | MDD% | MC pct | DSR | PF@2x | top sym share | PF ex-top |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| macd_rsi_m048 | IS | 46 | 26 | 56.52 | 1.445 | - | -48.94 | - | - | - | - | - |
| macd_rsi_m048 | OOS | 244 | 129 | 52.87 | 1.56 | [1.117,2.12] | -78.11 | 83.2 | 0.00 | 1.476 | 0.13 | 1.636 |
| crypto_r1 | IS | 204 | 107 | 52.45 | 2.017 | - | -92.53 | - | - | - | - | - |
| crypto_r1 | OOS | 689 | 384 | 55.73 | 2.449 | [1.857,3.206] | -89.85 | 100.0 | 0.00 | 2.332 | 0.18 | 2.409 |
| connors_rsi2 | IS | 426 | 266 | 62.44 | 0.96 | - | -98.15 | - | - | - | - | - |
| connors_rsi2 | OOS | 2402 | 1574 | 65.53 | 1.479 | [1.192,1.883] | -97.50 | 98.2 | 0.00 | 1.329 | 0.13 | 1.479 |
| crypto_mom20 | IS | 2909 | 1429 | 49.16 | 1.716 | - | -100.0 | - | - | - | - | - |
| crypto_mom20 | OOS | 12054 | 5870 | 48.71 | 1.497 | [1.336,1.682] | -100.0 | 100.0 | 0.00 | 1.392 | 0.12 | 1.488 |
| crypto_mr_rsi14 | IS | 970 | 437 | 45.05 | 0.896 | - | -100.0 | - | - | - | - | - |
| crypto_mr_rsi14 | OOS | 2811 | 1513 | 53.82 | 1.394 | [1.13,1.718] | -95.26 | 92.7 | 0.00 | 1.282 | 0.12 | 1.41 |

Yearly OOS PF (crypto_r1): 2020 1.434, 2021 2.221, 2022 1.259, 2023 1.372, 2024 2.126, 2025 2.124, 2026 0.589 (loss year flagged).

## 4. Gate evaluation
Gates: OOS after costs n>=100, PF>=1.5, PF CI lower>=1.2, WR>=50%, MDD<=20%, MC pct>=95, DSR>0.95, PF@2x>=1.3, top symbol <=30%, PF ex-top >=1.3.

- macd_rsi_m048: FAIL (MDD -78.11, MC 83.2<95, DSR 0.00, PF@2x 1.476>=1.3 ok, top 0.13<=0.3 ok, pf_ex 1.636>=1.3 ok). Misses MDD, MC, DSR.
- crypto_r1: FAIL (MDD -89.85, DSR 0.00). Misses MDD, DSR. (PF, CI, WR, MC, pf@2x, top share, pf_ex all pass.)
- connors_rsi2: FAIL (PF 1.479<1.5, CI lo 1.192<1.2, MDD -97.5, DSR 0.00).
- crypto_mom20: FAIL (WR 48.71<50, PF 1.497<1.5, MDD -100, DSR 0.00).
- crypto_mr_rsi14: FAIL (PF 1.394<1.5, CI lo 1.13<1.2, MDD -95.26, MC 92.7<95, DSR 0.00, PF@2x 1.282<1.3).

Closest candidate: crypto_r1 — passes all gates except MDD and DSR. Single gate that most blocks promotion: MDD (-89.85% vs <=20% limit). Root cause: no stop loss, 5-day fixed hold in volatile crypto.

## 5. No MONEY-READY strategy. No CANDIDATE (all fail MDD, a hard gate). No paper tracker added.

What would change the verdict for crypto_r1: add a volatility-scaled stop loss (e.g., 2x ATR) and re-test MDD on OOS; if MDD <=20% and DSR>0.95 with n>=100, reclassify as MONEY-READY. Do not loosen gates.

## 6. Reproduce
Command: `cd ../wt-opencode-moneyready && python3 scripts/opencode_crypto_backtest.py`
Outputs: `reports/opencode_money_ready_results.json`. Data: yfinance daily OHLC, 2016-01-01 to today. No credentials needed.

## 7. Data integrity
- Dropped: none (no same-minute resolver batches in this synthetic daily-bar backtest; no exit_price 0.0 rows since signals are bar-close entries).
- Costs: crypto 30bp round trip applied; 2x = 60bp.
- IS/OOS split frozen at 2019-12-31 / 2020-01-01 before seeing results.
- Trials counted = 5 for DSR.
"