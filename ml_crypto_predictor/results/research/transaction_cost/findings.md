# transaction_cost_researcher — slippage flips PF sign

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** tc_001 — Does literature-prior slippage flip gross-positive to net-negative?

| Class | Gross PF | Net PF | Gross mean | Net mean | bps |
|---|---|---|---|---|---|
| COMMODITY | 6.560 | 0.000 | +0.0328% | -0.0472% | 8 |
| CRYPTO | 0.409 | 0.251 | -0.1535% | -0.2535% | 10 |
| EQUITY | 1.212 | 0.000 | +0.0034% | -0.0466% | 5 |
| FOREX | 0.394 | 0.000 | -0.0021% | -0.0221% | 2 |
| FUTURES | 0.000 | 0.000 | -0.0296% | -0.0696% | 4 |

**Wire-up:** `alpha_engine/execution_researcher.py` callers; add gross/net toggle on audit page.

