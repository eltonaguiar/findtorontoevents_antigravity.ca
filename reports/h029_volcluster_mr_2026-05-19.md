# H-029 CRYPTO volatility-cluster mean-reversion — 2026-05-19

_Generated 2026-05-19T04:33:33+00:00 by `tools/h029_volcluster_mr.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick / scoring path. Fetches free Binance data, runs the pre-registered signal through `edge_stability_harness` (imported unmodified), writes this report.

## Pre-registered hypothesis (registry `local_harvest_2026_05_19` / H-029)

Fade the next-session open after an extreme-range day. Day D qualifies when its true range is in the **top decile of the trailing 90-day TR distribution** AND its volume is **> 2.5x the trailing 90-day mean volume**. Enter at the open of D+1: **SHORT if D closed up, LONG if D closed down**. Exit at VWAP-reversion (5-day mean close), a 24h time stop, or +/-1xATR(14). Continuous multi-asset book over liquid Binance USDT majors, daily bars.

**No-look-ahead:** day-D qualification uses only bars strictly before D for the 90-day TR/volume baselines and ATR(14); the trade enters at the D+1 open and resolves within the D+1 bar.

## Data

- Binance public daily klines via the api-failover chain (api/api1/api2/api3 -> CryptoCompare), free, no key. Cached to `tools/cache/h029_volcluster_cache.json`.
- Symbols fetched: 15.
- Continuous-book resolved records (every instrument-day): **13598**.
- Of which qualifying H-029 signal days (extreme-range + >2.5x vol): **513**.

| symbol | records | wins | WR |
|---|---|---|---|
| BTCUSDT | 909 | 488 | 53.7% |
| ETHUSDT | 909 | 500 | 55.0% |
| BNBUSDT | 905 | 458 | 50.6% |
| SOLUSDT | 907 | 450 | 49.6% |
| XRPUSDT | 907 | 462 | 50.9% |
| ADAUSDT | 908 | 435 | 47.9% |
| DOGEUSDT | 907 | 474 | 52.3% |
| AVAXUSDT | 905 | 442 | 48.8% |
| LINKUSDT | 902 | 465 | 51.5% |
| DOTUSDT | 907 | 462 | 50.9% |
| MATICUSDT | 908 | 511 | 56.3% |
| LTCUSDT | 909 | 490 | 53.9% |
| TRXUSDT | 902 | 449 | 49.8% |
| ATOMUSDT | 906 | 449 | 49.6% |
| NEARUSDT | 907 | 464 | 51.2% |

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): `-0.21 -0.14 -0.03 +0.00 +0.17 +0.12 -0.13 -0.01 +0.00 +0.00 +0.00 +0.00 -0.09 -0.09 -0.14 +0.13 +0.07 +0.18 +0.11 -0.11 +0.15 -0.08 -0.04 +0.00 +0.17 +0.00 -0.08 +0.00 +0.15 -0.14 +0.00 +0.09 -0.17 +0.27 -0.26 +0.00 +0.23 -0.22 -0.12 -0.05 -0.01 +0.10 +0.00 -0.13 +0.00 -0.19 +0.42 +0.03 +0.22 +0.00 +0.00 +0.00 +0.00 +0.00 +0.18 +0.22 +0.21 +0.25 +0.00 +0.00 +0.00 +0.08 -0.21 -0.30 -0.02`
- windows scored: 65  (strong: 1)
- sign: `mixed`  same-sign ok: False
- harness `is_admissible()`: False
- harness reason: REJECTED — only 1/65 windows reach eff>=0.3

## Edge & cost survival (over the qualifying H-029 signal days)

- pooled WR: 51.66%
- gross mean per-trade return: 0.00313
- net mean per-trade return (after 30bps): 0.00013
- cost-survival (|gross| > 30bps): 97.5%  (gate >= 60%: PASS)

## VERDICT: **REJECTED**

Clean kill. The volatility-cluster mean-reversion signal does not separate winners from losers with a stable sign across enough 14-day windows (or fails the 30bps cost gate). Do not wire or size. Archive as a tested failure.
