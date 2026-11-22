# Ledger data health — 2026-11-22

Every check below is arithmetic or structural, not statistical taste. `SIGN`, `NO_MOVE`, `BAD_PRICE`, `LEVELS` and `EXIT_SIGN` are impossible as written; `FLAT`, `MISMATCH`, `EXTREME`, `OUTLIER` are improbable and need an explanation from the writer.

## dashboard recent_closed (3500 rows)

| class | BAD_PRICE | EXIT_SIGN | FLAT | GAIN_BEYOND_LEVELS | LEVELS | MISMATCH | NO_MOVE | NO_MOVE_EXIT | OUTLIER |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 0 | 12 | 2 | 297 | 39 | 2 | 0 | 1 | 6 |
| EQUITY | 9 | 0 | 10 | 86 | 2 | 9 | 0 | 0 | 0 |
| FOREX | 29 | 2 | 40 | 1 | 2 | 29 | 0 | 1 | 0 |
| ETF | 0 | 0 | 0 | 16 | 0 | 0 | 1 | 0 | 0 |
| BOND | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| COMMODITY | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |

| class | median pnl | MAD | robust z>10 | max pnl | min pnl |
|---|---|---|---|---|---|
| CRYPTO | -0.8758 | 2.999 | 6 | 100.0 | -97.225 |
| FOREX | 0.0 | 0.4438 | 0 | 3.835 | -2.5 |
| EQUITY | -0.1782 | 3.6254 | 0 | 23.48 | -24.602 |
| ETF | -0.6753 | 1.7842 | 0 | 10.934 | -10.296 |
| BOND | -0.7595 | 0.368 | 0 | 1.285 | -1.276 |

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

