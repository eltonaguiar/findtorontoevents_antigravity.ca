# Ledger data health — 2026-11-22

Every check below is arithmetic or structural, not statistical taste. `SIGN`, `NO_MOVE`, `BAD_PRICE`, `LEVELS` and `EXIT_SIGN` are impossible as written; `FLAT`, `MISMATCH`, `EXTREME`, `OUTLIER` are improbable and need an explanation from the writer.

## dashboard recent_closed (3500 rows)

| class | EXIT_SIGN | FLAT | GAIN_BEYOND_LEVELS | LEVELS | NO_MOVE |
|---|---|---|---|---|---|
| CRYPTO | 12 | 0 | 273 | 31 | 0 |
| EQUITY | 2 | 1 | 112 | 4 | 0 |
| FOREX | 4 | 39 | 1 | 5 | 0 |
| ETF | 3 | 0 | 23 | 4 | 1 |
| COMMODITY | 0 | 0 | 10 | 3 | 0 |
| BOND | 1 | 0 | 0 | 1 | 0 |
| FUTURES | 0 | 0 | 1 | 0 | 0 |

| class | median pnl | MAD | robust z>10 | max pnl | min pnl |
|---|---|---|---|---|---|
| CRYPTO | -1.5132 | 2.5391 | 0 | 18.003 | -20.736 |
| ETF | -0.8094 | 1.7563 | 0 | 13.124 | -10.296 |
| COMMODITY | -3.0 | 2.0 | 0 | 6.697 | -24.984 |
| EQUITY | -0.8915 | 3.5715 | 0 | 23.48 | -30.209 |
| FOREX | 0.0 | 0.4016 | 0 | 3.835 | -2.254 |
| BOND | -0.3805 | 0.6913 | 0 | 2.0 | -1.276 |

## universal_resolved_picks (4877 rows)

| class | BLANK | DUP_ID | GAIN_BEYOND_LEVELS |
|---|---|---|---|
| CRYPTO | 5682 | 589 | 38 |
| FOREX | 611 | 70 | 0 |
| EQUITY | 615 | 10 | 0 |
| FUTURES | 183 | 30 | 0 |
| BOND | 9 | 0 | 0 |
| ETF | 1 | 0 | 0 |

| class | median pnl | MAD | robust z>10 | max pnl | min pnl |
|---|---|---|---|---|---|
| CRYPTO | 0.01 | 2.01 | 0 | 11.43 | -16.7 |
| EQUITY | -0.38 | 1.62 | 0 | 3.5 | -2.0 |
| FUTURES | 0.96 | 2.54 | 0 | 3.5 | -2.0 |

