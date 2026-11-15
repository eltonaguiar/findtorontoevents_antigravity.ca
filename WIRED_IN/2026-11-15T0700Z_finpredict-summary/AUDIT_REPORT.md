# AUDIT_REPORT — 2026-11-15

## 1. Inventory highlights
- Reviewed: paper_trading strategies, proven_winners, hypothesis harness, QA ledger, rigorous harness, quality gates, money_ready/shadow verdicts, WIRED_IN packages, updates/.
- Asset classes: stocks, crypto, forex, bonds, ETFs, commodities, mutual funds (zero coverage).
- 0/23 hypotheses survived clean OOS.

## 2. Failure taxonomy summary (top modes)
| Mode | Examples |
|------|----------|
| Look-ahead / data bugs | TIME_EXIT forging, stale prices, 22,947 ghost rows, 1,864 duplicates |
| Overfitting | verified_strategies sma200 in-sample tuned, OOS fail |
| Cost model | originals no costs; 10bp added later |
| Regime/wealth | equity sma200 loses wealth vs B&H |

## 3. Methods catalogue
- Present: sma200/50, momentum, RSI2, MACD, walk-forward 60/40, PBO, DSR, Sharpe, sortino, calmar, kelly, position sizing, TP/SL, 10bp cost, yfinance/Binance/CoinGecko.
- Absent: GBM, LSTM/Transformer, Prophet, HMM-deployed, vectorbt/backtrader, ccxt, alpha vantage, slippage/funding/tax models.

## 4. Candidates
| Candidate | Verdict | Evidence |
|-----------|---------|----------|
| BTC sma200 | PROMISING | wealth 1.94 vs 1.67; 0/11 protocol |
| GLD sma200 | window-sensitive | 2.12 vs 2.01 (pre-margin) |
| Equities sma200 | REJECT | lose wealth |
| TLT/BND sma200 | REJECT | negative Sharpe, lose wealth |
| FOREX | REJECT/INSUFFICIENT | WR 6.82%, DSR fail |
| COT 93.8% | REJECT | contaminated |

## 5. Proof protocol gate results
- 0/11 hypotheses compute PF/CI/DSR/WFO/Bonferroni/MC/shuffle. BTC sma200 wealth beat confirmed but protocol unpassed.

## 6. Metrics per candidate
- BTC: Sharpe 0.57 (vs 0.46), final 1.94 (vs 1.67), maxDD -0.377 vs -0.652. PF/DSR N/A (not computed).

## 7. Notes
- Canadian conventions (currency/tax/hours) not yet applied in cost models. FRED_API_KEY missing blocks bonds/macro.

## 8. Next steps
- Run BTC sma200 full protocol. If fail, pivot to passive allocation product.
