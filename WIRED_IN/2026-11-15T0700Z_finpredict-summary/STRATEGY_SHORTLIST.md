# STRATEGY_SHORTLIST — 2026-11-15

Legend: proven = passes all 10 gates; promising = fails some but edge; reject = fails majority.

| # | Candidate | Class | Verdict | Sharpe (OOS) | Final vs B&H | Note |
|---|-----------|-------|---------|--------------|--------------|------|
| 1 | BTC sma200 | Crypto | **promising** | 0.57 | 1.94 vs 1.67 | wealth beat confirmed; run full protocol |
| 2 | GLD sma200 | Commodity | **promising (window-sensitive)** | 1.14 | 2.12 vs 2.01 | re-run w/ 1% margin |
| 3 | SPY/QQQ/VTI sma200 | Equities | reject | better | lose wealth | DD overlay only |
| 4 | TLT/BND sma200 | Bonds | reject | negative | lose wealth | kill live buys |
| 5 | IWM sma200 | Equities | reject | 0.31 | lose wealth | |
| 6 | ETH sma200 | Crypto | reject | 0.28 | wins wealth, fails Sharpe | |
| 7 | FOREX | Forex | reject | — | — | WR 6.82% |
| 8 | COT 93.8% | Commodity | reject | — | — | contaminated |

## Ranked actions
1. Run BTC sma200 full proof-protocol (`python3 experiments/crypto_sma200_oos_protocol.py`).
2. Re-run GLD with 1% wealth margin.
3. Discard all others; no live capital.

## Constraints
- Never claim profitability without all 10 gates. Keep paper adapter paper-only. Live emission NO-GO.
